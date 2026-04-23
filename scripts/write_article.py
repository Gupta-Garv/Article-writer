#!/usr/bin/env python3
"""Main entry point for the SEO Article Writer pipeline.

Usage
-----
Single keyword (pipe-delimited):
    python scripts/write_article.py "keyword | https://example.com | audience | tone | 1200 | notes"

Batch file (one keyword line per line, lines starting with # are ignored):
    python scripts/write_article.py --batch keywords.txt

Research only (no article generation, no state update):
    python scripts/write_article.py --research-only "keyword | https://example.com"
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from any working directory
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
sys.path.insert(0, str(_SCRIPTS_DIR))

from article_generator import generate_article  # noqa: E402
from intent_research import analyze_intent  # noqa: E402
from scraper import scrape_website  # noqa: E402
from structure_selector import select_structure  # noqa: E402
from variation_engine import select_variations  # noqa: E402

ARTICLES_DIR = _REPO_ROOT / "articles"

_DEFAULTS = {
    "audience": "general readers",
    "tone": "professional and clear",
    "length": 1200,
    "notes": "",
}


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------


def parse_keyword_line(line: str) -> dict:
    """Parse a pipe-delimited keyword line into a settings dict.

    Expected format (all fields after the first two are optional):
        keyword | website | audience | tone | length | notes
    """
    parts = [p.strip() for p in line.split("|")]

    keyword = parts[0] if len(parts) > 0 else ""
    website = parts[1] if len(parts) > 1 else ""
    audience = parts[2] if len(parts) > 2 and parts[2] else _DEFAULTS["audience"]
    tone = parts[3] if len(parts) > 3 and parts[3] else _DEFAULTS["tone"]

    length = _DEFAULTS["length"]
    if len(parts) > 4 and parts[4]:
        raw_len = parts[4].strip()
        # Accept plain integers like "1200" or "1,200" only
        if re.fullmatch(r"\d[\d,]*", raw_len):
            try:
                length = int(raw_len.replace(",", ""))
            except ValueError:
                length = _DEFAULTS["length"]
        else:
            print(
                f"Warning: unrecognised length value {raw_len!r}; "
                f"defaulting to {_DEFAULTS['length']}.",
                file=sys.stderr,
            )

    notes = parts[5] if len(parts) > 5 else _DEFAULTS["notes"]

    return {
        "keyword": keyword,
        "website": website,
        "audience": audience,
        "tone": tone,
        "length": length,
        "notes": notes,
    }


def keyword_to_slug(keyword: str) -> str:
    """Convert a keyword string to a safe filename slug (max 60 chars)."""
    slug = keyword.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:60]


# ---------------------------------------------------------------------------
# Output saving
# ---------------------------------------------------------------------------


def save_article(keyword: str, content: str, metadata: dict) -> Path:
    """Write the article to articles/<slug>--<timestamp>.md."""
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

    slug = keyword_to_slug(keyword)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"{slug}--{timestamp}.md"
    filepath = ARTICLES_DIR / filename

    front_matter = (
        "---\n"
        f'keyword: "{keyword}"\n'
        f'website: "{metadata.get("website", "")}"\n'
        f'audience: "{metadata.get("audience", "")}"\n'
        f'tone: "{metadata.get("tone", "")}"\n'
        f'target_length: {metadata.get("length", 1200)}\n'
        f'structure: "{metadata.get("structure_name", "")}"\n'
        f'opening_angle: "{metadata.get("opening_angle", "")}"\n'
        f'conclusion_type: "{metadata.get("conclusion_type", "")}"\n'
        f'generated_at: "{datetime.now(timezone.utc).isoformat()}"\n'
        "---\n\n"
    )

    filepath.write_text(front_matter + content, encoding="utf-8")
    return filepath


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def process_keyword(settings: dict, research_only: bool = False) -> dict:
    """Run the full pipeline for a single keyword.

    Returns a dict with: keyword, filepath (or None), structure, status.
    """
    keyword = settings["keyword"]
    website = settings["website"]

    print(f"\n{'=' * 60}")
    print(f"  Keyword : {keyword}")
    print(f"  Website : {website or '(none)'}")
    print(f"{'=' * 60}")

    # Step 1 – Scrape website
    print("\n[1/5] Scraping website ...")
    scraped_data: dict = {}
    if website:
        scraped_data = scrape_website(website)
        if scraped_data.get("error"):
            print(f"       Warning: scrape failed — {scraped_data['error']}")
        else:
            print(
                f"       OK — {len(scraped_data.get('headings', []))} headings, "
                f"{len(scraped_data.get('paragraphs', []))} paragraphs"
            )
    else:
        scraped_data = {"url": "", "error": "No website provided."}
        print("       Skipped (no website provided).")

    # Step 2 – Research intent
    print("\n[2/5] Analysing search intent ...")
    intent = analyze_intent(keyword)
    print(f"       Intent  : {intent['intent_type']}")
    print(f"       Angle   : {intent['content_angle']}")

    # Step 3 – Select structure
    print("\n[3/5] Selecting article structure ...")
    structure = select_structure(dry_run=research_only)
    print(f"       Structure: {structure['name']}")

    # Step 4 – Select variations
    print("\n[4/5] Selecting variation settings ...")
    variations = select_variations(dry_run=research_only)
    print(f"       Opening  : {variations['opening_angle']}")
    print(f"       Tone     : {variations['tone_profile']}")
    print(f"       Evidence : {variations['evidence_ordering']}")
    print(f"       Closing  : {variations['conclusion_type']}")

    if research_only:
        print("\n[5/5] Research-only mode — skipping article generation.\n")
        summary = {
            "keyword": keyword,
            "intent": intent,
            "structure": structure,
            "variations": variations,
        }
        print(json.dumps(summary, indent=2))
        return {"keyword": keyword, "status": "research_only", "filepath": None}

    # Step 5 – Generate article
    print("\n[5/5] Generating article ...")
    content = generate_article(keyword, scraped_data, intent, structure, variations, settings)

    metadata = {
        **settings,
        "structure_name": structure["name"],
        "opening_angle": variations["opening_angle"],
        "conclusion_type": variations["conclusion_type"],
    }
    filepath = save_article(keyword, content, metadata)
    print(f"\n       Saved → {filepath.relative_to(_REPO_ROOT)}")

    return {
        "keyword": keyword,
        "status": "success",
        "filepath": str(filepath),
        "structure": structure["name"],
        "variations": variations,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli_epilog() -> str:
    return """
