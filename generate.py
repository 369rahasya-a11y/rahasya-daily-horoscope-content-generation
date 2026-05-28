import os
import json
import time
import urllib.request
import urllib.error

# Native Endpoint Config (Using Gemini Flash for reliable, high-speed free processing)
GEMINI_URL = "https://googleapis.com"
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

    # Clean REST API Structure formatting for native Google API ingestion
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 150
        }
    }

    # Authenticate via native URL API Key parameter to avoid header injection issues
    target_url = f"{GEMINI_URL}?key={API_KEY}"
    req = urllib.request.Request(
        target_url, 
        data=json.dumps(payload).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            # Parse text response safely out of the standard nested Gemini structure
            return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except urllib.error.HTTPError as he:
        if he.code == 429:
            print("⚠️ Rate limit hit. Cooling down system extra...")
            time.sleep(15) # Extended recovery pause
            return generate_horoscope(sign, mood) # Retry block
        print(f"HTTP Error {he.code} on {sign}-{mood}: {he.read().decode('utf-8')}")
        return "The cosmos are shifting quietly today. Take a moment to ground your breathing. Clarity will find you soon."
    except Exception as e:
        print(f"Error executing {sign}-{mood}: {e}")
        return "The cosmos are shifting quietly today. Take a moment to ground your breathing. Clarity will find you soon."

def main():
    if not API_KEY:
        print("❌ CRITICAL ERROR: GEMINI_API_KEY environment variable is missing!")
        return

    master_database = {}
    total = len(SIGNS) * len(MOODS)
    count = 0
    
    print(f"Starting Gemini Cloud content generation pipeline for {total} profiles...")
    for sign in SIGNS:
        master_database[sign] = {}
        for mood in MOODS:
            count += 1
            print(f"[{count}/{total}] Processing Content Profile: {sign} + {mood}")
            master_database[sign][mood] = generate_horoscope(sign, mood)
            
            # Crucial 4.5 second delay protects your Free Tier limits seamlessly (approx 13 requests/min)
            time.sleep(4.5)
            
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(master_database, f, indent=4, ensure_ascii=False)
    print("✨ Content system sync operation successfully completed!")

if __name__ == "__main__":
    main()
