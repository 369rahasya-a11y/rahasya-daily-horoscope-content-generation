import os
import re
import time
import random
from collections import defaultdict
from datetime import datetime, timedelta

from groq import Groq
from supabase import create_client

# ── ENV ───────────────────────────────────────────────────────────────────────

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
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("CONNECTED")

# ── SIMILARITY CONFIG ─────────────────────────────────────────────────────────

# Jaccard similarity threshold — 0.0 = anything goes, 1.0 = must be identical
# 0.35 means: if two outputs share more than 35% of their words, flag as too similar
SIMILARITY_THRESHOLD = 0.35

# Max regeneration attempts per mood before giving up and keeping best version
MAX_REGEN_ATTEMPTS = 2

# ── DATA ──────────────────────────────────────────────────────────────────────

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

MOODS = [
    "Ambitious", "Adventurous", "Creative", "Rebellious", "Confident",
    "Anxious", "Sad", "Lonely", "Romantic", "Nostalgic",
    "Exhausted", "Lazy", "Peaceful", "Daydreamy", "Irritated"
]

MOOD_TONE = {
    "Ambitious":   "bold, decisive, emotionally sharp",
    "Adventurous": "energetic, restless, forward-pulling",
    "Creative":    "curious, internally alive, slightly distracted",
    "Rebellious":  "sharp, resistant, quietly defiant",
    "Confident":   "grounded, clear-eyed, unbothered",
    "Anxious":     "warm, looping, hyper-aware of small details",
    "Sad":         "quiet, heavy, honest without being dramatic",
    "Lonely":      "intimate, still, aching without self-pity",
    "Romantic":    "soft, attentive, emotionally open",
    "Nostalgic":   "reflective, bittersweet, triggered by small things",
    "Exhausted":   "flat, spacious, beyond the point of explaining",
    "Lazy":        "slow, unbothered, gently resistant",
    "Peaceful":    "calm, settled, quietly observant",
    "Daydreamy":   "drifting, gentle, half-present",
    "Irritated":   "taut, dry, specific about what's wrong",
}

SIGN_TRAITS = {
    "Aries":       "impulsive, competitive, action-oriented, impatient with stagnation",
    "Taurus":      "comfort-seeking, security-focused, resistant to sudden change, values stability",
    "Gemini":      "mentally restless, curious, conversational, conflicted by multiple possibilities",
    "Cancer":      "emotionally protective, sentimental, attachment-focused, deeply affected by atmosphere",
    "Leo":         "pride-driven, visibility-aware, expressive, needs recognition to feel seen",
    "Virgo":       "analytical, self-critical, observant, improvement-oriented",
    "Libra":       "relationship-focused, harmony-seeking, socially aware, chronically indecisive",
    "Scorpio":     "emotionally intense, private, protective of vulnerability, all-or-nothing",
    "Sagittarius": "freedom-seeking, truth-driven, adventurous, resistant to feeling caged",
    "Capricorn":   "disciplined, achievement-focused, responsible, emotionally restrained",
    "Aquarius":    "independent, unconventional, intellectually driven, emotionally detached at times",
    "Pisces":      "imaginative, emotionally absorbent, intuitive, prone to escapism",
}

SIGN_BLIND_SPOTS = {
    "Aries":       "acts before processing, mistakes speed for strength",
    "Taurus":      "confuses comfort with avoidance, stays past the expiry date",
    "Gemini":      "talks around feelings instead of sitting with them",
    "Cancer":      "protects others so well they forget to ask for the same",
    "Leo":         "performs okayness rather than admitting they're not",
    "Virgo":       "fixes everything around the actual problem",
    "Libra":       "keeps the peace so long they lose track of their own position",
    "Scorpio":     "controls the narrative to avoid being surprised by pain",
    "Sagittarius": "reframes difficulty as freedom to avoid grieving it",
    "Capricorn":   "measures emotion by productivity, ignores what doesn't have a use",
    "Aquarius":    "intellectualizes feelings until they feel like someone else's",
    "Pisces":      "absorbs other people's reality until their own goes blurry",
}

