"""Article structure selector with weighted rotation logic.

Reads the structure pool from config/structures.json and the rotation state
from state/history.json.  Selects the next structure while avoiding
back-to-back repetition and preferring under-used structures.
"""

import json
import random
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "structures.json"
STATE_PATH = Path(__file__).resolve().parent.parent / "state" / "history.json"


def _load_structures() -> list:
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)["structures"]


def _load_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return {
        "last_structure_id": None,
        "structure_usage_count": {},
        "last_opening_angle": None,
        "last_tone_profile": None,
        "last_evidence_ordering": None,
        "last_conclusion_type": None,
        "article_count": 0,
    }


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


def select_structure(dry_run: bool = False) -> dict:
    """Select the next article structure, avoiding back-to-back repeats.

    Args:
        dry_run: When True the state file is not updated (useful for previews).

    Returns:
        A structure dict from config/structures.json.
    """
    structures = _load_structures()
    state = _load_state()

    last_id = state.get("last_structure_id")
    usage: dict = state.get("structure_usage_count", {})

    # Exclude the last-used structure to prevent immediate repetition
    candidates = [s for s in structures if s["id"] != last_id]
    if not candidates:
        candidates = structures  # only one structure exists – no choice

    # Inverse-frequency weighting so under-used structures are preferred
    weights = [1.0 / (usage.get(s["id"], 0) + 1) for s in candidates]
    chosen = random.choices(candidates, weights=weights, k=1)[0]

    if not dry_run:
        state["last_structure_id"] = chosen["id"]
        usage[chosen["id"]] = usage.get(chosen["id"], 0) + 1
        state["structure_usage_count"] = usage
        state["article_count"] = state.get("article_count", 0) + 1
        _save_state(state)

    return chosen
