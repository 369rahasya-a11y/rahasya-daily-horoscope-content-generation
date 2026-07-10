import os
import sys
import json
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from groq import (
    Groq,
    RateLimitError,
    AuthenticationError,
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
)
from supabase import create_client

load_dotenv()  # no-op in CI where .env doesn't exist; loads it locally

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from constants import SIGNS, MOODS  # noqa: E402

from prompt_builder import build_prompt  # noqa: E402
from validators import validate_batch  # noqa: E402

GROQ_API_KEY = os.getenv("GROQ_API_KEY_GEN1")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not GROQ_API_KEY:
    raise Exception("GROQ_API_KEY_GEN1 missing")
if not SUPABASE_URL:
    raise Exception("SUPABASE_URL missing")
if not SUPABASE_KEY:
    raise Exception("SUPABASE_SERVICE_ROLE_KEY missing")

client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("CONNECTED")

# Generator 3 always targets the same date Generator 1 just wrote for.
# Generator 1 writes to tomorrow (UTC+1 day); Generator 3 runs right
# after and interprets that same batch -- same convention as
# Generator 2, run independently and in parallel with it.
target_date = (datetime.utcnow().date() + timedelta(days=1)).isoformat()

EXPECTED_MOODS = set(MOODS)

failed_signs = []
succeeded_signs = []
total_updated = 0


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------
# These exist so the sign-processing loop can react differently to
# different failure classes instead of treating every exception the
# same way (that blanket handling was Root Cause 2 -- see README/audit
# notes below).

class EmptyOrInvalidResponseError(Exception):
    """Raised when Groq returns a response with no usable content --
    empty string, whitespace only, or something that isn't JSON at
    all (e.g. an error page). This is the exact condition that used
    to reach json.loads() unchecked and surface as:
        Expecting value: line 1 column 1 (char 0)
    That message is json.loads() telling you its input was empty --
    it is not a JSON *formatting* problem, it's a missing-content
    problem, and it needs to be caught before parsing, not after."""
    pass


class QuotaExhaustedError(Exception):
    """Raised when Groq returns 429 and we've already waited out the
    indicated (or a reasonable default) reset window once. Signals
    the caller that retrying further sign requests is pointless for
    the rest of this run."""
    pass


def _estimate_tokens(text: str) -> int:
    """Rough, fast estimate (~4 chars/token) -- not exact, just enough
    to sanity-check against Groq's actual usage numbers in the logs."""
    return len(text) // 4


def _log_request_result(prompt: str, raw: str, completion) -> None:
    """Detailed per-request logging: prompt length, raw response
    length, finish reason, and token usage, when available."""
    prompt_chars = len(prompt)
    response_chars = len(raw) if raw is not None else 0

    finish_reason = None
    try:
        finish_reason = completion.choices[0].finish_reason
    except Exception:
        pass

    usage_prompt = usage_completion = usage_total = None
    usage = getattr(completion, "usage", None)
    if usage is not None:
        usage_prompt = getattr(usage, "prompt_tokens", None)
        usage_completion = getattr(usage, "completion_tokens", None)
        usage_total = getattr(usage, "total_tokens", None)

    print(
        "  REQUEST LOG: "
        f"prompt_chars={prompt_chars} (~{_estimate_tokens(prompt)} tokens est.), "
        f"response_chars={response_chars}, "
        f"finish_reason={finish_reason}, "
        f"usage(prompt/completion/total)="
        f"{usage_prompt}/{usage_completion}/{usage_total}"
    )


def _retry_after_seconds(exc: APIStatusError, default: int = 60) -> int:
    """Best-effort extraction of a Retry-After style header from a Groq
    APIStatusError's underlying HTTP response. Falls back to a fixed
    default if the header isn't present or isn't parseable."""
    try:
        response = getattr(exc, "response", None)
        if response is not None:
            header_value = response.headers.get("retry-after")
            if header_value is not None:
                return int(float(header_value))
    except Exception:
        pass
    return default


