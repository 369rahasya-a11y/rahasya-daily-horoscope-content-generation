"""
Pure-code validation for Generator 3 output. No AI calls, no
self-critique loops -- structural and phrase-level checks only,
same approach as Generator 2's validators.py, but against Generator
3's own JSON shape and forbidden-phrase list.
"""

REQUIRED_KEYS = {
    "mood",
    "mood_connection",
    "today_influence",
    "daily_action",
    "personal_note",
}

# Phrases that break this generator's writing philosophy outright.
# Kept short and high-precision on purpose -- this is a safety net,
# not a style editor.
FORBIDDEN_PHRASES = [
    # analysis-of-the-horoscope leakage
    "the horoscope suggests", "the horoscope means", "this teaches",
    "the lesson is", "this is really about", "the reading tells us",

    # conclusions/diagnoses handed to the reader
    "this means", "the real issue is", "you fear", "you avoid",
    "you seek", "you struggle with", "you are someone who",
    "your personality", "your subconscious",

    # coaching / therapy / spiritual / motivational language
    "you should", "you must", "remember to", "the universe",
    "everything happens for a reason", "holding space", "inner child",
    "self-care", "healing journey", "trust the process",
    "manifest", "toxic positivity",

    # generic daily-action failure modes named explicitly in the prompt
    "stay positive", "take a break", "trust yourself", "be patient",
    "communicate openly",
]


def contains_forbidden_phrase(text: str):
    """Returns the first forbidden phrase found, or None."""
    lowered = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            return phrase
    return None


def validate_entry(entry: dict) -> list:
    """Validates a single mood's interpretation object. Returns a list
    of problem strings; empty list means the entry is valid."""
    problems = []

    missing = REQUIRED_KEYS - entry.keys()
    if missing:
        problems.append(f"missing keys: {missing}")
        return problems  # no point checking further

    for key in REQUIRED_KEYS - {"mood"}:
        value = entry.get(key, "")
        if not isinstance(value, str) or not value.strip():
            problems.append(f"'{key}' is empty or not a string")
            continue

        phrase = contains_forbidden_phrase(value)
        if phrase:
            problems.append(f"'{key}' contains forbidden phrase: \"{phrase}\"")

    return problems


def validate_batch(entries: list, expected_moods: set) -> list:
    """Validates a full 15-entry batch for one sign. Returns a list of
    problem strings covering both batch-level and per-entry issues."""
    problems = []

    if len(entries) != len(expected_moods):
        problems.append(f"expected {len(expected_moods)} entries, got {len(entries)}")

    returned_moods = {e.get("mood") for e in entries if isinstance(e, dict)}
    if returned_moods != expected_moods:
        problems.append(
            f"mood mismatch — missing: {expected_moods - returned_moods}, "
            f"unexpected: {returned_moods - expected_moods}"
        )

    for entry in entries:
        if not isinstance(entry, dict):
            problems.append(f"entry is not a JSON object: {entry!r}")
            continue
        entry_problems = validate_entry(entry)
        if entry_problems:
            mood = entry.get("mood", "UNKNOWN")
            problems.append(f"[{mood}] " + "; ".join(entry_problems))

    return problems
