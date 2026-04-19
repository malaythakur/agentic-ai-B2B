-- Initial schema for AI SaaS Outbound System

-- Leads table: source of truth for lead intelligence
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    lead_id VARCHAR(255) UNIQUE NOT NULL,
    company VARCHAR(500) NOT NULL,
    website VARCHAR(500),
    signal TEXT,
    decision_maker VARCHAR(255),
    fit_score INTEGER DEFAULT 0,
    message_intent TEXT,
    status VARCHAR(50) DEFAULT 'new',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Campaign runs table: track each batch generation
CREATE TABLE IF NOT EXISTS campaign_runs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    total_leads INTEGER DEFAULT 0,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Outbound messages table: send-ready payloads
CREATE TABLE IF NOT EXISTS outbound_messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    run_id VARCHAR(255) REFERENCES campaign_runs(run_id),
    lead_id VARCHAR(255) REFERENCES leads(lead_id),
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    to_email VARCHAR(500) NOT NULL,
    from_email VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'queued',
    gmail_message_id VARCHAR(255),
    gmail_thread_id VARCHAR(255),
    sent_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Replies table: track incoming replies
CREATE TABLE IF NOT EXISTS replies (
    id SERIAL PRIMARY KEY,
    reply_id VARCHAR(255) UNIQUE NOT NULL,
    message_id VARCHAR(255) REFERENCES outbound_messages(message_id),
    lead_id VARCHAR(255) REFERENCES leads(lead_id),
    gmail_message_id VARCHAR(255) NOT NULL,
    gmail_thread_id VARCHAR(255) NOT NULL,
    from_email VARCHAR(500) NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    classification VARCHAR(50),
    processed_at TIMESTAMP WITH TIME ZONE,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Followups table: scheduled follow-up messages
CREATE TABLE IF NOT EXISTS followups (
    id SERIAL PRIMARY KEY,
    followup_id VARCHAR(255) UNIQUE NOT NULL,
    message_id VARCHAR(255) REFERENCES outbound_messages(message_id),
    lead_id VARCHAR(255) REFERENCES leads(lead_id),
    sequence_number INTEGER NOT NULL,
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'scheduled',
    subject TEXT,
    body TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Suppression list table: emails to never contact
CREATE TABLE IF NOT EXISTS suppression_list (
    id SERIAL PRIMARY KEY,
    email VARCHAR(500) UNIQUE NOT NULL,
    reason VARCHAR(255),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    lead_id VARCHAR(255)
);

-- Events table: audit log for all meaningful state changes
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_leads_lead_id ON leads(lead_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_fit_score ON leads(fit_score);

CREATE INDEX IF NOT EXISTS idx_campaign_runs_run_id ON campaign_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_campaign_runs_status ON campaign_runs(status);

CREATE INDEX IF NOT EXISTS idx_outbound_messages_message_id ON outbound_messages(message_id);
CREATE INDEX IF NOT EXISTS idx_outbound_messages_run_id ON outbound_messages(run_id);
CREATE INDEX IF NOT EXISTS idx_outbound_messages_lead_id ON outbound_messages(lead_id);
CREATE INDEX IF NOT EXISTS idx_outbound_messages_status ON outbound_messages(status);
CREATE INDEX IF NOT EXISTS idx_outbound_messages_gmail_message_id ON outbound_messages(gmail_message_id);
CREATE INDEX IF NOT EXISTS idx_outbound_messages_gmail_thread_id ON outbound_messages(gmail_thread_id);

CREATE INDEX IF NOT EXISTS idx_replies_message_id ON replies(message_id);
CREATE INDEX IF NOT EXISTS idx_replies_lead_id ON replies(lead_id);
CREATE INDEX IF NOT EXISTS idx_replies_gmail_thread_id ON replies(gmail_thread_id);
CREATE INDEX IF NOT EXISTS idx_replies_classification ON replies(classification);

CREATE INDEX IF NOT EXISTS idx_followups_message_id ON followups(message_id);
CREATE INDEX IF NOT EXISTS idx_followups_lead_id ON followups(lead_id);
CREATE INDEX IF NOT EXISTS idx_followups_scheduled_for ON followups(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_followups_status ON followups(status);

CREATE INDEX IF NOT EXISTS idx_suppression_list_email ON suppression_list(email);

CREATE INDEX IF NOT EXISTS idx_events_entity_type ON events(entity_type);
CREATE INDEX IF NOT EXISTS idx_events_entity_id ON events(entity_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_outbound_messages_updated_at BEFORE UPDATE ON outbound_messages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_followups_updated_at BEFORE UPDATE ON followups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