Examples:
  python scripts/write_article.py \\
      "best crm for agencies | https://example.com | agency owners | authoritative | 1200"

  python scripts/write_article.py --batch keywords.txt

  python scripts/write_article.py --research-only \\
      "email marketing software | https://example.com"
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SEO Article Writer — processes keywords one by one.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_cli_epilog(),
    )
    parser.add_argument(
        "keyword_input",
        nargs="?",
        help="'keyword | website | audience | tone | length | notes'",
    )
    parser.add_argument(
        "--batch",
        metavar="FILE",
        help="Text file with one keyword line per line (# lines are skipped).",
    )
    parser.add_argument(
        "--research-only",
        action="store_true",
        help="Run research only; skip article generation and state updates.",
    )

    args = parser.parse_args()

    if not args.keyword_input and not args.batch:
        parser.print_help()
        return 1

    keyword_lines: list = []

    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            print(f"Error: batch file not found: {args.batch}", file=sys.stderr)
            return 1
        raw_lines = batch_path.read_text(encoding="utf-8").splitlines()
        keyword_lines = [
            ln.strip()
            for ln in raw_lines
            if ln.strip() and not ln.strip().startswith("#")
        ]
    elif args.keyword_input:
        keyword_lines = [args.keyword_input.strip()]

    results = []
    for line in keyword_lines:
        settings = parse_keyword_line(line)
        if not settings["keyword"]:
            print(f"Skipping empty keyword in line: {line!r}", file=sys.stderr)
            continue
        result = process_keyword(settings, research_only=args.research_only)
        results.append(result)

    print(f"\n{'=' * 60}")
    print(f"Pipeline complete. Processed {len(results)} keyword(s).")
    if not args.research_only:
        for r in results:
            if r.get("filepath"):
                rel = Path(r["filepath"]).relative_to(_REPO_ROOT)
                print(f"  • {r['keyword']}")
                print(f"    → {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
