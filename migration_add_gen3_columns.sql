-- Generator 3 columns. Additive only -- never touches Generator 1's
-- `content` column, and never touches Generator 2's columns
-- (hidden_pattern, alt_perspective, notice_cue, reflection_question,
-- gen2_status, gen2_generated_at). Generator 3 runs independently and
-- in parallel with Generator 2, against the same horoscope, with its
-- own status column so the two never interfere with each other.

alter table horoscopes
  add column if not exists mood_connection text,
  add column if not exists today_influence text,
  add column if not exists daily_action text,
  add column if not exists personal_note text,
  add column if not exists gen3_status text default 'pending',
  add column if not exists gen3_generated_at timestamptz;

-- Same note as the Generator 2 migration: existing rows will get
-- gen3_status = 'pending' by default too, but Generator 3 only ever
-- queries by horoscope_date = target_date (tomorrow, relative to when
-- it runs), so old historical rows are never picked up in practice.
