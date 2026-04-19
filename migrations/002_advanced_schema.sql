-- Advanced schema for autonomous GTM agent
-- Adds tables for lead qualification, offer matching, conversation memory, 
-- deliverability, feedback learning, experiments, pipeline state machine, and CRM

-- Lead scores table - multi-dimensional scoring
CREATE TABLE IF NOT EXISTS lead_scores (
    id SERIAL PRIMARY KEY,
    lead_id VARCHAR(255) UNIQUE NOT NULL REFERENCES leads(lead_id),
    
    -- Signal dimensions
    signal_strength INTEGER DEFAULT 0,
    hiring_intensity INTEGER DEFAULT 0,
    funding_stage INTEGER DEFAULT 0,
    company_size_fit INTEGER DEFAULT 0,
    market_relevance INTEGER DEFAULT 0,
    
    -- Computed scores
    priority_score INTEGER DEFAULT 0,
    qualification_score INTEGER DEFAULT 0,
    
    -- Qualification decision
    is_qualified BOOLEAN DEFAULT FALSE,
    qualified_at TIMESTAMP WITH TIME ZONE,
    disqualification_reason TEXT,
    
    -- Metadata
    score_version VARCHAR(50) DEFAULT 'v1',
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Offer strategies table - signal to offer mapping
CREATE TABLE IF NOT EXISTS offer_strategies (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    
    -- Signal matching
    signal_type VARCHAR(100) NOT NULL,
    signal_keywords TEXT[],
    
    -- Offer definition
    offer_angle TEXT NOT NULL,
    message_style VARCHAR(100) NOT NULL,
    cta_type VARCHAR(100) NOT NULL,
    
    -- Performance tracking
    total_sent INTEGER DEFAULT 0,
    total_replies INTEGER DEFAULT 0,
    reply_rate DECIMAL(5,2) DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Conversation memory table - thread context
CREATE TABLE IF NOT EXISTS conversation_memory (
    id SERIAL PRIMARY KEY,
    memory_id VARCHAR(255) UNIQUE NOT NULL,
    lead_id VARCHAR(255) REFERENCES leads(lead_id),
    thread_id VARCHAR(255),
    
    -- Conversation state
    tone VARCHAR(100),
    relationship_stage VARCHAR(100),
    objection_raised TEXT,
    last_topic TEXT,
    
    -- Email history
    emails_sent INTEGER DEFAULT 0,
    replies_received INTEGER DEFAULT 0,
    
    -- Context
    context_summary TEXT,
    key_points TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Deliverability rules table
CREATE TABLE IF NOT EXISTS deliverability_rules (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(255) UNIQUE NOT NULL,
    domain VARCHAR(255) NOT NULL,
    
    -- Domain health
    domain_warmed BOOLEAN DEFAULT FALSE,
    warmup_start_date TIMESTAMP WITH TIME ZONE,
    warmup_end_date TIMESTAMP WITH TIME ZONE,
    
    -- Send limits
    max_sends_per_hour INTEGER DEFAULT 30,
    max_sends_per_day INTEGER DEFAULT 200,
    current_hourly_count INTEGER DEFAULT 0,
    current_daily_count INTEGER DEFAULT 0,
    
    -- Inbox rotation
    primary_inbox VARCHAR(255),
    backup_inboxes TEXT[],
    
    -- Health metrics
    bounce_rate DECIMAL(5,2) DEFAULT 0,
    spam_rate DECIMAL(5,2) DEFAULT 0,
    health_score INTEGER DEFAULT 100,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Experiments table - A/B testing
CREATE TABLE IF NOT EXISTS experiments (
    id SERIAL PRIMARY KEY,
    experiment_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    experiment_type VARCHAR(100) NOT NULL, -- subject, message, cta
    
    -- Variants
    variants JSONB NOT NULL,
    
    -- Targeting
    target_segment VARCHAR(100),
    sample_size INTEGER,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active', -- active, paused, completed
    
    -- Results
    total_participants INTEGER DEFAULT 0,
    statistical_significance BOOLEAN DEFAULT FALSE,
    winner VARCHAR(255),
    
    -- Timeline
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Experiment results table
CREATE TABLE IF NOT EXISTS experiment_results (
    id SERIAL PRIMARY KEY,
    result_id VARCHAR(255) UNIQUE NOT NULL,
    experiment_id VARCHAR(255) REFERENCES experiments(experiment_id),
    message_id VARCHAR(255) REFERENCES outbound_messages(message_id),
    
    variant VARCHAR(255) NOT NULL,
    
    -- Outcomes
    replied BOOLEAN DEFAULT FALSE,
    replied_at TIMESTAMP WITH TIME ZONE,
    converted BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Pipeline state machine table
CREATE TABLE IF NOT EXISTS pipeline_states (
    id SERIAL PRIMARY KEY,
    state_id VARCHAR(255) UNIQUE NOT NULL,
    lead_id VARCHAR(255) UNIQUE NOT NULL REFERENCES leads(lead_id),
    
    -- Current state
    current_state VARCHAR(50) DEFAULT 'NEW',
    previous_state VARCHAR(50),
    
    -- State transitions
    entered_current_state_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    state_history JSONB DEFAULT '[]'::jsonb,
    
    -- Pipeline metrics
    time_in_state_seconds INTEGER DEFAULT 0,
    total_pipeline_days INTEGER DEFAULT 0,
    
    -- Stage-specific data
    stage_data JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Deals table (CRM layer)
CREATE TABLE IF NOT EXISTS deals (
    id SERIAL PRIMARY KEY,
    deal_id VARCHAR(255) UNIQUE NOT NULL,
    lead_id VARCHAR(255) REFERENCES leads(lead_id),
    
    -- Deal details
    deal_name VARCHAR(500),
    deal_value DECIMAL(12,2),
    deal_stage VARCHAR(50) DEFAULT 'prospecting',
    
    -- Probability
    win_probability INTEGER DEFAULT 0,
    
    -- Timeline
    expected_close_date DATE,
    actual_close_date DATE,
    
    -- Owner
    owner_id VARCHAR(255),
    owner_type VARCHAR(50) DEFAULT 'system', -- system, human
    
    -- Source tracking
    source_campaign VARCHAR(255),
    source_message_id VARCHAR(255),
    
    -- Status
    status VARCHAR(50) DEFAULT 'open', -- open, won, lost
    lost_reason TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Human escalation queue table
CREATE TABLE IF NOT EXISTS human_escalation_queue (
    id SERIAL PRIMARY KEY,
    escalation_id VARCHAR(255) UNIQUE NOT NULL,
    lead_id VARCHAR(255) REFERENCES leads(lead_id),
    message_id VARCHAR(255) REFERENCES outbound_messages(message_id),
    reply_id VARCHAR(255) REFERENCES replies(reply_id),
    
    -- Escalation reason
    escalation_reason VARCHAR(100) NOT NULL, -- pricing, negotiation, angry, high_value
    priority VARCHAR(50) DEFAULT 'normal', -- low, normal, high, urgent
    
    -- Context
    context_summary TEXT,
    
    -- Assignment
    assigned_to VARCHAR(255),
    assigned_at TIMESTAMP WITH TIME ZONE,
    
    -- Resolution
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, resolved, dismissed
    resolution_notes TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance metrics table (for feedback learning)
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    metric_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Metric dimensions
    dimension_type VARCHAR(100) NOT NULL, -- subject, company_type, angle, signal
    dimension_value VARCHAR(255) NOT NULL,
    
    -- Metrics
    total_sent INTEGER DEFAULT 0,
    total_replies INTEGER DEFAULT 0,
    total_converted INTEGER DEFAULT 0,
    
    -- Rates
    reply_rate DECIMAL(5,2) DEFAULT 0,
    conversion_rate DECIMAL(5,2) DEFAULT 0,
    
    -- Statistical significance
    sample_size INTEGER DEFAULT 0,
    confidence_level DECIMAL(5,2),
    
    -- Trend
    trend_direction VARCHAR(20), -- improving, declining, stable
    
    -- Metadata
    period_start DATE,
    period_end DATE,
    
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_lead_scores_lead_id ON lead_scores(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_scores_priority_score ON lead_scores(priority_score);
CREATE INDEX IF NOT EXISTS idx_lead_scores_is_qualified ON lead_scores(is_qualified);

CREATE INDEX IF NOT EXISTS idx_offer_strategies_signal_type ON offer_strategies(signal_type);
CREATE INDEX IF NOT EXISTS idx_offer_strategies_reply_rate ON offer_strategies(reply_rate);

CREATE INDEX IF NOT EXISTS idx_conversation_memory_lead_id ON conversation_memory(lead_id);
CREATE INDEX IF NOT EXISTS idx_conversation_memory_thread_id ON conversation_memory(thread_id);

CREATE INDEX IF NOT EXISTS idx_deliverability_rules_domain ON deliverability_rules(domain);
CREATE INDEX IF NOT EXISTS idx_deliverability_rules_health_score ON deliverability_rules(health_score);

CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiments_experiment_type ON experiments(experiment_type);

CREATE INDEX IF NOT EXISTS idx_experiment_results_experiment_id ON experiment_results(experiment_id);
CREATE INDEX IF NOT EXISTS idx_experiment_results_variant ON experiment_results(variant);

CREATE INDEX IF NOT EXISTS idx_pipeline_states_lead_id ON pipeline_states(lead_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_states_current_state ON pipeline_states(current_state);

CREATE INDEX IF NOT EXISTS idx_deals_lead_id ON deals(lead_id);
CREATE INDEX IF NOT EXISTS idx_deals_deal_stage ON deals(deal_stage);
CREATE INDEX IF NOT EXISTS idx_deals_owner_type ON deals(owner_type);

CREATE INDEX IF NOT EXISTS idx_human_escalation_queue_status ON human_escalation_queue(status);
CREATE INDEX IF NOT EXISTS idx_human_escalation_queue_priority ON human_escalation_queue(priority);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_dimension_type ON performance_metrics(dimension_type);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_dimension_value ON performance_metrics(dimension_value);

-- Triggers for updated_at
CREATE TRIGGER update_lead_scores_updated_at BEFORE UPDATE ON lead_scores
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_offer_strategies_updated_at BEFORE UPDATE ON offer_strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversation_memory_updated_at BEFORE UPDATE ON conversation_memory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_deliverability_rules_updated_at BEFORE UPDATE ON deliverability_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pipeline_states_updated_at BEFORE UPDATE ON pipeline_states
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_deals_updated_at BEFORE UPDATE ON deals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update leads table to add email field
ALTER TABLE leads ADD COLUMN IF NOT EXISTS email VARCHAR(500);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);

-- Update leads table to add more qualification fields
ALTER TABLE leads ADD COLUMN IF NOT EXISTS company_size VARCHAR(100);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS funding_stage VARCHAR(100);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS market_segment VARCHAR(100);
