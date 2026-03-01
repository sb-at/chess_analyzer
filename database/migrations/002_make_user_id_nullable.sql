-- Migration: Make user_id nullable in jobs table for public analysis
-- This allows jobs to run without requiring a user account

ALTER TABLE jobs
ALTER COLUMN user_id DROP NOT NULL;

-- Add comment to clarify the purpose
COMMENT ON COLUMN jobs.user_id IS 'User ID - nullable for public analysis without authentication';