def call_groq(prompt: str):
    """
    Calls Groq once and returns the raw text content.

    Distinguishes error classes instead of catching everything the
    same way (Root Cause 2):
      - RateLimitError (429): NOT retried in a tight loop here. We wait
        out the API's own indicated reset window once, then re-raise
        (as QuotaExhaustedError) so the caller can decide to stop the
        whole run rather than burn further attempts against an
        already-exhausted quota.
      - AuthenticationError (401): fatal immediately, no retry --
        retrying with the same bad credentials can't ever succeed.
      - APIConnectionError / APITimeoutError: genuine transient
        network issues -- these are the ones worth a short retry loop.
      - Any other APIStatusError (400/500/etc.): logged with status
        code and body, retried with backoff, same as network errors,
        since a transient server-side issue is still possible.
    """
    last_error = None

    for attempt in range(3):
        print(f"  API attempt {attempt + 1}")
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=3500,
            )

            raw = completion.choices[0].message.content
            raw = raw.strip() if raw else ""

            _log_request_result(prompt, raw, completion)

            return raw

        except RateLimitError as e:
            wait_seconds = _retry_after_seconds(e, default=60)
            print(
                f"  RATE LIMIT (429) on attempt {attempt + 1}: {e}. "
                f"Waiting {wait_seconds}s (from Retry-After header if present) "
                f"before giving up on this request -- quota is likely exhausted, "
                f"not retrying blindly."
            )
            time.sleep(wait_seconds)
            # Re-raise as QuotaExhaustedError so the sign loop (and
            # main script) can decide to stop the whole run instead of
            # continuing to hammer an exhausted quota sign by sign.
            raise QuotaExhaustedError(
                f"Groq rate limit (429) hit and not recovered after waiting "
                f"{wait_seconds}s: {e}"
            ) from e

        except AuthenticationError as e:
            print(f"  AUTHENTICATION FAILED: {e}. Not retrying -- fix GROQ_API_KEY_GEN1.")
            raise

        except (APIConnectionError, APITimeoutError) as e:
            print(f"  NETWORK/TIMEOUT ERROR on attempt {attempt + 1}: {e}")
            last_error = e
            if attempt < 2:
                time.sleep(5)
            continue

        except APIStatusError as e:
            body_preview = getattr(e, "body", None)
            print(
                f"  API ERROR on attempt {attempt + 1}: status={e.status_code} "
                f"message={e} body={body_preview}"
            )
            last_error = e
            if attempt < 2:
                time.sleep(5)
            continue

    raise last_error


def parse_json_array(raw: str):
    """
    Parses Groq's raw text response into a JSON array.

    Fix for Root Cause 1: validates the response BEFORE calling
    json.loads(). An empty or whitespace-only response used to reach
    json.loads() directly and surface as:
        Expecting value: line 1 column 1 (char 0)
    which is Python reporting "there was nothing here to parse," not
    a JSON formatting problem. That distinction matters: the old code
    treated it as a generic parse failure with no visibility into
    what Groq actually returned. Now, the full raw response is logged
    before we do anything else with it, and an empty/invalid response
    raises a clearly-named EmptyOrInvalidResponseError instead of
    letting json.JSONDecodeError's confusing message be the only signal.
    """
    print(f"  RAW RESPONSE (full, {len(raw) if raw else 0} chars):")
    print(f"  {raw!r}")

    if raw is None or not raw.strip():
        raise EmptyOrInvalidResponseError(
            "Groq returned an empty or whitespace-only response -- "
            "see the full raw response logged above (there is none)."
        )

    cleaned = raw.strip()

    # Defensively strip markdown fences even though the prompt asks
    # Groq not to use them -- models don't always comply.
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    if not cleaned:
        raise EmptyOrInvalidResponseError(
            "Response was non-empty before markdown-fence stripping, but "
            "became empty after stripping ``` fences -- see the full raw "
            "response logged above."
        )

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Preserve the original JSONDecodeError as the cause rather
        # than swallowing it -- `from e` keeps the traceback chain so
        # the real parse position/context isn't lost.
        raise EmptyOrInvalidResponseError(
            f"Failed to parse Groq's response as JSON ({e}). "
            f"See the full raw response logged above for what was "
            f"actually returned."
        ) from e


