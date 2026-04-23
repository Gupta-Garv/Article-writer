# Article-writer

A repository-based skill and automation for chat-native SEO article generation.

Send keyword batches at any time. The pipeline processes each keyword one by one:
scrapes the target website, researches search intent, selects a rotating article
structure, applies variation settings, and generates a unique SEO-ready markdown
article — saved as a committed file in `articles/`.

---

## Quick start

### From Copilot chat
Open a Copilot chat in this repository and paste keywords using the format:

```
keyword | website | audience | tone | length | notes
```

Example:
```
best crm for agencies | https://example.com | agency owners | authoritative, skeptical | 1200
email marketing software | https://example.com | small business owners | practical | 1400 | focus on beginners
```

The skill processes each line in order and saves an article per keyword.

### From GitHub Actions
1. Go to **Actions → SEO Article Writer → Run workflow**
2. Paste your keywords (one per line) into the **Keywords** input
3. Optionally enable **Research only** to preview the pipeline without generating articles
4. The workflow commits generated articles to `articles/` and uploads them as a workflow artifact

You must add your OpenAI API key as a repository secret named `OPENAI_API_KEY`.

### From the command line

```bash
# Install dependencies
pip install -r requirements.txt

# Single keyword
python scripts/write_article.py \
  "best crm for agencies | https://example.com | agency owners | authoritative | 1200"

# Batch file (one keyword line per line, # lines ignored)
python scripts/write_article.py --batch keywords.txt

# Research only (no article generated, no state updated)
python scripts/write_article.py --research-only \
  "email marketing software | https://example.com"
```

Set `OPENAI_API_KEY` in your environment to enable live generation. Without it, the
pipeline saves a structured LLM prompt to the output file so you can paste it into
any chat interface.

---

## Input format

```
keyword | website | audience | tone | length | notes
```

| Field      | Required | Description                              | Default                  |
|------------|----------|------------------------------------------|--------------------------|
| `keyword`  | Yes      | Primary SEO keyword                      | —                        |
| `website`  | No       | URL to scrape for factual source content | *(none)*                 |
| `audience` | No       | Target reader profile                    | `general readers`        |
| `tone`     | No       | Desired writing tone                     | `professional and clear` |
| `length`   | No       | Target word count                        | `1200`                   |
| `notes`    | No       | Special instructions for this article    | *(none)*                 |

---

## Pipeline steps

For each keyword the pipeline runs five steps:

| Step | Module                      | What it does                                                    |
|------|-----------------------------|-----------------------------------------------------------------|
| 1    | `scripts/scraper.py`        | Scrapes the website: headings, paragraphs, FAQs, features       |
| 2    | `scripts/intent_research.py`| Classifies search intent and finds subtopics and questions      |
| 3    | `scripts/structure_selector.py` | Picks an article structure from the rotating pool           |
| 4    | `scripts/variation_engine.py`   | Selects opening angle, tone profile, evidence order, closing |
| 5    | `scripts/article_generator.py`  | Builds the LLM prompt and generates the article             |

---

## Variation system

Every article gets a unique combination of:

### Article structures (8 options, rotating)

| Structure             | Description                                          |
|-----------------------|------------------------------------------------------|
| Problem-Solution      | Opens with the core problem, then the solution       |
| Comparison            | Evaluates options against clear criteria             |
| Comprehensive Guide   | Covers fundamentals through advanced topics          |
| FAQ-Led               | Centers on answering specific reader questions       |
| Contrarian Review     | Challenges conventional wisdom honestly              |
| Use-Case Narrative    | Explores the topic through reader scenarios          |
| Decision Framework    | Gives readers a structured way to choose             |
| Step-by-Step Explainer| Process walkthrough to a clear outcome               |

The selector uses inverse-frequency weighting so under-used structures are
preferred and the immediately previous structure is always excluded.

### Opening angles (8 options)
`direct_answer` · `industry_problem` · `user_pain_point` · `contrarian_hook` ·
`context_and_promise` · `surprising_stat` · `scenario_narrative` · `question_hook`

### Tone profiles (5 options)
`analytical_neutral` · `practical_direct` · `skeptical_critical` ·
`educational_clear` · `expert_authoritative`

### Evidence orderings (4 options)
`website_first` · `intent_first` · `mixed_interleaved` · `problem_led`

### Conclusion types (6 options)
`verdict` · `use_case_fit` · `tradeoff_summary` · `who_should_avoid` ·
`next_steps` · `open_question`

In roughly 35 % of runs the middle sections of the chosen structure are reversed
to further vary article flow. Rotation state persists in `state/history.json`
across runs.

---

## Output

Articles are saved to:

```
articles/<keyword-slug>--<YYYYMMDD-HHMMSS>.md
```

Each file begins with a YAML front-matter block:

```yaml
---
keyword: "best crm for agencies"
website: "https://example.com"
audience: "agency owners"
tone: "authoritative, skeptical"
target_length: 1200
structure: "Contrarian Review"
opening_angle: "contrarian_hook"
conclusion_type: "tradeoff_summary"
generated_at: "2025-01-01T10:00:00+00:00"
---
```

---

## Repository layout

```
.
├── .github/
│   ├── agents/
│   │   └── seo-article-writer.md   ← skill definition (chat-native invocation)
│   └── workflows/
│       └── article-writer.yml      ← GitHub Actions workflow
├── articles/                       ← generated articles (committed artifacts)
├── config/
│   ├── structures.json             ← article structure pool (8 structures)
│   └── defaults.json               ← default values for optional fields
├── scripts/
│   ├── write_article.py            ← main pipeline entry point / CLI
│   ├── scraper.py                  ← website scraper
│   ├── intent_research.py          ← search-intent classifier
│   ├── structure_selector.py       ← weighted rotation selector
│   ├── variation_engine.py         ← variation settings selector
│   └── article_generator.py        ← LLM prompt builder + caller
├── state/
│   └── history.json                ← persistent rotation state
├── requirements.txt
└── README.md
```

---

## Configuration

### Adding a new article structure
Edit `config/structures.json` and add an entry to the `structures` array.
The `sections` list defines the section keys passed to the LLM — use
descriptive snake_case names so the model understands what each section covers.

### Changing defaults
Edit `config/defaults.json`.

### Resetting rotation state
Delete or reset `state/history.json` to its initial value:

```json
{
  "last_structure_id": null,
  "structure_usage_count": {},
  "last_opening_angle": null,
  "last_tone_profile": null,
  "last_evidence_ordering": null,
  "last_conclusion_type": null,
  "article_count": 0
}
```

---

## Quality rules

Every generated article must:

- Use no promotional or marketing language ("game-changer", "revolutionary", etc.)
- Ground all factual claims in the scraped website source material
- Use a proper H1 > H2 > H3 heading hierarchy
- Include the primary keyword naturally (not stuffed)
- Weave in semantic terms organically
- Mix prose paragraphs with lists — not bullet points for everything
