import json
import os
import time
import requests

from supabase import create_client

# ENV VARIABLES
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# CONNECT SUPABASE
supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# ZODIAC SIGNS
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

# FREE MODELS
MODELS = [
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free"
]

# LOAD MASTER PROMPT
with open("prompt.txt", "r", encoding="utf-8") as f:
    MASTER_PROMPT = f.read()

# GENERATE PER SIGN
for sign in SIGNS:

    print(f"\n========== {sign} ==========")

    prompt = f"""
{MASTER_PROMPT}

IMPORTANT:
Generate horoscopes ONLY for this zodiac sign:
{sign}

Generate ALL 15 moods.

Return ONLY valid JSON.
"""

    generated = False

    # TRY MULTIPLE MODELS
    for model_name in MODELS:

        print(f"\nTrying model: {model_name}")

        try:

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                },
                timeout=180
            )

            print("STATUS:", response.status_code)

            result = response.json()

            # RATE LIMIT HANDLING
            if response.status_code == 429:

                retry_time = 30

                try:
                    retry_time = result["error"]["metadata"]["retry_after_seconds"]
                except:
                    pass

                print(f"Rate limited. Waiting {retry_time} seconds...")

                time.sleep(retry_time)

                continue

            # MODEL FAILED
            if "choices" not in result:

                print("MODEL FAILED")
                print(result)

                continue

            # EXTRACT CONTENT
            text = result["choices"][0]["message"]["content"]

            # CLEAN JSON
            if text.startswith("```json"):
                text = text.replace("```json", "")
                text = text.replace("```", "")

            text = text.strip()

            # PARSE JSON
            parsed = json.loads(text)

            # INSERT INTO SUPABASE
            for item in parsed["horoscopes"]:

                supabase.table("horoscopes").upsert({
                    "horoscope_date": parsed["date"],
                    "sign": item["sign"],
                    "mood": item["mood"],
                    "content": item["content"]
                }).execute()

            print(f"SUCCESS FOR {sign}")

            generated = True

            break

        except Exception as e:

            print("ERROR:")
            print(str(e))

            continue

    # ALL MODELS FAILED
    if not generated:

        print(f"FAILED FOR {sign}")

    # SMALL DELAY
    time.sleep(5)

print("\nALL DONE")
