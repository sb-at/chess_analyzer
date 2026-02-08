-- ChessMirror Database Schema
-- PostgreSQL initialization script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE,
    chess_com_username VARCHAR(255),
    lichess_username VARCHAR(255),
    chess_com_access_token TEXT,
    lichess_access_token TEXT,
    rating INT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_sync TIMESTAMP,
    CONSTRAINT at_least_one_username CHECK (
        chess_com_username IS NOT NULL OR lichess_username IS NOT NULL
    )
);

-- Patterns table
CREATE TABLE IF NOT EXISTS patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    pattern_type VARCHAR(50) NOT NULL, -- 'tactical', 'opening', 'strategic', 'time_management', 'psychological'
    pattern_subtype VARCHAR(100) NOT NULL, -- e.g., 'missed_fork', 'poor_opening_results'
    severity FLOAT CHECK (severity >= 0 AND severity <= 1), -- 0-1 score
    frequency INT DEFAULT 0,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    examples JSONB, -- array of {game_id, move_number, fen, etc.}
    metadata JSONB, -- additional pattern-specific data
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Pattern progress tracking
CREATE TABLE IF NOT EXISTS pattern_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    pattern_id UUID REFERENCES patterns(id) ON DELETE CASCADE,
    measured_at TIMESTAMP DEFAULT NOW(),
    occurrence_rate FLOAT, -- percentage of games with this pattern
    improvement_score FLOAT, -- calculated improvement metric
    notes TEXT
);

-- User sessions for authentication
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Background jobs tracking
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL, -- 'import', 'analysis', 'pattern_detection'
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    progress INT DEFAULT 0, -- 0-100
    total_items INT,
    processed_items INT DEFAULT 0,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_patterns_user_id ON patterns(user_id);
CREATE INDEX idx_patterns_type ON patterns(pattern_type);
CREATE INDEX idx_patterns_severity ON patterns(severity DESC);
CREATE INDEX idx_pattern_progress_user_id ON pattern_progress(user_id);
CREATE INDEX idx_pattern_progress_measured_at ON pattern_progress(measured_at DESC);
CREATE INDEX idx_user_sessions_token ON user_sessions(token);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add trigger to patterns table
CREATE TRIGGER update_patterns_updated_at
    BEFORE UPDATE ON patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
