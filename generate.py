import os
import re
import time
from datetime import datetime, timedelta

from groq import Groq
from supabase import create_client

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not GROQ_API_KEY:
    raise Exception("GROQ_API_KEY missing")

if not SUPABASE_URL:
    raise Exception("SUPABASE_URL missing")

if not SUPABASE_KEY:
    raise Exception("SUPABASE_SERVICE_ROLE_KEY missing")

client = Groq(api_key=GROQ_API_KEY)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

print("CONNECTED")

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

MOODS = [
    "Ambitious", "Adventurous", "Creative", "Rebellious", "Confident",
    "Anxious", "Sad", "Lonely", "Romantic", "Nostalgic",
    "Exhausted", "Lazy", "Peaceful", "Daydreamy", "Irritated"
]

SIGN_TRAITS = {
"Aries": "acts before thinking, direct, competitive, impulsive, hides vulnerability through action, becomes restless when emotions slow them down, dislikes waiting for clarity",

```
"Taurus": "steady, comfort-seeking, loyal, emotionally persistent, values stability, resists sudden change, holds onto people and routines longer than necessary, seeks security during uncertainty",

"Gemini": "curious, mentally restless, adaptable, socially observant, processes emotions through thinking, overanalyzes conversations, seeks stimulation, notices subtle shifts in communication",

"Cancer": "emotionally intuitive, protective, nostalgic, sensitive, remembers emotional details, withdraws when hurt, values emotional safety, deeply affected by relationship dynamics",

"Leo": "expressive, proud, warm-hearted, attention-aware, wants appreciation, notices when effort is overlooked, generous with affection, emotionally driven by recognition and connection",

"Virgo": "analytical, self-critical, observant, improvement-focused, processes emotions through problem-solving, notices flaws and inconsistencies, overthinks details, seeks understanding before action",

"Libra": "relationship-oriented, diplomatic, harmony-seeking, indecisive, avoids conflict, values mutual effort, highly aware of social dynamics, struggles when relationships feel unbalanced",

"Scorpio": "intense, private, emotionally deep, all-or-nothing, highly protective of vulnerability, struggles with trust, feels emotions strongly but reveals them selectively, values loyalty above words",

"Sagittarius": "freedom-seeking, adventurous, optimistic, blunt, dislikes feeling restricted, seeks perspective during emotional situations, processes feelings through movement, exploration, and future possibilities",

"Capricorn": "disciplined, ambitious, practical, emotionally reserved, focuses on responsibility during emotional stress, struggles to ask for help, values competence, often suppresses feelings to stay productive",

"Aquarius": "independent, unconventional, future-focused, emotionally detached when overwhelmed, intellectualizes feelings, values autonomy, questions social expectations, seeks distance before emotional clarity",

"Pisces": "imaginative, empathetic, dreamy, emotionally porous, absorbs surrounding emotions, escapes into imagination when overwhelmed, deeply sensitive to atmosphere, values emotional connection and meaning"

}


with open("prompt.txt", "r", encoding="utf-8") as f:
    MASTER_PROMPT = f.read()

target_date = (
    datetime.utcnow().date() + timedelta(days=1)
).isoformat()

yesterday = (
    datetime.utcnow().date() - timedelta(days=1)
).isoformat()

failed_signs = []
successful_signs = []
total_uploaded = 0

for sign in SIGNS:

    print(f"\n========== {sign} ==========\n")

    mood_format = "\n\n".join(
        [f"===MOOD: {m}===\nWrite horoscope here" for m in MOODS]
    )

    previous = (
        supabase.table("horoscopes")
        .select("mood,content")
        .eq("horoscope_date", yesterday)
        .eq("sign", sign)
        .execute()
    )

    previous_text = ""

    if previous.data:

        for row in previous.data:

            previous_text += f"""

===PREVIOUS MOOD: {row['mood']}===

{row['content']}
"""

    prompt = f"""
{MASTER_PROMPT}

IMPORTANT:

Generate horoscopes ONLY for:
{sign}

Sign personality:
{SIGN_TRAITS[sign]}

YESTERDAY'S READINGS

{previous_text}

CRITICAL DAILY VARIATION RULE

Do not rewrite, paraphrase, or slightly modify yesterday's reading.

For each mood:

- use a different emotional situation
- use a different emotional trigger
- use a different social interaction
- use a different internal conflict
- use a different concrete scene

Keep the emotional identity of the mood the same.

Change the situation.

Generate ALL these moods:
{", ".join(MOODS)}

OUTPUT FORMAT EXACTLY:

{mood_format}

RULES:
- Generate all 15 moods exactly once
- Keep each mood header EXACTLY as written
- No JSON
- No markdown code blocks
- No explanations
- No intro text
- No ending text
- Output only mood sections
"""

    try:

        print("Generating...")

        completion = None

        for attempt in range(3):

            try:

                print(f"API Attempt {attempt + 1}")

                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=1.0,
                    max_tokens=5000
                )

                break

            except Exception as e:

                print(f"API FAILED: {str(e)}")

                if attempt == 2:
                    failed_signs.append(sign)
                    raise

                time.sleep(5)

        text = completion.choices[0].message.content.strip()

        print("Parsing Sections...")

        sections = re.split(r"===MOOD:\s*", text)

        horoscopes = []

        for section in sections:

            section = section.strip()

            if not section:
                continue

            if "===" not in section:
                continue

            mood, content = section.split("===", 1)

            mood = mood.strip()
            content = content.strip()

            if not mood or not content:
                continue

            horoscopes.append({
                "mood": mood,
                "content": content
            })

        required_moods = set(MOODS)
        returned_moods = {h["mood"] for h in horoscopes}

        if required_moods != returned_moods:

            print(f"MISSING OR DUPLICATE MOODS FOR {sign}")
            print("Expected:", required_moods)
            print("Returned:", returned_moods)

            failed_signs.append(sign)
            continue

        if len(horoscopes) != 15:

            print(f"INVALID MOOD COUNT FOR {sign}")
            failed_signs.append(sign)
            continue

        print("Uploading...")

        count = 0

        for item in horoscopes:

            supabase.table("horoscopes").upsert(
                {
                    "horoscope_date": target_date,
                    "sign": sign,
                    "mood": item["mood"],
                    "content": item["content"]
                },
                on_conflict="horoscope_date,sign,mood"
            ).execute()

            count += 1

        successful_signs.append(sign)
        total_uploaded += count

        print(f"SUCCESS: Uploaded {count}")

    except Exception as e:

        print("FAILED:")
        print(str(e))

        failed_signs.append(sign)

    print("Waiting before next sign...\n")
    time.sleep(8)

print("\n========================")
print("GENERATION COMPLETE")
print("========================")

print(f"TOTAL UPLOADED: {total_uploaded}")
print(f"SUCCESSFUL SIGNS: {len(successful_signs)}")

if total_uploaded != 180:
    raise Exception(
        f"Expected 180 readings, got {total_uploaded}"
    )

if failed_signs:
    print("\nFAILED SIGNS:")
    print(sorted(list(set(failed_signs))))
else:
    print("\nALL SIGNS GENERATED SUCCESSFULLY")
