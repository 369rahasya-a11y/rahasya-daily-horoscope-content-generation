```python
import os
import time

from supabase import create_client

# =========================
# ENV VARIABLES
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# =========================
# VALIDATION
# =========================

if not SUPABASE_URL:
    raise Exception("SUPABASE_URL missing")

if not SUPABASE_KEY:
    raise Exception("SUPABASE_SERVICE_ROLE_KEY missing")

# =========================
# CONNECT SUPABASE
# =========================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

print("CONNECTED")

# =========================
# TEST DATA
# =========================

SIGNS = [
    "Aries"
]

# =========================
# TEST INSERT
# =========================

for sign in SIGNS:

    print(f"\n========== {sign} ==========\n")

    try:

        print("Testing Supabase insert...")

        parsed = {
            "date": "2026-05-28",
            "sign": sign,
            "horoscopes": [
                {
                    "mood": "Ambitious",
                    "content": "This is a Supabase test horoscope."
                }
            ]
        }

        for item in parsed["horoscopes"]:

            supabase.table("horoscopes").insert(
                {
                    "horoscope_date": parsed["date"],
                    "sign": parsed["sign"],
                    "mood": item["mood"],
                    "content": item["content"]
                }
            ).execute()

        print("SUCCESS")

    except Exception as e:

        print("FAILED:")
        print(str(e))

    time.sleep(2)

print("\nSUPABASE TEST COMPLETE")
```
