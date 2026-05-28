print("STEP 1")

import json
print("STEP 2")

import os
print("STEP 3")

import time
print("STEP 4")

import requests
print("STEP 5")

from supabase import create_client
print("STEP 6")

# =========================
# ENV VARIABLES
# =========================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
print("STEP 7")

SUPABASE_URL = os.getenv("SUPABASE_URL")
print("STEP 8")

SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
print("STEP 9")

# =========================
# VALIDATION
# =========================

if not OPENROUTER_API_KEY:
    raise Exception("OPENROUTER_API_KEY missing")

if not SUPABASE_URL:
    raise Exception("SUPABASE_URL missing")

if not SUPABASE_KEY:
    raise Exception("SUPABASE_SERVICE_ROLE_KEY missing")

print("STEP 10")

# =========================
# CONNECT SUPABASE
# =========================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

print("STEP 11")

print("SUPABASE CONNECTED")
