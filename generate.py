import os
import re
import time
import random
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

# ── TOKEN BUDGET ──────────────────────────────────────────────────────────────
# Groq free tier: 100,000 tokens/day
# Budget per sign: ~6,500 tokens (prompt ~800 in + output ~1,600 out = ~2,400 × safety buffer)
# 12 signs × 6,500 = 78,000 — leaves 22,000 headroom for any regens
# If we exceed DAILY_TOKEN_LIMIT mid-run we stop cleanly instead of burning retries

DAILY_TOKEN_LIMIT  = 90_000   # stop before hitting the hard wall
TOKEN_SAFETY_STOP  = 85_000   # warn and pause if we cross this
tokens_used        = 0        # running total tracked from API responses

# ── SIMILARITY CONFIG ─────────────────────────────────────────────────────────
# Raised from 0.35 → 0.45 so we only flag genuinely repetitive outputs,
# not just outputs that share common English words.
# Cross-day: no API regen — we mutate the flagged sentence directly in Python.
# Cross-mood: same mutation approach, zero extra API calls.

SIMILARITY_THRESHOLD = 0.45

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

# 36 unique scenes — one assigned per mood, no repeats within a run
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
    "laughing during a conversation then wondering why it bothered them on the drive home",
    "someone asking a simple question that landed on something unhealed",
    "rearranging something small on their desk before starting something difficult",
    "saying they were fine and meaning most of it",
    "skipping a social event and feeling quieter than expected afterward",
    "reading an old message out of some habit they hadn't named yet",
    "writing a long reply then cutting it down to three words",
    "deciding not to bring something up and immediately second-guessing that",
    "walking into a room and pausing before remembering why they came",
    "noticing they had been holding their jaw tight for the last hour",
    "putting off one task by completing three smaller ones instead",
    "closing a conversation they started because it wasn't going the way they hoped",
    "rehearsing what they would say before a call that turned out to be nothing",
    "finishing a meal without tasting it because their mind was elsewhere",
    "turning down plans then sitting with the silence longer than expected",
    "noticing someone's tone shift and spending the rest of the day decoding it",
    "writing something down to remember it and then losing the note",
    "getting to the end of a page without reading a single word",
    "making coffee and letting it go cold while sitting with a thought",
    "leaving early from something they had been looking forward to",
    "starting to explain something and stopping because it would take too long",
    "catching themselves smiling at something and immediately feeling guilty for it",
    "sending the message and then wishing they had waited one more minute",
    "agreeing to something and realizing only afterward that they didn't want to",
]

# 27 domains — one assigned per mood (15 used, rest are spare for variety across days)
EMOTIONAL_DOMAINS = [
    "workplace dynamics", "friendship tension", "family relationships",
    "creative frustration", "financial stress", "decision fatigue",
    "social awkwardness", "burnout", "loneliness in company",
    "nostalgia triggered by something ordinary", "self-image", "ambition",
    "routine", "independence", "guilt", "avoidance", "personal boundaries",
    "identity shifts", "long-term relationship drift", "dating uncertainty",
    "professional envy", "parental expectations",
    "the weight of being the dependable one",
    "growing apart from a friend slowly",
    "the gap between who you are and who you perform",
    "unfinished creative work", "the cost of always being the one who checks in",
]


# ── SIMILARITY HELPERS ────────────────────────────────────────────────────────

STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "you","your","it","its","is","are","was","were","be","been","being",
    "have","has","had","do","does","did","that","this","they","them","their",
    "there","then","than","when","what","who","how","so","if","as","by",
    "from","not","no","can","will","would","could","should","just","more",
    "even","still","some","one","every","like","about","after","before",
    "into","out","up","down","all","any","each","i","my","me","we","our",
}

def tokenize(text: str) -> set:
    words = re.findall(r"[a-z]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}

def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def similarity(text_a: str, text_b: str) -> float:
    return jaccard(tokenize(text_a), tokenize(text_b))

def find_most_similar_sentence(content: str, reference: str) -> str:
    """Return the sentence in `content` most similar to any sentence in `reference`."""
    ref_tokens = tokenize(reference)
    sentences  = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if len(s.strip()) > 20]
    if not sentences:
        return ""
    return max(sentences, key=lambda s: jaccard(tokenize(s), ref_tokens))

def replace_sentence(content: str, old_sentence: str, new_sentence: str) -> str:
    """Swap one sentence in content for another."""
    return content.replace(old_sentence, new_sentence, 1)


