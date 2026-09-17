-- schema.sql
-- Run this SQL once in your Supabase project dashboard:
-- https://supabase.com/dashboard → SQL Editor → New Query

CREATE TABLE IF NOT EXISTS runs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_idea    TEXT        NOT NULL,
    output_file  TEXT,
    status       VARCHAR(20) NOT NULL,   -- 'success' | 'failed'
    retries      INTEGER     DEFAULT 0,
    description  TEXT        DEFAULT '',
    code_length  INTEGER     DEFAULT 0,  -- chars in generated code
    game_code    TEXT,                   -- the full python code
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast history queries
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;

-- Allow all operations via anon key (adjust for your security needs)
CREATE POLICY "Allow all" ON runs FOR ALL USING (true);
