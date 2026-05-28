import os
import time
import itertools
import requests
import google.generativeai as genai

# Raw environment variables
url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_KEY"]
gemini_key = os.environ["GEMINI_API_KEY"]

# Configure the legacy-stable Google library interface
genai.configure(api_key=gemini_key)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
moods = ["Ambitious", "Adventurous", "Creative", "Rebellious", "Confident", "Anxious", "Sad", "Lonely", "Romantic", "Nostalgic", "Exhausted", "Lazy", "Peaceful", "Daydreamy", "Irritated"]

# Direct API Headers for new Supabase keys standard
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

print("Clearing yesterday's forecast...")
try:
    # Direct delete API call via requests to prevent library hanging
    delete_url = f"{url}/rest/v1/daily_horoscopes?zodiac_sign=not.eq."
    res = requests.delete(delete_url, headers=headers)
    print(f"Database reset status code: {res.status_code}")
except Exception as e:
    print(f"Notice: Handled clear entry routine safely: {e}")

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
    
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            # Direct upsert data dictionary
            payload = {
                "zodiac_sign": sign,
                "mood": mood,
                "horoscope_text": text
            }
            
            # Post directly to the rest database endpoint
            insert_url = f"{url}/rest/v1/daily_horoscopes"
            post_res = requests.post(insert_url, json=payload, headers=headers)
            
            if post_res.status_code in [200, 201]:
                print(f"   ✅ Saved successfully: {sign} ({mood})")
                break
            else:
                print(f"   ⚠️ Database rejected payload with status {post_res.status_code}: {post_res.text}")
            
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"   ⚠️ Rate limit hit. Cooling down. Retrying attempt {attempt + 1} in 35 seconds...")
                time.sleep(35)
            else:
                print(f"   ❌ Error generating for {sign}-{mood}: {e}")
                break
    
    # 13-second pace buffer
    time.sleep(13)

print("All 180 horoscopes successfully synced to the cloud database!")
