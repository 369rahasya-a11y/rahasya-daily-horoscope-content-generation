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

# REQUEST
response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
)

# DEBUG
print("STATUS:", response.status_code)
print("RAW RESPONSE:")
print(response.text)

# CONVERT JSON
result = response.json()

# SAFETY CHECK
if "choices" not in result:
    raise Exception(f"OpenRouter Error: {result}")

text = result["choices"][0]["message"]["content"]

# CLEAN JSON
if text.startswith("```json"):
    text = text.replace("```json", "").replace("```", "")

# PARSE
parsed = json.loads(text)

# CONNECT SUPABASE
supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# INSERT
for item in parsed["horoscopes"]:
    supabase.table("horoscopes").upsert({
        "horoscope_date": parsed["date"],
        "sign": item["sign"],
        "mood": item["mood"],
        "content": item["content"]
    }).execute()

print("All horoscopes uploaded successfully.")
