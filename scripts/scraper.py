"""Website scraper module for the SEO Article Writer pipeline.

Extracts structured content from a given URL to serve as the factual
source layer for article generation.
"""

import os
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

_DEFAULT_TIMEOUT = 15
SCRAPE_TIMEOUT = int(os.environ.get("SCRAPE_TIMEOUT", _DEFAULT_TIMEOUT))
MAX_TEXT_LENGTH = 8000
USER_AGENT = (
    "Mozilla/5.0 (compatible; SEOArticleWriter/1.0; "
    "+https://github.com/Gupta-Garv/Article-writer)"
)


def _clean_text(text: str) -> str:
    """Normalise whitespace and strip leading/trailing space."""
    return re.sub(r"\s+", " ", text).strip()


def _extract_faqs(soup: BeautifulSoup) -> list:
    """Extract FAQ pairs from Schema.org markup or common dl/dt patterns."""
    faqs = []

    # Schema.org FAQPage markup
    for item in soup.select("[itemtype*='FAQPage'] [itemtype*='Question']"):
        q_el = item.select_one("[itemprop='name']")
        a_el = item.select_one("[itemprop='acceptedAnswer'] [itemprop='text']")
        if q_el and a_el:
            faqs.append(
                {
                    "question": _clean_text(q_el.get_text()),
                    "answer": _clean_text(a_el.get_text()),
                }
            )

    # Fallback: <dt>/<dd> definition lists
    if not faqs:
        for dt in soup.find_all("dt"):
            dd = dt.find_next_sibling("dd")
            if dd:
                faqs.append(
                    {
                        "question": _clean_text(dt.get_text()),
                        "answer": _clean_text(dd.get_text()),
                    }
                )

    return faqs[:10]


def _extract_feature_benefit_lists(soup: BeautifulSoup) -> tuple:
    """Heuristically pull feature and benefit lists from <ul>/<ol> elements."""
    features: list = []
    benefits: list = []

    for ul in soup.find_all(["ul", "ol"]):
        items = [
            _clean_text(li.get_text())
            for li in ul.find_all("li")
            if len(_clean_text(li.get_text())) > 10
        ]
        if not items:
            continue

        prev_heading = ul.find_previous(["h1", "h2", "h3", "h4"])
        parent_text = _clean_text(prev_heading.get_text()) if prev_heading else ""

        if re.search(r"feature|capabilit|what.+include|what.+offer", parent_text, re.I):
            features.extend(items[:8])
        elif re.search(r"benefit|advantage|why|value", parent_text, re.I):
            benefits.extend(items[:8])

    return features[:12], benefits[:12]


def scrape_website(url: str) -> dict:
    """Scrape a website and return structured content.

    Returns a dict with keys:
        url, error, title, meta_description, headings (list of {level, text}),
        paragraphs (list of str), faqs (list of {question, answer}),
        features (list of str), benefits (list of str), raw_text (str).
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=SCRAPE_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {
            "url": url,
            "error": str(exc),
            "title": "",
            "meta_description": "",
            "headings": [],
            "paragraphs": [],
            "faqs": [],
            "features": [],
            "benefits": [],
            "raw_text": "",
        }

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    # Title
    title_el = soup.find("title")
    title_text = _clean_text(title_el.get_text()) if title_el else ""

    # Meta description
    meta_desc = ""
    meta_el = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    if meta_el and meta_el.get("content"):
        meta_desc = _clean_text(meta_el["content"])

    # Headings
    headings = []
    for level in range(1, 7):
        for h in soup.find_all(f"h{level}"):
            text = _clean_text(h.get_text())
            if text:
                headings.append({"level": level, "text": text})

    # Paragraphs (skip very short ones)
    paragraphs = [
        _clean_text(p.get_text())
        for p in soup.find_all("p")
        if len(_clean_text(p.get_text())) > 40
    ]

    faqs = _extract_faqs(soup)
    features, benefits = _extract_feature_benefit_lists(soup)

    # Raw body text (truncated)
    body = soup.find("body")
    raw_text = _clean_text(body.get_text()) if body else ""
    raw_text = raw_text[:MAX_TEXT_LENGTH]

    return {
        "url": url,
        "error": None,
        "title": title_text,
        "meta_description": meta_desc,
        "headings": headings[:30],
        "paragraphs": paragraphs[:20],
        "faqs": faqs,
        "features": features,
        "benefits": benefits,
        "raw_text": raw_text,
    }
