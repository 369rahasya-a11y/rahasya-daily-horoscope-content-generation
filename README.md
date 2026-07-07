# Rahasya — Horoscope + Mood Content, One Repository, One Run

Everything happens in a single GitHub Actions job, one step after
another, in one continuous run:

1. **Horoscope Generator** (`generate.py`) — writes tomorrow's
   Horoscope for all 12 signs × 15 moods (180 rows) into Supabase.
   Completely unchanged from your original generator — same
   `prompt.txt`, same writing logic, same Groq call, reading its API
   key from `GROQ_API_KEY` in the environment exactly as before.
2. **Mood Content Generator** (`generator3/generate_interpretations.py`)
   — runs immediately after, in the same job, as the next step. It
   reads the Horoscope rows the first step just wrote and adds four
   sections written through the lens of the reader's selected mood:
   Mood Connection, Today's Influence, Daily Action, and a Personal
   Note. It also reads its Groq key from `GROQ_API_KEY` in the
   environment, independently of the first step — same pattern,
   unchanged.

## Why one job instead of two

GitHub Actions runs the steps inside a job strictly in order — each
step only starts once the previous one has completely finished. That
alone guarantees the Mood Content Generator never starts until the
Horoscope Generator has exited and its Supabase writes are committed
(every write Generator 1 makes is a synchronous call — the data is
already there the moment the process ends). One job, two steps, no
artificial waiting is needed to get that guarantee.

## Repository layout

```
.
├── generate.py                          # Horoscope Generator (unchanged original)
├── prompt.txt                           # Horoscope Generator's writing rules
├── constants.py                         # SIGNS, MOODS
├── generator3/
│   ├── generate_interpretations.py      # Mood Content Generator entry point
│   ├── prompt_builder.py                # appends sign + horoscopes to base.txt
│   ├── validators.py                    # structural + forbidden-phrase checks
│   └── prompts/
│       └── base.txt                     # entire philosophy + all 4 section briefs, one file
├── migration_add_gen3_columns.sql       # run once, before first use
├── requirements.txt
├── .env.example
├── .gitignore
└── .github/workflows/daily.yml          # cron + manual trigger, one job, two steps
```

## How the two generators connect

`migration_add_gen3_columns.sql` adds a `gen3_status` column defaulting
to `'pending'`. The Horoscope Generator's upsert also explicitly resets
`gen3_status` back to `'pending'` on every write — this is the only
line that differs from your original `generate.py` (one line becomes
two). So if it's ever re-run for a date it already processed, the Mood
Content Generator will reprocess that row on the next run instead of
leaving stale sections paired with a new Horoscope.

The Mood Content Generator queries for `gen3_status = 'pending'` rows
for the date the Horoscope Generator just wrote, processes 15 moods
per request (one request per sign), and marks each row `'done'` or
`'failed'`.

## Setup

### 1. Run the database migration

Run `migration_add_gen3_columns.sql` against your Supabase project
before the first run. Assumes a `horoscopes` table already exists
with `horoscope_date`, `sign`, `mood`, `content` columns.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

```
GROQ_API_KEY=your_groq_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
```

### 4. Run locally (optional)

```bash
python generate.py
python generator3/generate_interpretations.py
```

## GitHub Secrets (required)

| Secret name | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key — used by both generators, each reading it independently from its own environment |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |

## Automated daily run

`.github/workflows/daily.yml` runs on cron (`0 18 * * *` UTC) and
supports manual triggering via **Actions → Run workflow**. One job,
four steps: checkout, install dependencies, run the Horoscope
Generator, then run the Mood Content Generator — all in that order, in
one continuous run.

## After cloning, the only required setup is:

1. Run the migration against Supabase once.
2. Add the three GitHub Secrets above.
3. Push to GitHub.

From that point on, the pipeline runs automatically every day with no
further manual intervention.
