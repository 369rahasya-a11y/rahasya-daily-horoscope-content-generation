import json
import os
import time
from datetime import datetime

from groq import Groq
from supabase import create_client

# =========================
# ENV VARIABLES
# =========================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# =========================
# VALIDATION
# =========================

if not GROQ_API_KEY:
    raise Exception("GROQ_API_KEY missing")

if not SUPABASE_URL:
    raise Exception("SUPABASE_URL missing")

if not SUPABASE_KEY:
    raise Exception("SUPABASE_SERVICE_ROLE_KEY missing")

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
# DATA
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

MOODS = [
    "Ambitious",
    "Adventurous",
    "Creative",
    "Rebellious",
    "Confident",
    "Anxious",
    "Sad",
    "Lonely",
    "Romantic",
    "Nostalgic",
    "Exhausted",
    "Lazy",
    "Peaceful",
    "Daydreamy",
    "Irritated"
]

# =========================
# LOAD MASTER PROMPT
# =========================

with open("prompt.txt", "r", encoding="utf-8") as f:
    MASTER_PROMPT = f.read()

today = datetime.utcnow().date().isoformat()

# =========================
# GENERATE
# =========================

for sign in SIGNS:

    print(f"\n========== {sign} ==========\n")

    moods_text = "\n".join([f"- {m}" for m in MOODS])

    prompt = f"""
{MASTER_PROMPT}

IMPORTANT:

Generate horoscopes ONLY for:
{sign}

Generate ALL these moods:
{moods_text}

Return ONLY ONE valid JSON object.

STRICT FORMAT:

{{
  "date": "{today}",
  "sign": "{sign}",
  "horoscopes": [
    {{
      "mood": "Ambitious",
      "content": "horoscope text here"
    }}
  ]
}}

RULES:
- Output ONLY JSON
- Do NOT add explanations
- Do NOT add markdown
- Do NOT wrap JSON in triple backticks
- Generate ALL 15 moods
- Each mood must appear exactly once
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
            max_tokens=1800
        )

        text = completion.choices[0].message.content.strip()

        print("\nRAW RESPONSE:\n")
        print(text)

        # =========================
        # CLEAN RESPONSE
        # =========================

        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

        # FIND JSON START
        json_start = text.find("{")

        # FIND JSON END
        json_end = text.rfind("}")

        if json_start != -1 and json_end != -1:
            text = text[json_start:json_end + 1]

               count = 0

        for item in parsed["horoscopes"]:

            supabase.table("horoscopes").upsert(
                {
                    "horoscope_date": parsed["date"],
                    "sign": parsed["sign"],
                    "mood": item["mood"],
                    "content": item["content"]
                }
            ).execute()

            count += 1

        print(f"SUCCESS: Uploaded {count}")

    except Exception as e:

        print("FAILED:")
        print(str(e))

    # =========================
    # RATE LIMIT PROTECTION
    # =========================

    print("Waiting before next sign...\n")

    time.sleep(8)

print("\nALL 180 HOROSCOPES GENERATED")
