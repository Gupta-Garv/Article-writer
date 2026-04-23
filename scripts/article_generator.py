"""Article generator for the SEO Article Writer pipeline.

Builds a detailed LLM prompt from the research, structure, and variation
settings, then calls the OpenAI API to produce the article.

If no OPENAI_API_KEY environment variable is set, the function returns the
structured prompt so the user or a chat agent can generate the article
manually.
"""

import os
import textwrap

# ---------------------------------------------------------------------------
# Descriptive label maps (used in the prompt)
# ---------------------------------------------------------------------------

_OPENING_ANGLE_LABELS = {
    "direct_answer": (
        "Start by giving the clearest, most direct answer to what the reader is searching for."
    ),
    "industry_problem": (
        "Open by describing a widespread challenge or frustration in the industry."
    ),
    "user_pain_point": (
        "Open from the reader's perspective — their frustration, confusion, or unmet need."
    ),
    "contrarian_hook": (
        "Challenge a common assumption or piece of conventional wisdom about the topic."
    ),
    "context_and_promise": (
        "Briefly set context for why the topic matters, then promise the reader what they will get."
    ),
    "surprising_stat": (
        "Lead with a striking, relevant statistic or fact that reframes the topic."
    ),
    "scenario_narrative": (
        "Open with a brief, relatable scenario the target reader will immediately recognise."
    ),
    "question_hook": (
        "Begin with a thought-provoking question that draws the reader in."
    ),
}

_TONE_LABELS = {
    "analytical_neutral": (
        "Data-driven and objective. Present evidence and let readers draw conclusions."
    ),
    "practical_direct": (
        "Clear, direct, and actionable. No filler. Get to the point quickly."
    ),
    "skeptical_critical": (
        "Probing and honest. Question assumptions. Acknowledge trade-offs openly."
    ),
    "educational_clear": (
        "Patient and thorough. Explain concepts clearly for readers who are learning."
    ),
    "expert_authoritative": (
        "Confident and authoritative. Write as a subject-matter expert."
    ),
}

_CONCLUSION_LABELS = {
    "verdict": "End with a clear, direct verdict or bottom line.",
    "use_case_fit": "End by specifying who this is best suited for based on use case.",
    "tradeoff_summary": "End with an honest summary of the key trade-offs.",
    "who_should_avoid": "End by being candid about who should not use or pursue this.",
    "next_steps": "End with concrete next steps the reader can take.",
    "open_question": "End with a thoughtful question that prompts the reader to reflect further.",
}

# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def _build_system_prompt() -> str:
    return textwrap.dedent(
        """
        You are an expert SEO content writer. Your job is to write high-quality,
        informative articles that rank well in search engines and genuinely help readers.

        Strict rules:
        - Do NOT use promotional or marketing language
          (e.g. "game-changer", "revolutionary", "best-in-class", "cutting-edge",
          "industry-leading", "unlock", "transform", "supercharge").
        - Do NOT write puffery or hype of any kind.
        - Write in a clear, factual, and human-readable way.
        - Use the provided factual source material from the website.
          Do not fabricate data, statistics, or product claims.
        - Match the specified tone profile exactly.
        - Follow the specified article structure and section order.
        - Use the specified opening angle for the introduction.
        - Use the specified conclusion type for the ending.
        - Generate a proper SEO-friendly H1 > H2 > H3 heading hierarchy.
        - Target the exact word count specified.
        - Include the primary keyword naturally in the H1 title and throughout the body.
          Do not keyword-stuff.
        - Weave in the listed semantic terms naturally.
        - Mix prose paragraphs with bullet lists — do not use lists for everything.
        """
    ).strip()


def _build_website_block(scraped_data: dict) -> str:
    if scraped_data.get("error"):
        return (
            f"[Website scrape failed: {scraped_data['error']}. "
            "Use your general knowledge as a fallback and clearly signal when "
            "you are not drawing from the provided source.]\n"
        )

    lines = []
    if scraped_data.get("title"):
        lines.append(f"Page title: {scraped_data['title']}")
    if scraped_data.get("meta_description"):
        lines.append(f"Meta description: {scraped_data['meta_description']}")

    if scraped_data.get("headings"):
        lines.append("\nPage headings:")
        for h in scraped_data["headings"][:15]:
            lines.append(f"  {'#' * h['level']} {h['text']}")

    if scraped_data.get("paragraphs"):
        lines.append("\nKey paragraphs:")
        for p in scraped_data["paragraphs"][:10]:
            lines.append(f"  - {p}")

    if scraped_data.get("features"):
        lines.append("\nFeatures mentioned on site:")
        for f in scraped_data["features"]:
            lines.append(f"  - {f}")

    if scraped_data.get("benefits"):
        lines.append("\nBenefits mentioned on site:")
        for b in scraped_data["benefits"]:
            lines.append(f"  - {b}")

    if scraped_data.get("faqs"):
        lines.append("\nFAQs extracted from the website:")
        for faq in scraped_data["faqs"]:
            lines.append(f"  Q: {faq['question']}")
            lines.append(f"  A: {faq['answer']}")

    return "\n".join(lines)


