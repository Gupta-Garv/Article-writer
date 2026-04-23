---
name: seo-article-writer
description: >
  Chat-native skill that generates unique SEO articles from keyword batches.
  For each keyword it scrapes a target website, researches search intent,
  selects a rotating article structure, and produces a finished markdown
  article saved to articles/ in the repository.
tools:
  - bash
  - filesystem
---

# SEO Article Writer Skill

## What this skill does

When you provide one or more keywords (in the compact input format below),
this skill processes each keyword through a five-step pipeline and saves a
finished SEO article for every keyword to the `articles/` directory.

**Pipeline steps (per keyword):**

1. **Scrape** the provided website and extract headings, paragraphs, FAQs, features, and benefits.
2. **Research** search intent — classifies the keyword as informational, commercial, or transactional and identifies subtopics, key questions, and semantic terms.
3. **Select structure** from a rotating pool of eight article structures, using weighted randomness to avoid back-to-back repetition.
4. **Select variation settings** — picks a unique opening angle, tone profile, evidence ordering, and conclusion type for this run.
5. **Generate article** — calls the LLM with a detailed prompt built from all the above and saves the result as a markdown file.

---

## Input format

```
keyword | website | audience | tone | length | notes
```

All fields after **keyword** are optional (defaults apply when omitted).

| Field      | Description                                       | Default              |
|------------|---------------------------------------------------|----------------------|
| `keyword`  | Primary SEO keyword                               | *(required)*         |
| `website`  | URL to scrape for factual source material         | *(none)*             |
| `audience` | Target reader profile                             | `general readers`    |
| `tone`     | Desired writing tone                              | `professional and clear` |
| `length`   | Target word count                                 | `1200`               |
| `notes`    | Special instructions for this article             | *(none)*             |

### Single keyword
```
best crm for agencies | https://example.com | agency owners | authoritative, skeptical | 1200
```

### Multiple keywords (one per line)
```
best crm for agencies | https://example.com | agency owners | authoritative | 1200
email marketing software | https://example.com | small business owners | clear, practical | 1400 | focus on beginners
project management tools | https://example.com | remote teams | practical | 1000
```

---

## How to invoke this skill

### From GitHub Copilot chat (chat-native)

1. Open a Copilot chat in the `Gupta-Garv/Article-writer` repository.
2. Paste your keyword lines using the format above.
3. The skill will:
   - Run each keyword through the pipeline by executing `scripts/write_article.py`
   - Save the generated articles to `articles/`
   - Commit the results back to the repository

### From GitHub Actions (automated)

1. Go to **Actions → SEO Article Writer → Run workflow**.
2. Paste your keywords (one per line) into the **Keywords** field.
3. Optionally toggle **Research only** to preview the pipeline output without generating an article.
4. The workflow commits generated articles and uploads them as a workflow artifact.

### From the command line

```bash
# Install dependencies
pip install -r requirements.txt

# Single keyword
python scripts/write_article.py \
  "best crm for agencies | https://example.com | agency owners | authoritative | 1200"

# Batch file
python scripts/write_article.py --batch keywords.txt

# Research only (no generation, no state update)
python scripts/write_article.py --research-only \
  "email marketing software | https://example.com"
```

Set `OPENAI_API_KEY` in your environment (or as a repository secret named
`OPENAI_API_KEY`) to enable live article generation.  Without the key the
pipeline completes all research steps and saves a structured prompt that you
can paste into any LLM.

---

## Variation system

Each article run draws independently from four variation pools to ensure
no two articles look the same.

### 1 · Article structures (8 options)

| ID                  | Name                        | Opening style          |
|---------------------|-----------------------------|------------------------|
| `problem_solution`  | Problem-Solution Deep Dive  | Problem hook           |
| `comparison`        | Comparison-Style Article    | Context hook           |
| `guide`             | Comprehensive Guide         | Knowledge-gap hook     |
| `faq_led`           | FAQ-Led Article             | Question hook          |
| `contrarian`        | Contrarian Review           | Contrarian hook        |
| `use_case`          | Use-Case Narrative          | Scenario hook          |
| `decision_framework`| Decision Framework Article  | Decision hook          |
| `step_by_step`      | Step-by-Step Explainer      | Outcome hook           |

The selector uses **inverse-frequency weighting**: structures used less
often receive a higher probability of being chosen.  The immediately
previous structure is always excluded from the candidate pool.

### 2 · Opening angles (8 options)
`direct_answer` · `industry_problem` · `user_pain_point` · `contrarian_hook` ·
`context_and_promise` · `surprising_stat` · `scenario_narrative` · `question_hook`

### 3 · Tone profiles (5 options)
`analytical_neutral` · `practical_direct` · `skeptical_critical` ·
`educational_clear` · `expert_authoritative`

### 4 · Evidence orderings (4 options)
`website_first` · `intent_first` · `mixed_interleaved` · `problem_led`

### 5 · Conclusion types (6 options)
`verdict` · `use_case_fit` · `tradeoff_summary` · `who_should_avoid` ·
`next_steps` · `open_question`

In ~35 % of runs the middle sections of the chosen structure are reversed to
further vary the article flow.

Rotation state is persisted in `state/history.json` across runs so variation
is maintained over time.

---

## Output

Each article is saved to:

```
articles/<keyword-slug>--<YYYYMMDD-HHMMSS>.md
```

The file includes a YAML front-matter block with pipeline metadata:

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
│   │   └── seo-article-writer.md   ← this file (skill definition)
│   └── workflows/
│       └── article-writer.yml      ← GitHub Actions workflow
├── articles/                       ← generated articles (committed as artifacts)
├── config/
│   ├── structures.json             ← article structure pool
│   └── defaults.json               ← default field values
├── scripts/
│   ├── write_article.py            ← main pipeline entry point
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

## Quality rules enforced on every article

- No promotional or marketing language (no "game-changer", "revolutionary", etc.)
- No puffery or hype
- All factual claims grounded in the scraped website source
- Proper H1 > H2 > H3 heading hierarchy
- Keyword used naturally (not stuffed)
- Semantic terms woven in organically
- Prose paragraphs mixed with lists — not lists for everything