# 36 scenes — enough to assign unique ones per mood (15) with plenty of spare
SCENES = [
    "rereading a message three times before deciding it sounded too eager",
    "staring at an unfinished task without opening it",
    "sitting in silence after a conversation ended too cleanly",
    "opening an app and forgetting the reason within seconds",
    "deleting a paragraph and starting over from the first word",
    "pretending to be busy to avoid a conversation they weren't ready for",
    "leaving a tab open all day without acting on it",
    "cleaning the kitchen instead of dealing with what actually needed attention",
    "changing their mind halfway through a decision and not telling anyone",
    "overhearing a name they hadn't thought about in months",
    "checking the time repeatedly without registering what it said",
    "typing a reply and closing the thread without sending it",
    "laughing during a conversation and then wondering why it still bothered them on the drive home",
    "someone asking a simple question that accidentally landed on something unhealed",
    "rearranging something small on their desk before starting something difficult",
    "saying 'I'm fine' and meaning most of it",
    "skipping a social event and feeling quieter than expected afterward",
    "reading an old message not to feel sad but out of some habit they hadn't named yet",
    "writing a long reply and then cutting it down to three words",
    "deciding not to bring something up and immediately second-guessing that",
    "walking into a room and pausing before remembering why they came",
    "noticing they'd been holding their jaw tight for the last hour",
    "putting off one task by completing three smaller ones instead",
    "closing a conversation they initiated because it wasn't going the way they hoped",
    "rehearsing what they'd say before a call that turned out to be nothing",
    "finishing a meal without tasting it because their mind was somewhere else",
    "keeping a tab open for three days as a way of pretending they'd decided",
    "turning down plans and then sitting with the silence longer than they expected",
    "noticing someone's tone shift and spending the rest of the day trying to decode it",
    "writing something down so they wouldn't forget it and then losing the note",
    "getting to the end of a page and realizing they hadn't read a single word",
    "sending a voice note instead of typing because they didn't trust their own words",
    "making coffee and letting it go cold while they sat with a thought",
    "leaving early from something they'd been looking forward to",
    "starting to explain something and stopping because it would take too long",
    "catching themselves smiling at something and immediately feeling guilty for it",
]

EMOTIONAL_DOMAINS = [
    "workplace dynamics", "friendship tension", "family relationships",
    "creative frustration", "financial stress", "decision fatigue",
    "social awkwardness", "burnout", "loneliness in company",
    "nostalgia triggered by something ordinary", "self-image", "ambition",
    "routine", "independence", "guilt", "avoidance", "personal boundaries",
    "identity shifts", "long-term relationship drift", "dating uncertainty",
    "unfinished creative work", "professional envy", "parental expectations",
    "the weight of being the dependable one", "growing apart from a friend slowly",
    "not recognising yourself in an old photo", "the gap between who you are and who you perform",
]

SHAREABLE_LINE_EXAMPLES = [
    "Some people stop texting because they lose interest. Others stop because they started caring too much.",
    "Not every unanswered question needs an answer — some just reveal what you've been afraid to admit.",
    "It's strange how quickly peace arrives when you stop waiting for someone to become who they promised they'd be.",
    "Sometimes the hardest boundary is accepting that someone can disappoint you without being a bad person.",
    "You keep pretending it doesn't affect you because reacting would make it feel too real.",
    "The task wasn't difficult — starting it felt like admitting it mattered.",
    "There's a version of moving on that looks exactly like staying busy.",
    "You're not avoiding it. You're just waiting to feel ready, which is the same thing.",
]

OUTPUT_RULES = [
    "Never directly mention the mood name anywhere in the text.",
    "Exactly 6 sentences.",
    "Between 150 and 170 words.",
    "At least one sentence must feel emotionally recognizable — worth saving or rereading.",
    "Use specific behavior and concrete moments, not abstract emotional statements.",
    "Do not repeat the same emotional situation, trigger, or scene across moods.",
    "Do not use: 'Things are changing', 'trust the universe', 'new opportunities', 'emotional growth'.",
    "Do not use: checking the phone, scrolling social media, fear of failure, as recurring anchors.",
    "Every mood must feel like a different person having a different day.",
    "Write as if observing a real person — not generating horoscope content.",
]

QUALITY_CHECKS = [
    "Is this clearly shaped by the zodiac sign's traits and blind spots?",
    "Does it contain a concrete real-life scene, not just abstract emotion?",
    "Is there at least one line worth screenshotting or sharing?",
    "Does the emotional conflict feel human and specific, not generic?",
    "Does it sound like a real observation, not a template being filled?",
    "If a similar theme appeared in an earlier mood, is it expressed through a different emotional lens?",
]


