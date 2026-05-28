import json
import os
from datetime import datetime

import google.generativeai as genai
from supabase import create_client

# ENV VARIABLES
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# CONFIGURE GEMINI
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.0-flash")

# LOAD PROMPT
with open("prompt.txt", "r", encoding="utf-8") as f:
    prompt = f.read()

# GENERATE CONTENT
response = model.generate_content(prompt)

text = response.text.strip()

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

# INSERT INTO DATABASE
for item in parsed["horoscopes"]:
    supabase.table("horoscopes").upsert({
        "horoscope_date": parsed["date"],
        "sign": item["sign"],
        "mood": item["mood"],
        "content": item["content"]
    }).execute()

print("All horoscopes uploaded successfully.")
