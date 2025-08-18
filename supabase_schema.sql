-- Argentis FSRI-Lite Pro Database Schema
-- Run this SQL in your Supabase SQL Editor

-- Table for daily FSRI scores
CREATE TABLE IF NOT EXISTS scores_daily (
    id BIGSERIAL PRIMARY KEY,
    dt DATE NOT NULL,
    crop VARCHAR(50) NOT NULL,
    region VARCHAR(10) NOT NULL,
    production DECIMAL(5,2) NOT NULL,
    movement DECIMAL(5,2) NOT NULL,
    policy DECIMAL(5,2) NOT NULL,
    biosecurity DECIMAL(5,2) NOT NULL,
    fsri DECIMAL(5,2) NOT NULL,
    drivers JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint for idempotent upserts
    UNIQUE(dt, crop, region)
);

-- Table for decision logging
CREATE TABLE IF NOT EXISTS decisions_log (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMP WITH TIME ZONE NOT NULL,
    crop VARCHAR(50) NOT NULL,
    region VARCHAR(10) NOT NULL,
    fsri DECIMAL(5,2) NOT NULL,
    drivers JSONB,
    action TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_scores_daily_dt_crop ON scores_daily(dt, crop);
CREATE INDEX IF NOT EXISTS idx_scores_daily_region ON scores_daily(region);
CREATE INDEX IF NOT EXISTS idx_decisions_log_ts ON decisions_log(ts);
CREATE INDEX IF NOT EXISTS idx_decisions_log_crop_region ON decisions_log(crop, region);

-- Enable Row Level Security (RLS)
ALTER TABLE scores_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions_log ENABLE ROW LEVEL SECURITY;

-- Create policies for API access (adjust based on your auth setup)
CREATE POLICY "Allow read access to scores_daily" ON scores_daily
    FOR SELECT USING (true);

CREATE POLICY "Allow insert/update to scores_daily" ON scores_daily
    FOR ALL USING (true);

CREATE POLICY "Allow insert to decisions_log" ON decisions_log
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow read access to decisions_log" ON decisions_log
    FOR SELECT USING (true);