def _build_user_prompt(
    keyword: str,
    scraped_data: dict,
    intent: dict,
    structure: dict,
    variations: dict,
    settings: dict,
) -> str:
    audience = settings.get("audience", "general readers")
    tone = settings.get("tone", "professional and clear")
    length = settings.get("length", 1200)
    notes = settings.get("notes", "")

    website_url = scraped_data.get("url", "the provided website")
    website_block = _build_website_block(scraped_data)

    subtopics = "\n".join(f"  - {s}" for s in intent.get("subtopics", []))
    questions = "\n".join(f"  - {q}" for q in intent.get("questions", []))
    semantic_terms = ", ".join(intent.get("semantic_terms", []))

    # Apply optional section-order reversal (middle sections only)
    sections = list(structure.get("sections", []))
    if variations.get("section_order_reversed") and len(sections) > 4:
        intro = sections[:1]
        conclusion = sections[-1:]
        middle = sections[1:-1]
        sections = intro + list(reversed(middle)) + conclusion

    sections_text = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(sections))

    opening_desc = _OPENING_ANGLE_LABELS.get(variations.get("opening_angle", ""), "")
    tone_desc = _TONE_LABELS.get(variations.get("tone_profile", ""), "")
    conclusion_desc = _CONCLUSION_LABELS.get(variations.get("conclusion_type", ""), "")

    notes_line = f"- Special instructions: {notes}" if notes else ""

    return f"""Write a complete SEO article for the keyword below.

## Keyword and settings
- Primary keyword: {keyword}
- Target audience: {audience}
- Requested tone: {tone}
- Target word count: approximately {length} words
- Search intent: {intent.get("intent_type", "informational")}
- Content angle: {intent.get("content_angle", "")}
{notes_line}

## Factual source material (scraped from {website_url})
{website_block}

## Topic research
Subtopics to cover:
{subtopics}

Questions the article should answer:
{questions}

Semantic terms to include naturally: {semantic_terms}

## Article structure: {structure.get("name", "")}
{structure.get("description", "")}

Sections in order:
{sections_text}

## Variation settings for this article
- Opening angle: {variations.get("opening_angle")}
  {opening_desc}
- Tone profile: {variations.get("tone_profile")}
  {tone_desc}
- Evidence ordering: {variations.get("evidence_ordering")}
- Conclusion type: {variations.get("conclusion_type")}
  {conclusion_desc}

## Output requirements
- Format: Markdown
- H1 title must include the primary keyword
- H2 for main sections, H3 for sub-points where helpful
- Write at approximately {length} words
- Human-readable prose — mix paragraphs with lists
- No promotional language or hype
- Do not fabricate data not found in the source material
- Write the complete article from title to conclusion
""".strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_article(
    keyword: str,
    scraped_data: dict,
    intent: dict,
    structure: dict,
    variations: dict,
    settings: dict,
) -> str:
    """Generate an SEO article using the OpenAI API.

    If OPENAI_API_KEY is not set or the *openai* package is absent, returns
    the structured prompt so the user can run it in any LLM.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()

    user_prompt = _build_user_prompt(
        keyword, scraped_data, intent, structure, variations, settings
    )

    if not api_key:
        return (
            "<!-- ARTICLE GENERATION PROMPT\n"
            "     No OPENAI_API_KEY found. Paste the prompt below into your preferred LLM.\n"
            "-->\n\n"
            "---\n\n"
            + user_prompt
        )

    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _build_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""
    except ImportError:
        return (
            "<!-- The *openai* package is not installed.\n"
            "     Run: pip install openai\n"
            "     Then re-run the script, or paste the prompt below into an LLM.\n"
            "-->\n\n"
            "---\n\n"
            + user_prompt
        )
    except Exception as exc:  # noqa: BLE001 — openai raises many subclasses; catch all
        # Try to surface a friendlier message for known OpenAI API errors
        exc_type = type(exc).__name__
        return (
            f"<!-- Article generation failed ({exc_type}): {exc}\n"
            "     Paste the prompt below into an LLM as a fallback.\n"
            "-->\n\n"
            "---\n\n"
            + user_prompt
        )