# ── MUTATION BANK ─────────────────────────────────────────────────────────────
# When similarity is too high we swap the most-similar sentence for a
# pre-written alternative. No API call needed — zero tokens burned.

MUTATION_SENTENCES = {
    "Ambitious": [
        "The gap between where you are and where you want to be feels sharper today, and that sharpness is useful.",
        "You caught yourself calculating the cost of staying still and didn't like the number.",
        "The version of yourself that hesitates is getting harder to justify.",
    ],
    "Adventurous": [
        "Something about today makes the usual route feel like a waste of possibility.",
        "You keep returning to a thought that starts with 'what if I just went'.",
        "The itch isn't restlessness — it's the specific feeling of having something to prove to yourself.",
    ],
    "Creative": [
        "The idea arrived while you were doing something completely unrelated, which is always how it works.",
        "You've been circling the same blank page long enough to know the problem isn't the page.",
        "There's a version of this that's already finished in your head — getting it out is the work.",
    ],
    "Rebellious": [
        "You said yes when you meant something else entirely, and your body registered it before your brain did.",
        "The rule was never explained, which is the only reason you're still following it.",
        "Today the version of you that stops asking permission feels closer to the surface.",
    ],
    "Confident": [
        "You made the decision before the conversation ended and didn't feel the need to explain why.",
        "Something that would have unsettled you a month ago barely registered today.",
        "The opinion landed and you disagreed without needing anyone else to agree with you first.",
    ],
    "Anxious": [
        "You sent the message and immediately wished you could see the exact moment they read it.",
        "The thing you keep calling overthinking is actually just noticing what others miss.",
        "You ran the scenario forward three times and still couldn't find a version where it went smoothly.",
    ],
    "Sad": [
        "The feeling arrived without warning, the way some feelings do — specific and completely uncalled for.",
        "You weren't thinking about it and then you were, and suddenly the room felt different.",
        "There's a kind of sad that doesn't ask for anything — it just sits there until it's ready to leave.",
    ],
    "Lonely": [
        "You were surrounded by people and still somehow the only one in the room.",
        "The conversation was fine. You just kept waiting for it to become something else.",
        "It's not that no one was there — it's that no one was there in the right way.",
    ],
    "Romantic": [
        "You noticed something small about them that they probably didn't know you noticed.",
        "The feeling is quiet but it's been consistent, which is more than you can say for most things.",
        "You kept the conversation going longer than necessary and didn't mind at all.",
    ],
    "Nostalgic": [
        "Something ordinary today — a smell, a font, a specific quality of light — put you somewhere else entirely.",
        "You didn't expect to miss it this much, and the unexpectedness made it worse.",
        "The memory wasn't sad exactly, just carrying the specific weight of something that no longer exists.",
    ],
    "Exhausted": [
        "You did everything that was asked of you and still felt like you'd left something undone.",
        "The tiredness today is the kind that sleep doesn't fix.",
        "You answered every message and somehow came away feeling more behind than before.",
    ],
    "Lazy": [
        "The task exists. You are aware of the task. That is as far as things have progressed.",
        "Everything that needs doing will still need doing in an hour, which is its own kind of comfort.",
        "You started to get up and then made a very reasonable argument for why now wasn't the time.",
    ],
    "Peaceful": [
        "Nothing is resolved — you've just stopped needing it to be resolved today.",
        "The quiet today has a different quality, like you finally stopped bracing for something.",
        "You let three things go and only noticed afterward that you'd done it.",
    ],
    "Daydreamy": [
        "You spent twenty minutes somewhere that doesn't exist yet and came back refreshed.",
        "The meeting continued and you were technically present for all of it.",
        "Your attention kept drifting toward a version of things you haven't built yet.",
    ],
    "Irritated": [
        "The specific thing that bothered you wasn't the thing — it was everything behind it.",
        "You explained it once, clearly, and are now being asked to explain it again.",
        "The patience is there. It's just being used on something that doesn't deserve this much of it.",
    ],
}


# ── PROMPT BUILDER ────────────────────────────────────────────────────────────
# Target: ~750-850 input tokens per call (was ~1,500+)
# Key cuts: no OUTPUT_RULES list, no QUALITY_CHECKS list, no SHAREABLE examples,
# no yesterday's full content — just the 3 structural things the model needs:
# sign identity, per-mood assignments, and format.

