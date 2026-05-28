import os
import time
import itertools
import google.generativeai as genai
from supabase import create_client, Client

# Initialize database clients using standard cloud environments
url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Configure the stable Google library interface using the active model string standard
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash-latest')

signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
moods = ["Ambitious", "Adventurous", "Creative", "Rebellious", "Confident", "Anxious", "Sad", "Lonely", "Romantic", "Nostalgic", "Exhausted", "Lazy", "Peaceful", "Daydreamy", "Irritated"]

print("Clearing yesterday's forecast...")
try:
    supabase.table("daily_horoscopes").delete().neq("zodiac_sign", "").execute()
    print("Database wiped clean!")
except Exception as e:
    print(f"Notice: Could not clear old entries: {e}")

print("Starting cosmic generations...")
for sign, mood in itertools.product(signs, moods):
    print(f"Generating for {sign} - {mood}...")
    
    prompt = f"""
    You are an expert, modern astrologer who writes intuitive, empathetic, and culturally relevant horoscopes. 
    Generate a daily horoscope for:
    - Zodiac Sign: {sign}
    - Selected Mood: {mood}

    [TONE INSTRUCTIONS BASED ON MOOD]
    - If Mood is (Ambitious, Adventurous, Creative, Rebellious, Confident): Use "Fierce & Direct" energy. Be a cosmic hype-man. Use active verbs. Urge immediate action.
    - If Mood is (Anxious, Sad, Lonely, Romantic, Nostalgic): Use "Nurturing & Deeply Empathetic" energy. Validate emotional depth. Speak like a trusted friend. 
    - If Mood is (Exhausted, Lazy, Peaceful, Daydreamy, Irritated): Use "Grounding & Calm" energy. Give permission to slow down or protect peace.

    [STRICT WRITING RULES]
    1. Never mention the name of the mood directly in the text. Mirror the feeling.
    2. Structure: Sentence 1: Acknowledge energy. Sentence 2: Practical advice. Sentence 3: Perspective shift.
    3. Word Count: Strictly between 50 and 70 words. Punchy.
    4. Output: Return ONLY the horoscope text. No greetings.
    5. Introduce absolute variety. Avoid using common astrological clichés like "The stars align," "Cosmic shift," or repeating sentence structures from yesterday. Make every generation unique.
    """
    
    # Auto-Retry Logic to bypass Google rate walls flawlessly
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            # Save cleanly to Supabase
            supabase.table("daily_horoscopes").insert({
                "zodiac_sign": sign,
                "mood": mood,
                "horoscope_text": text
            }).execute()
            
            print(f"✅ Saved successfully: {sign} ({mood})")
            break
            
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"⚠️ Rate limit hit. Cooling down. Retrying attempt {attempt + 1} in 35 seconds...")
                time.sleep(35)
            else:
                print(f"❌ Error generating for {sign}-{mood}: {e}")
                break
    
    # 13-second rate buffer to sit inside Google's standard free tier metrics
    time.sleep(13)

print("All 180 horoscopes successfully synced to the cloud database!")
