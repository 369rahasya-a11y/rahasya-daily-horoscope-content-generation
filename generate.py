import os
import time
import itertools
import requests

# Raw environment variables
url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_KEY"]
gemini_key = os.environ["GEMINI_API_KEY"]

signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
moods = ["Ambitious", "Adventurous", "Creative", "Rebellious", "Confident", "Anxious", "Sad", "Lonely", "Romantic", "Nostalgic", "Exhausted", "Lazy", "Peaceful", "Daydreamy", "Irritated"]

# Direct API Headers for Supabase REST endpoints
supabase_headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

print("Clearing yesterday's forecast...")
try:
    # Direct delete API call to clear out old table rows safely
    res = requests.delete(f"{url}/daily_horoscopes?zodiac_sign=not.eq.", headers=supabase_headers)
    print(f"Database reset status code: {res.status_code}")
except Exception as e:
    print(f"Notice: Clear operation log: {e}")

print("Starting cosmic generations...")
for sign, mood in itertools.product(signs, moods):
    print(f"👉 Processing: {sign} + {mood}...")
    
    prompt = f"""
    You are an expert, modern astrologer who writes intuitive, empathetic, and culturally relevant horoscopes. 
    Generate a daily horoscope for:
    - Zodiac Sign: {sign}
    - Selected Mood: {mood}

    [TONE INSTRUCTIONS BASED ON MOOD]
    - If Mood is (Ambitious, Adventurous, Creative, Rebellious, Confident): Use "Fierce & Direct" energy. Cosmic hype-man. Use active verbs. Urge action.
    - If Mood is (Anxious, Sad, Lonely, Romantic, Nostalgic): Use "Nurturing & Deeply Empathetic" energy. Validate emotional depth. Speak softly. 
    - If Mood is (Exhausted, Lazy, Peaceful, Daydreamy, Irritated): Use "Grounding & Calm" energy. Give permission to slow down or protect peace.

    [STRICT WRITING RULES]
    1. Never mention the name of the mood directly in the text. Mirror the feeling.
    2. Structure: Sentence 1: Acknowledge energy. Sentence 2: Practical advice. Sentence 3: Perspective shift.
    3. Word Count: Strictly between 50 and 70 words. Punchy.
    4. Output: Return ONLY the horoscope text. No greetings.
    5. Introduce absolute variety. Avoid using common astrological clichés like "The stars align," "Cosmic shift," or repeating sentence structures from yesterday. Make every generation unique.
    """
    
    # Raw JSON packet structure for Gemini 2.5 API
    gemini_payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    for attempt in range(3):
        try:
            # Direct API request completely independent of Google's deprecated SDKs
            gemini_url = f"https://googleapis.com{gemini_key}"
            gemini_res = requests.post(gemini_url, json=gemini_payload, headers={"Content-Type": "application/json"})
            
            if gemini_res.status_code == 200:
                # Parse out raw generated text smoothly from response tree
                text = gemini_res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                
                # Direct data dictionary deployment
                payload = {
                    "zodiac_sign": sign,
                    "mood": mood,
                    "horoscope_text": text
                }
                
                # Post data directly into Supabase REST endpoint
                post_res = requests.post(f"{url}/daily_horoscopes", json=payload, headers=supabase_headers)
                
                if post_res.status_code in [200, 201, 204]:
                    print(f"   ✅ Saved successfully: {sign} ({mood})")
                    break
                else:
                    print(f"   ⚠️ Database rejected row with status {post_res.status_code}: {post_res.text}")
                    break
            elif gemini_res.status_code == 429:
                print(f"   ⚠️ Google Rate limit hit. Cooling down. Retrying attempt {attempt + 1} in 35 seconds...")
                time.sleep(35)
            else:
                print(f"   ❌ Gemini API Error {gemini_res.status_code}: {gemini_res.text}")
                break
                
        except Exception as e:
            print(f"   ❌ Network processing exception: {e}")
            break
            
    # 13-second interval check to respect Google's free global tier limitations
    time.sleep(13)

print("All 180 horoscopes successfully synced to the cloud database!")
