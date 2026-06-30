# matcher.py — fuzzy match form unit names against the registry

import re
from difflib import SequenceMatcher
from config import FUZZY_MATCH_THRESHOLD, CHECKPOINTS


def _normalize(name: str) -> str:
    """Lowercase, strip punctuation and extra whitespace."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9 ]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def _similarity(a: str, b: str) -> int:
    """Return 0–100 similarity score between two strings."""
    return int(SequenceMatcher(None, _normalize(a), _normalize(b)).ratio() * 100)


def find_best_match(query: str, registry: list[dict]) -> dict | None:
    """
    Find the best matching unit in the registry for a given name string.
    Returns the registry dict on a match, None if below threshold.
    """
    best_score = 0
    best_unit = None
    for unit in registry:
        score = _similarity(query, unit.get("unit_number", ""))
        if score > best_score:
            best_score = score
            best_unit = unit
    if best_score >= FUZZY_MATCH_THRESHOLD:
        return best_unit
    return None


def normalize_checkpoint(raw: str) -> str | None:
    """
    Map a raw form checkpoint string to a canonical key.
    Returns one of: 'ruby', 'south_gate', 'basecamp', or None.
    """
    raw_lower = raw.lower().strip()
    for key, label in CHECKPOINTS.items():
        if _normalize(label) in raw_lower or raw_lower in _normalize(label):
            return key
    # Fallback partial matches
    if "ruby" in raw_lower or "ruby" in raw_lower or "welcome" in raw_lower:
        return "ruby"
    if "south" in raw_lower or "gate" in raw_lower:
        return "south_gate"
    if "base" in raw_lower or "camp" in raw_lower:
        return "basecamp"
    return None


CHECKPOINT_TO_STATUS = {
    "ruby":        "At Ruby",
    "south_gate": "At South Gate",
    "basecamp":   "On-site",
}
