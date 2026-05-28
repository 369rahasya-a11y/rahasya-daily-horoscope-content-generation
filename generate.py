import os
import json
import time
import urllib.request
import urllib.error
import sys

# Official Google developer endpoint path
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
API_KEY = os.environ.get("GEMINI_API_KEY")
OUTPUT_FILE = "horoscopes.json"

SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo", 
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
]

MOODS = [
    "ambitious", "adventurous", "creative", "rebellious", "confident",
    "anxious", "sad", "lonely", "romantic", "nostalgic",
    "exhausted", "lazy", "peaceful", "daydreamy", "irritated"
]

def get_tone_rules(mood):
    if mood in ["ambitious", "adventurous", "creative", "rebellious", "confident"]:
        return "Use 'fierce & direct' energy. The tone must feel motivating, magnetic, energetic, bold, action-oriented, and confident."
    elif mood in ["anxious", "sad", "lonely", "romantic", "nostalgic"]:
        return "Use 'nurturing & deeply empathetic' energy. The tone must feel emotionally safe, warm, validating, intimate, understanding, and emotionally intelligent."
    else:
        return "Use 'grounding & calm' energy. The tone must feel spacious, calming, slow, reflective, emotionally balanced, and gently reassuring."

def generate_horoscope(sign, mood):
    tone_instructions = get_tone_rules(mood)
    prompt = (
        f"Write a modern daily horoscope for the zodiac sign '{sign}'. "
        f"The emotional atmosphere must mirror the feeling of being '{mood}', "
        f"BUT YOU MUST NEVER DIRECTLY MENTION THE WORD '{mood}' OR ANY DIRECT SYNONYMS. "
        f"{tone_instructions}\n\n"
        f"STRICT WRITING RULES:\n"
        f"1. Must be between 50 and 70 words total.\n"
        f"2. Sentence 1: emotional/cosmic atmosphere.\n"
        f"3. Sentence 2: practical advice or mental shift.\n"
        f"4. Sentence 3: emotional realization or perspective shift.\n"
        f"Return ONLY the 3-sentence horoscope text. No notes, no introduction, no markdown."
    )

    # Standard native layout configuration required for direct REST API ingestion
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    # Append API key securely via standard URL parameter mapping path
    target_url = f"{GEMINI_URL}?key={API_KEY}"
    
    # Format the explicit headers and force a POST request method
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    req = urllib.request.Request(
        target_url, 
        data=json.dumps(payload).encode('utf-8'), 
        headers=headers,
        method='POST'  # Ensures Python forces a POST call instead of defaulting to a GET route
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            # FIXED PARSER PATH: Unpacks array positions exactly as returned by Google
            return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except urllib.error.HTTPError as he:
        if he.code == 429:
            print("\n⚠️ Rate limit hit. Cooling down system extra...", flush=True)
            time.sleep(20)
            return generate_horoscope(sign, mood)
        print(f"\nHTTP Error {he.code} on {sign}-{mood}", flush=True)
        return "The cosmos are shifting quietly today. Take a moment to ground your breathing. Clarity will find you soon."
    except Exception as e:
        print(f"\nError executing {sign}-{mood}: {e}", flush=True)
        return "The cosmos are shifting quietly today. Take a moment to ground your breathing. Clarity will find you soon."

def main():
    if not API_KEY:
        print("❌ CRITICAL ERROR: GEMINI_API_KEY environment variable is missing!", flush=True)
        return

    master_database = {}
    total = len(SIGNS) * len(MOODS)
    count = 0
    
    print(f"Starting Gemini Cloud content generation pipeline for {total} profiles...", flush=True)
    for sign in SIGNS:
        master_database[sign] = {}
        for mood in MOODS:
            count += 1
            print(f"[{count}/{total}] Processing Content Profile: {sign} + {mood}", flush=True)
            master_database[sign][mood] = generate_horoscope(sign, mood)
            
            # Crucial 4.5 second delay protects your Free Tier limits seamlessly
            time.sleep(4.5)
            
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(master_database, f, indent=4, ensure_ascii=False)
    print("✨ Content system sync operation successfully completed!", flush=True)

if __name__ == "__main__":
    main()
