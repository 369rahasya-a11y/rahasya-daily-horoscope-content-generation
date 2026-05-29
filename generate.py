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

client = Groq(api_key=GROQ_API_KEY)

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

SIGN_TRAITS = {
    "Aries": "direct, impulsive, action-oriented, competitive",
    "Taurus": "steady, comfort-seeking, loyal, resistant to change",
    "Gemini": "curious, mentally restless, adaptable, socially observant",
    "Cancer": "emotionally intuitive, protective, nostalgic, sensitive",
    "Leo": "expressive, proud, warm-hearted, attention-aware",
    "Virgo": "analytical, self-critical, observant, improvement-focused",
    "Libra": "relationship-oriented, diplomatic, harmony-seeking, indecisive",
    "Scorpio": "intense, private, emotionally deep, all-or-nothing",
    "Sagittarius": "freedom-seeking, adventurous, optimistic, blunt",
    "Capricorn": "disciplined, ambitious, practical, emotionally reserved",
    "Aquarius": "independent, unconventional, future-focused, detached",
    "Pisces": "imaginative, empathetic, dreamy, emotionally porous"
}

# =========================
# LOAD MASTER PROMPT
# =========================

with open("prompt.txt", "r", encoding="utf-8") as f:
    MASTER_PROMPT = f.read()

today = datetime.utcnow().date().isoformat()

failed_signs = []
successful_signs = []
total_uploaded = 0

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

Sign personality:
{SIGN_TRAITS[sign]}

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

CRITICAL:
- Return STRICT VALID JSON
- Response will be parsed using Python json.loads()
- Do not include comments
- Do not include trailing commas
- Do not include text before JSON
- Do not include text after JSON
- Escape quotation marks inside content properly
"""

    try:

        print("Generating...")

        completion = None

        for attempt in range(3):

            try:

                print(f"API Attempt {attempt + 1}")

                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.8,
                    max_tokens=1800
                )

                break

            except Exception as e:

                print(f"API FAILED: {str(e)}")

                if attempt == 2:
                    failed_signs.append(sign)
                    raise

                time.sleep(5)

        text = completion.choices[0].message.content.strip()

        # =========================
        # CLEAN RESPONSE
        # =========================

        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

        json_start = text.find("{")
        json_end = text.rfind("}")

        if json_start != -1 and json_end != -1:
            text = text[json_start:json_end + 1]

        print("Parsing JSON...")

        try:

            parsed = json.loads(text)

        required_moods = set(MOODS)
        returned_moods = {item["mood"] for item in parsed["horoscopes"]}

    if required_moods != returned_moods:

        print(f"MISSING OR DUPLICATE MOODS FOR {sign}")

        failed_signs.append(sign)

        continue

    if len(parsed["horoscopes"]) != 15:

        print(f"INVALID MOOD COUNT FOR {sign}")

        failed_signs.append(sign)

        continue


        except json.JSONDecodeError as e:

            print(f"INVALID JSON FOR {sign}")
            print(str(e))

            failed_signs.append(sign)

            continue

        print("Uploading...")

        count = 0

        for item in parsed["horoscopes"]:

            supabase.table("horoscopes").upsert(
                {
                    "horoscope_date": parsed["date"],
                    "sign": parsed["sign"],
                    "mood": item["mood"],
                    "content": item["content"]
                },
                on_conflict="horoscope_date,sign,mood"
            ).execute()

            count += 1

        successful_signs.append(sign)
        total_uploaded += count

        print(f"SUCCESS: Uploaded {count}")

    except Exception as e:

        print("FAILED:")
        print(str(e))

    print("Waiting before next sign...\n")

    time.sleep(8)

print("\n========================")
print("GENERATION COMPLETE")
print("========================")

print(f"TOTAL UPLOADED: {total_uploaded}")
print(f"SUCCESSFUL SIGNS: {len(successful_signs)}")

if failed_signs:

    print("\nFAILED SIGNS:")
    print(failed_signs)

else:

    print("\nALL SIGNS GENERATED SUCCESSFULLY")
