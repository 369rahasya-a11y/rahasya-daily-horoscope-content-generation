import json
import os
import time
import requests

from supabase import create_client

# =========================
# ENV VARIABLES
# =========================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# =========================
# CONNECT SUPABASE
# =========================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

print("SUPABASE CONNECTED")

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
"""

    try:

        print("Sending request...")

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.9,
                "max_tokens": 4000
            },
            timeout=45
        )

        print("STATUS:", response.status_code)

        result = response.json()

        if "choices" not in result:

            print("FAILED:")
            print(result)

            continue

        text = result["choices"][0]["message"]["content"]

        # CLEAN JSON
        if text.startswith("```json"):
            text = text.replace("```json", "")
            text = text.replace("```", "")

        text = text.strip()

        print("Parsing JSON...")

        parsed = json.loads(text)

        print("Uploading to Supabase...")

        count = 0

        for item in parsed["horoscopes"]:

            supabase.table("horoscopes").upsert({
                "horoscope_date": parsed["date"],
                "sign": item["sign"],
                "mood": item["mood"],
                "content": item["content"]
            }).execute()

            count += 1

        print(f"SUCCESS: Uploaded {count} horoscopes")

    except Exception as e:

        print("ERROR:")
        print(str(e))

    time.sleep(35)

print("\nALL DONE")
