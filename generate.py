import os
import time
import itertools
from google import genai
from supabase import create_client, Client

# Clean client initialisation using environment variables 
url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(url, key)
ai_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
moods = ["Ambitious", "Adventurous", "Creative", "Rebellious", "Confident", "Anxious", "Sad", "Lonely", "Romantic", "Nostalgic", "Exhausted", "Lazy", "Peaceful", "Daydreamy", "Irritated"]

print("Clearing yesterday's forecast...")
try:
    supabase.table("daily_horoscopes").delete().neq("zodiac_sign", "").execute()
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
    
    # Retry mechanism loop (will try up to 3 times if Google rate limits us)
    for attempt in range(3):
        try:
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            text = response.text.strip()
            
            # Insert cleanly to Supabase
            supabase.table("daily_horoscopes").insert({
                "zodiac_sign": sign,
                "mood": mood,
                "horoscope_text": text
            }).execute()
            
            print(f"✅ Saved successfully: {sign} ({mood})")
            break # Success! Break out of the retry loop
            
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"⚠️ Google rate limit hit. Cool down cooling active. Retrying attempt {attempt + 1} in 35 seconds...")
                time.sleep(35) # Wait out Google's penalty window
            else:
                print(f"❌ Error generating for {sign}-{mood}: {e}")
                break
    
    # Standard steady pace pause between items
    time.sleep(13)

print("All 180 horoscopes successfully synced to the cloud database!")
