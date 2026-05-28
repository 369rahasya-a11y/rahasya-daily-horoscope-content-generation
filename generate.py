````python
import json
import os
import requests
import time

from supabase import create_client

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# LOAD PROMPT
with open("prompt.txt", "r", encoding="utf-8") as f:
    prompt = f.read()

MAX_RETRIES = 5

for attempt in range(MAX_RETRIES):

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
            ]
        }
    )

    print("STATUS:", response.status_code)

    result = response.json()

    # SUCCESS
    if "choices" in result:
        break

    # RATE LIMIT
    if response.status_code == 429:
        retry_time = 30

        try:
            retry_time = result["error"]["metadata"]["retry_after_seconds"]
        except:
            pass

        print(f"Rate limited. Waiting {retry_time} seconds...")

        time.sleep(retry_time)

        continue

    # OTHER ERRORS
    raise Exception(f"OpenRouter Error: {result}")

# FINAL TEXT
text = result["choices"][0]["message"]["content"]

# CLEAN JSON
if text.startswith("```json"):
    text = text.replace("```json", "").replace("```", "")

# PARSE JSON
parsed = json.loads(text)

# CONNECT SUPABASE
supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# INSERT DATA
for item in parsed["horoscopes"]:
    supabase.table("horoscopes").upsert({
        "horoscope_date": parsed["date"],
        "sign": item["sign"],
        "mood": item["mood"],
        "content": item["content"]
    }).execute()

print("All horoscopes uploaded successfully.")
````