for sign in SIGNS:
    print(f"\n========== {sign} ==========\n")

    rows_resp = (
        supabase.table("horoscopes")
        .select("mood,content")
        .eq("horoscope_date", target_date)
        .eq("sign", sign)
        .execute()
    )
    rows = rows_resp.data or []

    if not rows:
        print(f"No rows found for {sign} on {target_date}, skipping.")
        continue

    if {r["mood"] for r in rows} != EXPECTED_MOODS:
        print(f"WARNING: {sign} does not have all 15 pending moods "
              f"({len(rows)} found) — proceeding with what's available.")

    prompt = build_prompt(sign, rows)
    expected_moods_for_batch = {r["mood"] for r in rows}

    success = False
    quota_exhausted = False

    for attempt in range(3):
        try:
            print("Generating interpretations...")
            raw = call_groq(prompt)
            parsed = parse_json_array(raw)

            if not isinstance(parsed, list):
                raise ValueError("Top-level JSON is not an array")

            problems = validate_batch(parsed, expected_moods_for_batch)
            if problems:
                print(f"VALIDATION FAILED for {sign} (attempt {attempt + 1}):")
                for p in problems:
                    print(f"  - {p}")
                if attempt == 2:
                    failed_signs.append(sign)
                    break
                time.sleep(5)
                continue

            print("Updating rows...")
            count = 0
            for entry in parsed:
                supabase.table("horoscopes").update({
                    "mood_connection": entry["mood_connection"],
                    "today_influence": entry["today_influence"],
                    "daily_action": entry["daily_action"],
                    "personal_note": entry["personal_note"],
                    "gen3_status": "done",
                    "gen3_generated_at": datetime.utcnow().isoformat(),
                }).eq("horoscope_date", target_date).eq("sign", sign).eq(
                    "mood", entry["mood"]
                ).execute()
                count += 1

            succeeded_signs.append(sign)
            total_updated += count
            print(f"SUCCESS: updated {count} rows for {sign}")
            success = True
            break

        except QuotaExhaustedError as e:
            # Root Cause 2 fix: a 429 is not treated like any other
            # exception. We do not retry further sign requests in this
            # run -- if the quota is exhausted, every remaining sign
            # will fail the same way, so we stop the whole script
            # instead of burning more failed attempts and more log
            # noise. Signs not yet processed are left exactly as they
            # are (still 'pending'), so the next scheduled/manual run
            # will pick them up normally.
            print(f"QUOTA EXHAUSTED while processing {sign}: {e}")
            print(
                "Stopping the entire run -- remaining signs are left "
                "'pending' and will be picked up on the next run."
            )
            quota_exhausted = True
            break

        except AuthenticationError as e:
            # Fatal, identical reasoning to QuotaExhaustedError: retrying
            # with the same broken credentials cannot succeed, and every
            # remaining sign will fail the same way.
            print(f"AUTHENTICATION FAILED while processing {sign}: {e}")
            print("Stopping the entire run -- fix GROQ_API_KEY_GEN1 and re-run.")
            quota_exhausted = True  # reuse the same "stop everything" path
            break

        except EmptyOrInvalidResponseError as e:
            print(f"EMPTY/INVALID RESPONSE (attempt {attempt + 1}) for {sign}: {e}")
            if attempt == 2:
                failed_signs.append(sign)
            time.sleep(5)

        except Exception as e:
            print(f"FAILED (attempt {attempt + 1}) for {sign}: {e}")
            if attempt == 2:
                failed_signs.append(sign)
            time.sleep(5)

    if quota_exhausted:
        break

    if not success and sign not in failed_signs:
        failed_signs.append(sign)

    print("Waiting before next sign...\n")
    time.sleep(8)

print("\n========================")
print("GENERATOR 3 COMPLETE")
print("========================")
print(f"TOTAL ROWS UPDATED: {total_updated}")
print(f"SUCCESSFUL SIGNS: {len(succeeded_signs)}")

if failed_signs:
    print("\nFAILED SIGNS (marked gen3_status='failed'):")
    print(sorted(set(failed_signs)))
    for sign in set(failed_signs):
        supabase.table("horoscopes").update({
            "gen3_status": "failed"
        }).eq("horoscope_date", target_date).eq("sign", sign).execute()
else:
    print("\nALL SIGNS PROCESSED SUCCESSFULLY")
