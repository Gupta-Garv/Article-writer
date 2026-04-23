"""Variation engine for the SEO Article Writer.

Selects the opening angle, tone profile, evidence ordering, and conclusion
type for each article run, avoiding back-to-back repetition to maximise
uniqueness across articles.
"""

import json
import random
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "state" / "history.json"

# ---------------------------------------------------------------------------
# Variation pools
# ---------------------------------------------------------------------------

OPENING_ANGLES = [
    "direct_answer",        # Lead with the clearest answer right away
    "industry_problem",     # Open with a widespread industry challenge
    "user_pain_point",      # Open from the reader's frustration or confusion
    "contrarian_hook",      # Challenge a common assumption about the topic
    "context_and_promise",  # Brief context, then promise of what readers will learn
    "surprising_stat",      # Open with a striking, relevant data point
    "scenario_narrative",   # Brief scenario the target reader will recognise
    "question_hook",        # Thought-provoking question to draw the reader in
]

TONE_PROFILES = [
    "analytical_neutral",    # Data-driven and objective
    "practical_direct",      # Clear and actionable; no filler
    "skeptical_critical",    # Probing; questions assumptions; acknowledges trade-offs
    "educational_clear",     # Patient and thorough; teaching mode
    "expert_authoritative",  # Confident subject-matter-expert voice
]

EVIDENCE_ORDERINGS = [
    "website_first",      # Lead with website-sourced claims, then intent context
    "intent_first",       # Lead with search-intent context, then website claims
    "mixed_interleaved",  # Alternate between intent and website sources
    "problem_led",        # Open with the problem, then layer in supporting evidence
]

CONCLUSION_TYPES = [
    "verdict",           # Clear "here is the bottom line" statement
    "use_case_fit",      # "This works best if you are..."
    "tradeoff_summary",  # Honest summary of pros and cons
    "who_should_avoid",  # "This is not for you if..."
    "next_steps",        # "Here is what to do next..."
    "open_question",     # End with a thoughtful question that prompts reflection
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


def _pick_avoiding_last(pool: list, last_key: str, state: dict) -> str:
    """Pick randomly from *pool*, avoiding the value stored in *state[last_key]*."""
    last_used = state.get(last_key)
    candidates = [x for x in pool if x != last_used]
    if not candidates:
        candidates = pool
    return random.choice(candidates)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def select_variations(dry_run: bool = False) -> dict:
    """Select variation settings for the current article run.

    Args:
        dry_run: When True the state file is not updated.

    Returns:
        Dict with keys: opening_angle, tone_profile, evidence_ordering,
        conclusion_type, section_order_reversed.
    """
    state = _load_state()

    opening_angle = _pick_avoiding_last(OPENING_ANGLES, "last_opening_angle", state)
    tone_profile = _pick_avoiding_last(TONE_PROFILES, "last_tone_profile", state)
    evidence_ordering = _pick_avoiding_last(
        EVIDENCE_ORDERINGS, "last_evidence_ordering", state
    )
    conclusion_type = _pick_avoiding_last(CONCLUSION_TYPES, "last_conclusion_type", state)

    # Occasionally reverse the middle sections to vary article flow (~35 % of runs)
    section_order_reversed = random.random() < 0.35

    variations = {
        "opening_angle": opening_angle,
        "tone_profile": tone_profile,
        "evidence_ordering": evidence_ordering,
        "conclusion_type": conclusion_type,
        "section_order_reversed": section_order_reversed,
    }

    if not dry_run:
        state.update(
            {
                "last_opening_angle": opening_angle,
                "last_tone_profile": tone_profile,
                "last_evidence_ordering": evidence_ordering,
                "last_conclusion_type": conclusion_type,
            }
        )
        _save_state(state)

    return variations
