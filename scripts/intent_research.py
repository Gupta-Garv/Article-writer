"""Search intent and topic research module for the SEO Article Writer pipeline.

Classifies keyword intent and identifies supporting subtopics, questions,
and semantic terms — all without external API calls.
"""

import re

# ---------------------------------------------------------------------------
# Intent signal patterns
# ---------------------------------------------------------------------------

_TRANSACTIONAL = re.compile(
    r"\b(buy|price|cost|discount|deal|coupon|cheap|affordable|order|purchase|get|"
    r"download|sign up|free trial|pricing|subscribe)\b",
    re.I,
)
_COMMERCIAL = re.compile(
    r"\b(best|top|review|vs|versus|compare|comparison|alternative|alternatives to|"
    r"pros and cons|worth it|should i|recommend|ranking)\b",
    re.I,
)
_INFORMATIONAL = re.compile(
    r"\b(how|what|why|when|where|who|guide|tutorial|tips|explained|definition|"
    r"meaning|examples|learn|understand|overview|introduction|beginner)\b",
    re.I,
)

# ---------------------------------------------------------------------------
# Subtopic pools by intent
# ---------------------------------------------------------------------------

_SUBTOPICS = {
    "informational": [
        "definition and core concepts",
        "historical context and background",
        "how it works in practice",
        "key components or elements",
        "common misconceptions",
        "real-world examples",
        "limitations and trade-offs",
        "related concepts worth knowing",
    ],
    "commercial": [
        "evaluation criteria",
        "feature comparison",
        "pricing and value analysis",
        "usability and learning curve",
        "integrations and compatibility",
        "customer support quality",
        "use-case fit",
        "key differentiators",
    ],
    "transactional": [
        "what you get for the price",
        "setup and onboarding process",
        "key terms and conditions",
        "refund or cancellation policy",
        "alternatives at different price points",
        "getting started checklist",
        "first steps after purchase",
    ],
    "navigational": [
        "brand overview and positioning",
        "primary features and capabilities",
        "pricing tiers",
        "how it compares to alternatives",
        "typical user profiles",
        "known limitations",
        "support and documentation",
    ],
}

# ---------------------------------------------------------------------------
# Question templates by intent
# ---------------------------------------------------------------------------

_QUESTIONS = {
    "informational": [
        "What is {keyword}?",
        "How does {keyword} work?",
        "Why does {keyword} matter?",
        "What are the key components of {keyword}?",
        "What are common mistakes related to {keyword}?",
        "What should beginners know about {keyword}?",
    ],
    "commercial": [
        "What should you look for in {keyword}?",
        "How do I choose the right {keyword}?",
        "What are the trade-offs between {keyword} options?",
        "Is {keyword} worth the investment?",
        "Who benefits most from {keyword}?",
        "How do the leading {keyword} options compare?",
    ],
    "transactional": [
        "What is included with {keyword}?",
        "How do I get started with {keyword}?",
        "What is the pricing for {keyword}?",
        "Are there alternatives to {keyword}?",
        "What should I know before buying {keyword}?",
    ],
    "navigational": [
        "What is {keyword}?",
        "How does {keyword} compare to alternatives?",
        "What features does {keyword} offer?",
        "Who is {keyword} designed for?",
    ],
}


def _infer_intent(keyword: str) -> str:
    """Return the most likely search intent for the keyword."""
    if _TRANSACTIONAL.search(keyword):
        return "transactional"
    if _COMMERCIAL.search(keyword):
        return "commercial"
    if _INFORMATIONAL.search(keyword):
        return "informational"
    # Default for head terms and brand-style queries
    return "informational"


def _infer_content_angle(keyword: str, intent: str) -> str:
    """Return a one-line description of the recommended content angle."""
    kw = keyword.lower()

    if intent == "commercial":
        if re.search(r"\bvs\b|\bversus\b|\bcompare\b", kw):
            return "direct comparison with clear evaluation criteria"
        if re.search(r"\bbest\b|\btop\b", kw):
            return "curated selection with evidence-backed reasoning"
        return "balanced review grounded in practical use"

    if intent == "transactional":
        return "buyer-oriented guide focused on decision confidence"

    if intent == "informational":
        if re.search(r"\bhow\b|\bguide\b|\btutorial\b", kw):
            return "step-by-step explanatory walkthrough"
        if re.search(r"\bwhat\b|\bdefinition\b|\bmeaning\b", kw):
            return "clear explanation with practical context"
        return "educational overview with real-world grounding"

    return "brand-neutral factual overview"


def analyze_intent(keyword: str) -> dict:
    """Analyse search intent for a keyword.

    Returns:
        keyword, intent_type, content_angle, subtopics (list),
        questions (list), semantic_terms (list).
    """
    intent = _infer_intent(keyword)
    angle = _infer_content_angle(keyword, intent)
    subtopics = _SUBTOPICS.get(intent, _SUBTOPICS["informational"])
    questions = [
        q.format(keyword=keyword) for q in _QUESTIONS.get(intent, [])
    ]

    # Derive semantic terms from the keyword itself
    words = re.sub(r"[^\w\s]", "", keyword).split()
    semantic_terms = sorted({w.lower() for w in words if len(w) > 3})

    return {
        "keyword": keyword,
        "intent_type": intent,
        "content_angle": angle,
        "subtopics": subtopics,
        "questions": questions,
        "semantic_terms": semantic_terms,
    }
