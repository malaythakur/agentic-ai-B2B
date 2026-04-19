-- Migration 003: Add templates table for AI-personalized message generation
-- This migration adds the template system for production-grade message templating

-- Create templates table
CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    template_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Template metadata
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Template content
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    
    -- Signal matching keywords (JSON array)
    signal_keywords JSONB DEFAULT '[]',
    
    -- Performance tracking
    usage_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    positive_reply_count INTEGER DEFAULT 0,
    reply_rate INTEGER DEFAULT 0,  -- Stored as percentage
    performance_score INTEGER DEFAULT 50,  -- 0-100 score
    
    -- A/B testing
    variant_of VARCHAR(255) REFERENCES templates(template_id),
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    
    -- Versioning
    version INTEGER DEFAULT 1,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_templates_category ON templates(category);
CREATE INDEX idx_templates_is_active ON templates(is_active);
CREATE INDEX idx_templates_is_default ON templates(is_default);
CREATE INDEX idx_templates_performance ON templates(performance_score DESC);
CREATE INDEX idx_templates_signal_keywords ON templates USING GIN(signal_keywords);

-- Add template tracking columns to outbound_messages
ALTER TABLE outbound_messages 
    ADD COLUMN IF NOT EXISTS template_id VARCHAR(255) REFERENCES templates(template_id),
    ADD COLUMN IF NOT EXISTS personalization_method VARCHAR(50) DEFAULT 'ai_generated';

-- Create index for template tracking
CREATE INDEX IF NOT EXISTS idx_outbound_messages_template_id ON outbound_messages(template_id);

-- Add comment explaining personalization_method values
COMMENT ON COLUMN outbound_messages.personalization_method IS 
    'Values: template_ai (template with AI personalization), custom (user-provided message), ai_generated (pure AI generation)';

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop existing trigger if exists to avoid errors
DROP TRIGGER IF EXISTS update_templates_updated_at ON templates;

-- Create trigger
CREATE TRIGGER update_templates_updated_at
    BEFORE UPDATE ON templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default templates (optional - can also be done via API)
-- These will be seeded via the API endpoint POST /api/templates/seed-defaults

-- Log migration completion
INSERT INTO events (event_id, event_type, entity_type, entity_id, data, created_at)
VALUES (
    'migration-003-' || extract(epoch from now())::bigint,
    'migration_applied',
    'migration',
    '003_templates',
    '{"description": "Added templates table for AI-personalized message generation", "tables": ["templates"], "indexes": 5}'::jsonb,
    CURRENT_TIMESTAMP
);
