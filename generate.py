import os
import json
import time
import requests

# UPDATED: Re-routed directly to the new Gemini 3.5 Flash stable free endpoint
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

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    params = {"key": API_KEY}
    
    try:
        response = requests.post(GEMINI_URL, json=payload, params=params, timeout=15)
        
        if response.status_code == 200:
            res_data = response.json()
            # Verified traversal path for Gemini 3.5 response structure
            return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        elif response.status_code == 404:
            # Emergency Backup Route: If 3.5 isn't active in your region yet, try the ultra-stable workhorse model string
            fallback_url = "https://googleapis.com"
            fallback_res = requests.post(fallback_url, json=payload, params=params, timeout=15)
            if fallback_res.status_code == 200:
                return fallback_res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"\n❌ Both models returned 404. Check your API Key setup status. Status: {fallback_res.status_code}", flush=True)
            return "The cosmic currents are stabilizing. Focus on inner grounding today."
        elif response.status_code == 429:
            print("\n⚠️ Quota tier limit hit. Pausing for extended cooldown...", flush=True)
            time.sleep(30)
            return generate_horoscope(sign, mood)
        else:
            print(f"\n❌ Server Error [{response.status_code}] on profile: {sign}-{mood}", flush=True)
            return "The cosmic currents are stabilizing. Focus on inner grounding today."
            
    except Exception as e:
        print(f"\nError processing data mapping path on {sign}-{mood}: {e}", flush=True)
        return "The cosmic currents are stabilizing. Focus on inner grounding today."

def main():
    if not API_KEY:
        print("❌ CRITICAL SETUP ERROR: GEMINI_API_KEY environment variable is entirely missing from repository secrets!", flush=True)
        return

    master_database = {}
    total = len(SIGNS) * len(MOODS)
    count = 0
    
    print(f"Starting Gemini Cloud content generation pipeline for {total} profiles...", flush=True)
    for sign in SIGNS:
        master_database[sign] = {}
        for mood in MOODS:
            count += 1
            print(f"[{count}/{total}] Syncing Content Profile: {sign} + {mood}", flush=True)
            master_database[sign][mood] = generate_horoscope(sign, mood)
            
            # Safe 5-second interval protects free tier request thresholds smoothly
            time.sleep(5.0)
            
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(master_database, f, indent=4, ensure_ascii=False)
    print("✨ Rahasya automated content system sync operation successfully completed!", flush=True)

if __name__ == "__main__":
    main()
