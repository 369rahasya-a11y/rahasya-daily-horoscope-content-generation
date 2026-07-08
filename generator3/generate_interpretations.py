import os
import sys
import json
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from groq import Groq
from supabase import create_client

load_dotenv()  # no-op in CI where .env doesn't exist; loads it locally

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from constants import SIGNS, MOODS  # noqa: E402

from prompt_builder import build_prompt  # noqa: E402
from validators import validate_batch  # noqa: E402

GROQ_API_KEY = os.getenv("GROQ_API_KEY_GEN1")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not GROQ_API_KEY:
    raise Exception("GROQ_API_KEY_GEN1 missing")
if not SUPABASE_URL:
    raise Exception("SUPABASE_URL missing")
if not SUPABASE_KEY:
    raise Exception("SUPABASE_SERVICE_ROLE_KEY missing")

client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("CONNECTED")

# Generator 3 always targets the same date Generator 1 just wrote for.
# Generator 1 writes to tomorrow (UTC+1 day); Generator 3 runs right
# after and interprets that same batch -- same convention as
# Generator 2, run independently and in parallel with it.
target_date = (datetime.utcnow().date() + timedelta(days=1)).isoformat()

EXPECTED_MOODS = set(MOODS)

failed_signs = []
succeeded_signs = []
total_updated = 0


def call_groq(prompt: str):
    last_error = None
    for attempt in range(3):
        try:
            print(f"  API attempt {attempt + 1}")
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=5000,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"  API FAILED: {e}")
            last_error = e
            time.sleep(5)
    raise last_error


def parse_json_array(text: str):
    """Groq sometimes wraps output in markdown fences despite instructions.
    Strip those defensively before parsing."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return json.loads(cleaned)


for sign in SIGNS:
    print(f"\n========== {sign} ==========\n")

    rows_resp = (
        supabase.table("horoscopes")
        .select("mood,content")
        .eq("horoscope_date", target_date)
        .eq("sign", sign)
        .eq("gen3_status", "pending")
        .execute()
    )
    rows = rows_resp.data or []

    if not rows:
        print(f"No pending rows for {sign}, skipping.")
        continue

    if {r["mood"] for r in rows} != EXPECTED_MOODS:
        print(f"WARNING: {sign} does not have all 15 pending moods "
              f"({len(rows)} found) — proceeding with what's available.")

    prompt = build_prompt(sign, rows)
    expected_moods_for_batch = {r["mood"] for r in rows}

    success = False
    for attempt in range(3):
        try:
            print("Generating interpretations...")
            raw = call_groq(prompt)
            parsed = parse_json_array(raw)

            if not isinstance(parsed, list):
                raise ValueError("Top-level JSON is not an array")

            problems = validate_batch(parsed, expected_moods_for_batch)
            if problems:
                print(f"VALIDATION FAILED for {sign} (attempt {attempt + 1}):")
                for p in problems:
                    print(f"  - {p}")
                if attempt == 2:
                    failed_signs.append(sign)
                    break
                time.sleep(5)
                continue

            print("Updating rows...")
            count = 0
            for entry in parsed:
                supabase.table("horoscopes").update({
                    "mood_connection": entry["mood_connection"],
                    "today_influence": entry["today_influence"],
                    "daily_action": entry["daily_action"],
                    "personal_note": entry["personal_note"],
                    "gen3_status": "done",
                    "gen3_generated_at": datetime.utcnow().isoformat(),
                }).eq("horoscope_date", target_date).eq("sign", sign).eq(
                    "mood", entry["mood"]
                ).execute()
                count += 1

            succeeded_signs.append(sign)
            total_updated += count
            print(f"SUCCESS: updated {count} rows for {sign}")
            success = True
            break

        except Exception as e:
            print(f"FAILED (attempt {attempt + 1}) for {sign}: {e}")
            if attempt == 2:
                failed_signs.append(sign)
            time.sleep(5)

    if not success and sign not in failed_signs:
        failed_signs.append(sign)

    print("Waiting before next sign...\n")
    time.sleep(8)

print("\n========================")
print("GENERATOR 3 COMPLETE")
print("========================")
print(f"TOTAL ROWS UPDATED: {total_updated}")
print(f"SUCCESSFUL SIGNS: {len(succeeded_signs)}")

if failed_signs:
    print("\nFAILED SIGNS (marked gen3_status='failed'):")
    print(sorted(set(failed_signs)))
    for sign in set(failed_signs):
        supabase.table("horoscopes").update({
            "gen3_status": "failed"
        }).eq("horoscope_date", target_date).eq("sign", sign).eq(
            "gen3_status", "pending"
        ).execute()
else:
    print("\nALL SIGNS PROCESSED SUCCESSFULLY")