# ── SIMILARITY HELPERS ────────────────────────────────────────────────────────

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "you", "your", "it", "its", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "that", "this", "they", "them", "their", "there", "then", "than",
    "when", "what", "who", "how", "so", "if", "as", "by", "from", "not",
    "no", "can", "will", "would", "could", "should", "just", "more",
    "even", "still", "some", "one", "every", "like", "about", "after",
    "before", "into", "out", "up", "down", "all", "any", "each",
}

def tokenize(text: str) -> set:
    """Lowercase words, strip punctuation, remove stopwords."""
    words = re.findall(r"[a-z]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}

def jaccard(set_a: set, set_b: set) -> float:
    """Jaccard similarity between two word sets. Returns 0.0–1.0."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union

def find_similar_pair(horoscopes: list, threshold: float) -> tuple | None:
    """
    Compare every pair of horoscopes.
    Returns (mood_a, mood_b, score) for the first pair above threshold, else None.
    """
    tokens = {h["mood"]: tokenize(h["content"]) for h in horoscopes}
    moods  = [h["mood"] for h in horoscopes]
    for i in range(len(moods)):
        for j in range(i + 1, len(moods)):
            score = jaccard(tokens[moods[i]], tokens[moods[j]])
            if score >= threshold:
                return (moods[i], moods[j], round(score, 3))
    return None

def is_too_similar_to_yesterday(content: str, yesterday_content: str, threshold: float) -> bool:
    """Returns True if today's content is too close to yesterday's for the same mood."""
    return jaccard(tokenize(content), tokenize(yesterday_content)) >= threshold


# ── PROMPT BUILDER ────────────────────────────────────────────────────────────

def build_prompt(
    sign: str,
    previous_text: str,
    scene_assignments: dict,        # mood -> scene string
    domain_assignments: dict,       # mood -> domain string
    flagged_moods: list = None,     # moods that need to be regenerated
    existing_outputs: dict = None,  # mood -> content (for context during regen)
) -> str:

    traits     = SIGN_TRAITS[sign]
    blind_spot = SIGN_BLIND_SPOTS[sign]

    mood_tone_block = "\n".join(
        f"  {mood}: {tone}" for mood, tone in MOOD_TONE.items()
    )

    # Inject per-mood scene + domain assignments directly into the prompt
    mood_assignment_block = "\n".join(
        f"  {mood}: scene → {scene_assignments[mood]} | domain → {domain_assignments[mood]}"
        for mood in MOODS
    )

    rules_block    = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(OUTPUT_RULES))
    checks_block   = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(QUALITY_CHECKS))
    shareable_block = "\n".join(f'  "{line}"' for line in SHAREABLE_LINE_EXAMPLES)

    # Full output block or regeneration-only block
    if flagged_moods:
        mood_output_block = "\n\n".join(
            f"===MOOD: {m}===\n[horoscope here]" for m in flagged_moods
        )
        regen_context = ""
        if existing_outputs:
            regen_context = "ALREADY ACCEPTED MOODS (do NOT reproduce these — they are kept as-is):\n"
            for m, c in existing_outputs.items():
                if m not in flagged_moods:
                    regen_context += f"\n===MOOD: {m}===\n{c}\n"
        target_moods_line = f"Regenerate ONLY these moods (they were too similar to another output): {', '.join(flagged_moods)}"
    else:
        mood_output_block = "\n\n".join(
            f"===MOOD: {m}===\n[horoscope here]" for m in MOODS
        )
        regen_context      = ""
        target_moods_line  = f"Generate ALL 15 moods for {sign}."

    variation_block = ""
    if previous_text:
        variation_block = f"""
YESTERDAY'S READINGS (variation reference — do NOT reuse situation, trigger, scene, or conflict):
{previous_text}
"""

    prompt = f"""You are writing emotionally intelligent horoscope content.
Goal: emotionally intelligent introspection disguised as astrology.
Target reactions: "this is weirdly accurate", "I needed to hear this", "this sounds exactly like me."

━━━ SIGN ━━━
{sign}
Personality: {traits}
Emotional blind spot: {blind_spot}

The sign's personality and blind spot must shape every mood's emotional conflict and behavior.
The sign should be recognizable from the situation alone.

━━━ MOOD TONE GUIDE ━━━
{mood_tone_block}

━━━ MANDATORY SCENE + DOMAIN ASSIGNMENTS ━━━
Each mood MUST use its assigned scene and emotional domain below.
Do not swap them. Do not ignore them.
{mood_assignment_block}

━━━ SHAREABLE LINE REQUIREMENT ━━━
At least one sentence per horoscope must feel worth saving or rereading.
Aim for this register (do not copy directly):
{shareable_block}

━━━ OUTPUT RULES ━━━
{rules_block}

━━━ QUALITY CHECK ━━━
Before writing each horoscope, confirm:
{checks_block}
Rewrite if any check fails.

{variation_block}
{regen_context}

━━━ OUTPUT ━━━
{target_moods_line}
No JSON. No markdown. No explanations. No intro or closing text.
Output only mood sections:

{mood_output_block}
"""
    return prompt.strip()


# ── SINGLE SIGN GENERATOR ─────────────────────────────────────────────────────

def generate_for_sign(sign: str, previous_map: dict) -> list | None:
    """
    Generate, validate, similarity-check, and if needed regenerate
    all 15 moods for a given sign.
    Returns list of {mood, content} dicts, or None on failure.
    """

    # Assign a unique random scene to each mood for this run
    shuffled_scenes  = random.sample(SCENES, len(MOODS))
    scene_assignments = {mood: shuffled_scenes[i] for i, mood in enumerate(MOODS)}

    # Assign a unique random domain to each mood for this run
    shuffled_domains  = random.sample(EMOTIONAL_DOMAINS, len(MOODS))
    domain_assignments = {mood: shuffled_domains[i] for i, mood in enumerate(MOODS)}

    # Build yesterday's text block
    previous_text = ""
    for mood, content in previous_map.items():
        previous_text += f"\n===PREVIOUS MOOD: {mood}===\n{content}\n"

    def call_api(prompt: str) -> str | None:
        for attempt in range(3):
            try:
                print(f"  API Attempt {attempt + 1}")
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=1.0,
                    max_tokens=5000
                )
                return completion.choices[0].message.content.strip()
            except Exception as e:
                print(f"  API FAILED: {e}")
                if attempt < 2:
                    time.sleep(5)
        return None

    def parse_sections(text: str, expected_moods: list) -> dict | None:
        """Parse mood sections from raw text. Returns {mood: content} or None."""
        sections = re.split(r"===MOOD:\s*", text)
        result   = {}
        for section in sections:
            section = section.strip()
            if not section or "===" not in section:
                continue
            mood, content = section.split("===", 1)
            mood    = mood.strip()
            content = content.strip()
            if mood and content:
                result[mood] = content
        if set(result.keys()) != set(expected_moods):
            return None
        return result

    # ── Step 1: Initial generation ────────────────────────────────────────────
    print("  Generating...")
    prompt = build_prompt(sign, previous_text, scene_assignments, domain_assignments)
    raw    = call_api(prompt)
    if not raw:
        print("  FAILED: No API response.")
        return None

    parsed = parse_sections(raw, MOODS)
    if not parsed:
        print("  FAILED: Could not parse all 15 moods.")
        return None

    # ── Step 2: Cross-day similarity check ───────────────────────────────────
    print("  Checking cross-day similarity...")
    day_flagged = []
    for mood, content in parsed.items():
        yesterday_content = previous_map.get(mood, "")
        if yesterday_content and is_too_similar_to_yesterday(content, yesterday_content, SIMILARITY_THRESHOLD):
            score = jaccard(tokenize(content), tokenize(yesterday_content))
            print(f"  ⚠ Cross-day similarity too high for [{mood}]: {round(score, 3)}")
            day_flagged.append(mood)

    # ── Step 3: Cross-mood similarity check ──────────────────────────────────
    print("  Checking cross-mood similarity...")
    horoscope_list = [{"mood": m, "content": c} for m, c in parsed.items()]
    mood_flagged   = []

    pair = find_similar_pair(horoscope_list, SIMILARITY_THRESHOLD)
    while pair:
        mood_a, mood_b, score = pair
        print(f"  ⚠ Cross-mood similarity too high: [{mood_a}] ↔ [{mood_b}] = {score}")
        # Flag the second mood in the pair (keep the first)
        if mood_b not in mood_flagged:
            mood_flagged.append(mood_b)
        # Remove flagged mood from list temporarily to find next bad pair
        horoscope_list = [h for h in horoscope_list if h["mood"] not in mood_flagged]
        pair = find_similar_pair(horoscope_list, SIMILARITY_THRESHOLD)

    all_flagged = list(set(day_flagged + mood_flagged))

    # ── Step 4: Regenerate flagged moods ─────────────────────────────────────
    if all_flagged:
        print(f"  Regenerating {len(all_flagged)} flagged mood(s): {all_flagged}")

        for attempt in range(MAX_REGEN_ATTEMPTS):
            print(f"  Regen attempt {attempt + 1}/{MAX_REGEN_ATTEMPTS}")

            regen_prompt = build_prompt(
                sign,
                previous_text,
                scene_assignments,
                domain_assignments,
                flagged_moods=all_flagged,
                existing_outputs=parsed,
            )
            regen_raw = call_api(regen_prompt)
            if not regen_raw:
                print("  Regen API call failed.")
                break

            regen_parsed = parse_sections(regen_raw, all_flagged)
            if not regen_parsed:
                print("  Regen parse failed.")
                break

            # Merge regen results back in
            for mood, content in regen_parsed.items():
                parsed[mood] = content

            # Re-run both checks on the full updated set
            still_flagged = []

            for mood in all_flagged:
                yesterday_content = previous_map.get(mood, "")
                if yesterday_content and is_too_similar_to_yesterday(parsed[mood], yesterday_content, SIMILARITY_THRESHOLD):
                    still_flagged.append(mood)

            full_list = [{"mood": m, "content": c} for m, c in parsed.items()]
            pair = find_similar_pair(full_list, SIMILARITY_THRESHOLD)
            while pair:
                mood_a, mood_b, score = pair
                if mood_b not in still_flagged:
                    still_flagged.append(mood_b)
                full_list = [h for h in full_list if h["mood"] not in still_flagged]
                pair = find_similar_pair(full_list, SIMILARITY_THRESHOLD)

            if not still_flagged:
                print("  All similarity issues resolved.")
                break
            else:
                print(f"  Still flagged after regen: {still_flagged}")
                all_flagged = still_flagged

        else:
            print(f"  ⚠ Could not fully resolve similarity after {MAX_REGEN_ATTEMPTS} attempts — keeping best version.")

    return [{"mood": m, "content": c} for m, c in parsed.items()]


# ── MAIN LOOP ─────────────────────────────────────────────────────────────────

target_date = (datetime.utcnow().date() + timedelta(days=1)).isoformat()
yesterday   = (datetime.utcnow().date() - timedelta(days=1)).isoformat()

failed_signs     = []
successful_signs = []
total_uploaded   = 0

for sign in SIGNS:

    print(f"\n========== {sign} ==========")

    # Fetch yesterday's readings as a {mood: content} map
    previous = (
        supabase.table("horoscopes")
        .select("mood,content")
        .eq("horoscope_date", yesterday)
        .eq("sign", sign)
        .execute()
    )

    previous_map = {}
    if previous.data:
        for row in previous.data:
            previous_map[row["mood"]] = row["content"]

    horoscopes = generate_for_sign(sign, previous_map)

    if not horoscopes or len(horoscopes) != 15:
        print(f"  FAILED: Could not generate valid horoscopes for {sign}.")
        failed_signs.append(sign)
        continue

    print("  Uploading...")
    count = 0

    try:
        for item in horoscopes:
            supabase.table("horoscopes").upsert(
                {
                    "horoscope_date": target_date,
                    "sign": sign,
                    "mood": item["mood"],
                    "content": item["content"],
                },
                on_conflict="horoscope_date,sign,mood"
            ).execute()
            count += 1

        successful_signs.append(sign)
        total_uploaded += count
        print(f"  SUCCESS: Uploaded {count}")

    except Exception as e:
        print(f"  UPLOAD FAILED: {e}")
        failed_signs.append(sign)

    print("  Waiting before next sign...")
    time.sleep(8)

# ── SUMMARY ───────────────────────────────────────────────────────────────────

print("\n========================")
print("GENERATION COMPLETE")
print("========================")
print(f"TOTAL UPLOADED:    {total_uploaded}")
print(f"SUCCESSFUL SIGNS:  {len(successful_signs)}")

if total_uploaded != 180:
    raise Exception(f"Expected 180 readings, got {total_uploaded}")

if failed_signs:
    print("\nFAILED SIGNS:")
    print(sorted(list(set(failed_signs))))
else:
    print("\nALL SIGNS GENERATED SUCCESSFULLY")
