"""
Builds the single prompt sent per sign for Generator 3.

Unlike Generator 2 (which splits its philosophy across
modules.py + one prompt file per section), Generator 3's entire
philosophy and all four section briefs live in one file:
prompts/base.txt. That file already ends with the batch/JSON-shape
instructions -- this module only needs to append the sign and the
15 horoscopes for that sign.
"""

from pathlib import Path

_BASE_DIR = Path(__file__).parent

with open(_BASE_DIR / "prompts" / "base.txt", "r", encoding="utf-8") as f:
    BASE_PROMPT = f.read()


def build_prompt(sign: str, rows: list) -> str:
    """
    rows: list of {"mood": ..., "content": ...} for this sign, already
    filtered to the target date and to gen3_status == 'pending'.
    """
    horoscope_block = "\n\n".join(
        f'===MOOD: {row["mood"]}===\n{row["content"]}' for row in rows
    )

    return f"""{BASE_PROMPT}

ZODIAC SIGN FOR THIS BATCH: {sign}

TODAY'S HOROSCOPES (one per mood):

{horoscope_block}
"""
