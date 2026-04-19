-- Add provider opt-in consent fields
-- Migration: 004_provider_optin_fields.sql
-- Description: Add fields for provider opt-in consent and automation settings

ALTER TABLE service_providers 
ADD COLUMN IF NOT EXISTS auto_outreach_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS outreach_consent_status VARCHAR(50) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS outreach_consent_date TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS opt_in_email_sent_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS provider_response_received_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS provider_response_text TEXT,
ADD COLUMN IF NOT EXISTS sentiment_analysis_result JSONB,
ADD COLUMN IF NOT EXISTS automation_settings JSONB DEFAULT '{}';

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_service_providers_outreach_consent_status 
ON service_providers(outreach_consent_status);

CREATE INDEX IF NOT EXISTS idx_service_providers_auto_outreach_enabled 
ON service_providers(auto_outreach_enabled);

-- Add comment
COMMENT ON COLUMN service_providers.auto_outreach_enabled IS 'Whether provider has opted in to automated outreach';
COMMENT ON COLUMN service_providers.outreach_consent_status IS 'Consent status: pending, consented, declined';
COMMENT ON COLUMN service_providers.outreach_consent_date IS 'Date when provider gave consent';
COMMENT ON COLUMN service_providers.opt_in_email_sent_at IS 'Timestamp when opt-in email was sent';
COMMENT ON COLUMN service_providers.provider_response_received_at IS 'Timestamp when provider response was received';
COMMENT ON COLUMN service_providers.provider_response_text IS 'Actual text of provider response';
COMMENT ON COLUMN service_providers.sentiment_analysis_result IS 'Sentiment analysis result of provider response';
COMMENT ON COLUMN service_providers.automation_settings IS 'Automation settings for provider outreach';