def build_prompt(
    sign: str,
    scene_assignments: dict,
    domain_assignments: dict,
    used_scenes_yesterday: list,
) -> str:

    traits     = SIGN_TRAITS[sign]
    blind_spot = SIGN_BLIND_SPOTS[sign]

    # One line per mood: tone | scene | domain
    mood_lines = "\n".join(
        f"{mood} [{MOOD_TONE[mood]}] → scene: {scene_assignments[mood]} | domain: {domain_assignments[mood]}"
        for mood in MOODS
    )

    # Only send scene NAMES from yesterday, not full content — saves ~2,000 tokens
    avoid_block = ""
    if used_scenes_yesterday:
        avoid_block = f"Avoid these scenes used yesterday: {'; '.join(used_scenes_yesterday[:8])}"

    # Output skeleton — tells the model exactly what to produce
    output_skeleton = "\n\n".join(
        f"===MOOD: {m}===\n[write here]" for m in MOODS
    )

    prompt = f"""Write 15 emotionally intelligent horoscopes for {sign}.

SIGN: {traits}. Blind spot: {blind_spot}.
Every horoscope must feel specific to this sign — recognizable from the situation alone.

RULES (non-negotiable):
- 6 sentences, 150–170 words each
- Never name the mood directly
- Each must include its assigned scene and domain
- Each must have one emotionally shareable line
- Tone must match the mood's register
- Write like observing a real person, not generating content
- No clichés: no "trust the universe", "emotional growth", "new opportunities"

MOOD ASSIGNMENTS (use exactly as given):
{mood_lines}

{avoid_block}

Output only the sections below. No intro. No explanation. No JSON.

{output_skeleton}"""

    return prompt.strip()


# ── SIMILARITY FIX (no API call) ─────────────────────────────────────────────

def fix_similarity(mood: str, content: str, label: str) -> str:
    """
    Replace the most-similar sentence with a pre-written alternative.
    Returns the mutated content. Uses zero API tokens.
    """
    candidates = MUTATION_SENTENCES.get(mood, [])
    if not candidates:
        return content  # can't fix, keep as-is

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if len(s.strip()) > 20]
    if not sentences:
        return content

    # Find the longest sentence (most likely to be the redundant one)
    target = max(sentences, key=len)

    # Pick mutation not already in the content
    for candidate in random.sample(candidates, len(candidates)):
        if candidate not in content:
            fixed = replace_sentence(content, target, candidate)
            print(f"    ✎ Mutated [{mood}] ({label}) — swapped sentence, no API call used.")
            return fixed

    return content  # all candidates already present, keep original


# ── API CALL WITH TOKEN TRACKING ─────────────────────────────────────────────

def parse_rate_limit_wait(msg: str) -> int:
    """
    Extract the exact wait time from a Groq 429 error message.
    Handles formats: '27m55.296s', '1h9m8s', '45.5s'
    Returns wait seconds + 10s buffer, or 60s default.
    """
    # e.g. "1h9m8.063s"
    match = re.search(r"(\d+)h(\d+)m[\d.]+s", msg)
    if match:
        return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + 10

    # e.g. "27m55.296s"
    match = re.search(r"(\d+)m[\d.]+s", msg)
    if match:
        return int(match.group(1)) * 60 + 10

    # e.g. "45.5s"
    match = re.search(r"([\d.]+)s", msg)
    if match:
        return int(float(match.group(1))) + 10

    return 60  # safe default


def call_api(prompt: str) -> tuple[str | None, int]:
    """
    Returns (response_text, tokens_used) or (None, 0) on unrecoverable failure.
    On rate limit: reads the exact wait time from the error, sleeps, then retries.
    Never skips — always waits and tries again.
    """
    global tokens_used

    if tokens_used >= TOKEN_SAFETY_STOP:
        print(f"  ⛔ Token safety stop reached ({tokens_used:,}/{DAILY_TOKEN_LIMIT:,}). Halting API calls.")
        return None, 0

    attempt = 0
    while True:
        attempt += 1
        try:
            print(f"  API Attempt {attempt} (tokens used so far: {tokens_used:,})")
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=1.0,
                max_tokens=2200,
            )
            used = resp.usage.total_tokens if resp.usage else 0
            tokens_used += used
            text = resp.choices[0].message.content.strip()
            print(f"  ✓ Tokens this call: {used:,} | Total today: {tokens_used:,}")
            return text, used

        except Exception as e:
            msg = str(e)

            if "rate_limit_exceeded" in msg or "429" in msg:
                wait = parse_rate_limit_wait(msg)
                # Convert to readable format for the log
                h, rem = divmod(wait, 3600)
                m, s   = divmod(rem, 60)
                if h:
                    wait_str = f"{h}h {m}m {s}s"
                elif m:
                    wait_str = f"{m}m {s}s"
                else:
                    wait_str = f"{s}s"
                print(f"  ⏳ Rate limited. Waiting {wait_str} then retrying (attempt {attempt})...")
                time.sleep(wait)
                continue  # retry after sleeping — no sign is ever skipped

            # Non-rate-limit error — retry up to 3 times with short delay
            print(f"  API ERROR (attempt {attempt}): {msg}")
            if attempt >= 3:
                print("  ✗ Failed after 3 attempts. Giving up on this call.")
                return None, 0
            time.sleep(5)


