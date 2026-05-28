import json
import os
import time

from groq import Groq
from supabase import create_client

# =========================
# ENV VARIABLES
# =========================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# =========================
# CLIENTS
# =========================

client = Groq(
    api_key=GROQ_API_KEY
)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

print("CONNECTED")

# =========================
# SIGNS
# =========================

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces"
]

# =========================
# LOAD PROMPT
# =========================

with open("prompt.txt", "r", encoding="utf-8") as f:
    MASTER_PROMPT = f.read()

# =========================
# GENERATE
# =========================

for sign in SIGNS:

    print(f"\n========== {sign} ==========\n")

    prompt = f"""
{MASTER_PROMPT}

IMPORTANT:
Generate horoscopes ONLY for:
{sign}

Generate all 15 moods.

Return ONLY valid JSON.

Do not add explanations.
Do not add markdown.
Do not wrap JSON in triple backticks.
"""

    try:

        print("Generating...")

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.9,
            max_tokens=2500
        )

        text = completion.choices[0].message.content

        print("\nRAW RESPONSE:\n")
        print(text)

        # =========================
        # CLEAN RESPONSE
        # =========================

        if text.startswith("```json"):
            text = text.replace("```json", "")

        if text.startswith("```"):
            text = text.replace("```", "")

        text = text.strip()

        # FIND JSON START
        json_start = text.find("{")

        if json_start != -1:
            text = text[json_start:]

        # FIND JSON END
        json_end = text.rfind("}")

        if json_end != -1:
            text = text[:json_end + 1]

        print("\nCLEANED JSON:\n")
        print(text)

        print("Parsing JSON...")

        parsed = json.loads(text)

        print("Uploading...")

        count = 0

        for item in parsed["horoscopes"]:

            supabase.table("horoscopes").upsert({
                "horoscope_date": parsed["date"],
                "sign": item["sign"],
                "mood": item["mood"],
                "content": item["content"]
            }).execute()

            count += 1

        print(f"SUCCESS: Uploaded {count}")

    except Exception as e:

        print("FAILED:")
        print(str(e))

    time.sleep(3)

print("\nALL DONE")
