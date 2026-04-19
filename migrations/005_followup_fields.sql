-- Migration 005: Add follow-up tracking fields to matches table

-- Add follow-up tracking fields
ALTER TABLE matches 
ADD COLUMN IF NOT EXISTS followup_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_followup_sent_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS response_received BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS response_received_at TIMESTAMP WITH TIME ZONE;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_matches_followup_count ON matches(followup_count);
CREATE INDEX IF NOT EXISTS idx_matches_last_followup ON matches(last_followup_sent_at);
CREATE INDEX IF NOT EXISTS idx_matches_response_received ON matches(response_received);

-- Add comments
COMMENT ON COLUMN matches.followup_count IS 'Number of follow-up emails sent for this match';
COMMENT ON COLUMN matches.last_followup_sent_at IS 'Timestamp of last follow-up email sent';
COMMENT ON COLUMN matches.response_received IS 'Whether the buyer has responded to outreach';
COMMENT ON COLUMN matches.response_received_at IS 'Timestamp when buyer response was received';
