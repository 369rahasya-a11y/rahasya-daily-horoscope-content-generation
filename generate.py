import os
import json
import time
import urllib.request

GROQ_API_URL = "https://groq.com"
API_KEY = os.environ.get("GROQ_API_KEY")
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
        f"Return ONLY the 3-sentence horoscope text. No notes, no introduction."
    )

    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    req = urllib.request.Request(
        GROQ_API_URL, 
        data=json.dumps(payload).encode('utf-8'), 
        headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {API_KEY}"}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data["choices"]["message"]["content"].strip()
    except Exception as e:
        print(f"Error {sign}-{mood}: {e}")
        return "The cosmos are shifting quietly today. Take a moment to ground your breathing. Clarity will find you soon."

def main():
    master_database = {}
    total = len(SIGNS) * len(MOODS)
    count = 0
    
    print(f"Starting generation for {total} items...")
    for sign in SIGNS:
        master_database[sign] = {}
        for mood in MOODS:
            count += 1
            print(f"[{count}/{total}] Processing {sign} - {mood}")
            master_database[sign][mood] = generate_horoscope(sign, mood)
            time.sleep(2) # Keeps us safely within Groq's free tier limits
            
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(master_database, f, indent=4, ensure_ascii=False)
    print("Done!")

if __name__ == "__main__":
    main()