# ── PARSE SECTIONS ────────────────────────────────────────────────────────────

def parse_sections(text: str) -> dict | None:
    sections = re.split(r"===MOOD:\s*", text)
    result   = {}
    for section in sections:
        section = section.strip()
        if not section or "===" not in section:
            continue
        mood, content = section.split("===", 1)
        mood    = mood.strip()
        content = content.strip()
        if mood in MOODS and content:
            result[mood] = content
    if set(result.keys()) != set(MOODS):
        return None
    return result


# ── GENERATE FOR ONE SIGN ─────────────────────────────────────────────────────

def generate_for_sign(sign: str, previous_map: dict) -> list | None:

    # Assign unique scenes and domains for this sign's run
    scene_assignments  = dict(zip(MOODS, random.sample(SCENES, len(MOODS))))
    domain_assignments = dict(zip(MOODS, random.sample(EMOTIONAL_DOMAINS, len(MOODS))))

    # Extract scene NAMES from yesterday's content for avoidance hint
    # (we don't send the full content — saves ~2,000 tokens per sign)
    used_scenes_yesterday = list(previous_map.keys())  # mood names as proxy

    prompt = build_prompt(sign, scene_assignments, domain_assignments, used_scenes_yesterday)

    print("  Generating...")
    raw, _ = call_api(prompt)
    if not raw:
        return None

    parsed = parse_sections(raw)
    if not parsed:
        print("  FAILED: Could not parse all 15 moods.")
        return None

    # ── Cross-day similarity check (fix via mutation, no API call) ────────────
    print("  Checking cross-day similarity...")
    for mood, content in list(parsed.items()):
        yesterday_content = previous_map.get(mood, "")
        if not yesterday_content:
            continue
        score = similarity(content, yesterday_content)
        if score >= SIMILARITY_THRESHOLD:
            print(f"  ⚠ Cross-day too similar [{mood}]: {round(score, 3)} — fixing...")
            parsed[mood] = fix_similarity(mood, content, "cross-day")

    # ── Cross-mood similarity check (fix via mutation, no API call) ───────────
    print("  Checking cross-mood similarity...")
    mood_list = list(parsed.keys())
    for i in range(len(mood_list)):
        for j in range(i + 1, len(mood_list)):
            ma, mb = mood_list[i], mood_list[j]
            score  = similarity(parsed[ma], parsed[mb])
            if score >= SIMILARITY_THRESHOLD:
                print(f"  ⚠ Cross-mood too similar [{ma}] ↔ [{mb}]: {round(score, 3)} — fixing...")
                parsed[mb] = fix_similarity(mb, parsed[mb], f"cross-mood vs {ma}")

    return [{"mood": m, "content": c} for m, c in parsed.items()]


# ── MAIN LOOP ─────────────────────────────────────────────────────────────────

target_date = (datetime.utcnow().date() + timedelta(days=1)).isoformat()
yesterday   = (datetime.utcnow().date() - timedelta(days=1)).isoformat()

failed_signs     = []
successful_signs = []
total_uploaded   = 0

for sign in SIGNS:

    print(f"\n========== {sign} ==========")

    # Fetch yesterday's readings
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
        time.sleep(8)
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

    print(f"  Waiting before next sign... (tokens used: {tokens_used:,})")
    time.sleep(8)

# ── SUMMARY ───────────────────────────────────────────────────────────────────

print("\n========================")
print("GENERATION COMPLETE")
print("========================")
print(f"TOTAL UPLOADED:    {total_uploaded}")
print(f"SUCCESSFUL SIGNS:  {len(successful_signs)}")
print(f"TOTAL TOKENS USED: {tokens_used:,}")

if total_uploaded != 180:
    raise Exception(f"Expected 180 readings, got {total_uploaded}")

if failed_signs:
    print("\nFAILED SIGNS:")
    print(sorted(list(set(failed_signs))))
else:
    print("\nALL SIGNS GENERATED SUCCESSFULLY")
