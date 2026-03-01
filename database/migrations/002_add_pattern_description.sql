-- Migration: Add description column to patterns table
-- This adds human-readable descriptions to patterns for better UX

-- Add description column to patterns table
ALTER TABLE patterns ADD COLUMN IF NOT EXISTS description TEXT;

-- Update existing patterns with generated descriptions based on pattern_subtype
-- This is optional but helps with existing data
UPDATE patterns
SET description =
    CASE
        -- Offensive patterns (missed opportunities)
        WHEN pattern_subtype LIKE 'missed_%' THEN
            'You missed ' || frequency || ' ' ||
            REPLACE(REPLACE(pattern_subtype, 'missed_', ''), '_', ' ') ||
            CASE WHEN frequency = 1 THEN ' opportunity' ELSE ' opportunities' END

        -- Defensive patterns (fell for tactics)
        WHEN pattern_subtype LIKE 'fell_for_%' THEN
            'You fell for ' ||
            REPLACE(REPLACE(pattern_subtype, 'fell_for_', ''), '_', ' ') ||
            ' attacks ' || frequency ||
            CASE WHEN frequency = 1 THEN ' time' ELSE ' times' END

        -- Generic fallback
        ELSE
            REPLACE(pattern_subtype, '_', ' ') || ' (' || frequency ||
            CASE WHEN frequency = 1 THEN ' time)' ELSE ' times)' END
    END
WHERE description IS NULL;
