-- B2B Matchmaking Platform Schema Migration
-- Creates tables for service providers, buyer companies, matches, and billing

-- ==========================================
-- SERVICE PROVIDERS
-- ==========================================
CREATE TABLE service_providers (
    id SERIAL PRIMARY KEY,
    provider_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Company info
    company_name VARCHAR(255) NOT NULL,
    website VARCHAR(500),
    description TEXT,
    
    -- Services offered
    services JSONB DEFAULT '[]',
    industries JSONB DEFAULT '[]',
    
    -- Ideal Customer Profile (ICP)
    icp_criteria JSONB DEFAULT '{}',
    
    -- Case studies & social proof
    case_studies JSONB DEFAULT '[]',
    differentiator TEXT,
    
    -- Contact & billing
    contact_email VARCHAR(500) NOT NULL,
    billing_email VARCHAR(500),
    
    -- Status
    active BOOLEAN DEFAULT TRUE,
    onboarding_complete BOOLEAN DEFAULT FALSE,
    
    -- Stripe/customer IDs
    stripe_customer_id VARCHAR(255),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_service_providers_provider_id ON service_providers(provider_id);
CREATE INDEX idx_service_providers_active ON service_providers(active);
CREATE INDEX idx_service_providers_industries ON service_providers USING GIN(industries);

-- ==========================================
-- PROVIDER SUBSCRIPTIONS
-- ==========================================
CREATE TABLE provider_subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(255) UNIQUE NOT NULL,
    provider_id VARCHAR(255) REFERENCES service_providers(provider_id),
    
    -- Plan details
    plan_type VARCHAR(50) NOT NULL,
    plan_name VARCHAR(255),
    
    -- Pricing (in cents)
    monthly_amount INTEGER DEFAULT 0,
    intro_fee_per_meeting INTEGER DEFAULT 0,
    
    -- Limits
    max_matches_per_month INTEGER DEFAULT 50,
    max_intros_per_month INTEGER DEFAULT 100,
    
    -- Usage tracking
    matches_used_this_month INTEGER DEFAULT 0,
    intros_sent_this_month INTEGER DEFAULT 0,
    meetings_booked_this_month INTEGER DEFAULT 0,
    
    -- Billing cycle
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_provider_subscriptions_subscription_id ON provider_subscriptions(subscription_id);
CREATE INDEX idx_provider_subscriptions_provider_id ON provider_subscriptions(provider_id);
CREATE INDEX idx_provider_subscriptions_status ON provider_subscriptions(status);

-- ==========================================
-- BUYER COMPANIES
-- ==========================================
CREATE TABLE buyer_companies (
    id SERIAL PRIMARY KEY,
    buyer_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Company info
    company_name VARCHAR(255) NOT NULL,
    website VARCHAR(500),
    industry VARCHAR(100),
    
    -- Company signals
    employee_count INTEGER,
    funding_stage VARCHAR(50),
    total_funding VARCHAR(100),
    
    -- What they need
    requirements JSONB DEFAULT '[]',
    budget_range VARCHAR(100),
    timeline VARCHAR(50) DEFAULT 'exploring',
    
    -- Signals indicating need
    signals JSONB DEFAULT '[]',
    
    -- Decision maker
    decision_maker_name VARCHAR(255),
    decision_maker_title VARCHAR(255),
    decision_maker_email VARCHAR(500),
    
    -- Status
    verified BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_buyer_companies_buyer_id ON buyer_companies(buyer_id);
CREATE INDEX idx_buyer_companies_active ON buyer_companies(active);
CREATE INDEX idx_buyer_companies_verified ON buyer_companies(verified);
CREATE INDEX idx_buyer_companies_industry ON buyer_companies(industry);
CREATE INDEX idx_buyer_companies_funding_stage ON buyer_companies(funding_stage);
CREATE INDEX idx_buyer_companies_requirements ON buyer_companies USING GIN(requirements);

-- ==========================================
-- MATCHES
-- ==========================================
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- References
    provider_id VARCHAR(255) REFERENCES service_providers(provider_id),
    buyer_id VARCHAR(255) REFERENCES buyer_companies(buyer_id),
    
    -- Match scoring
    match_score INTEGER DEFAULT 0,
    
    -- Score breakdown
    score_breakdown JSONB DEFAULT '{}',
    
    -- Match status workflow
    status VARCHAR(50) DEFAULT 'pending',
    
    -- Intro tracking
    intro_sent_at TIMESTAMP WITH TIME ZONE,
    intro_message_id VARCHAR(255),
    
    -- Meeting tracking
    meeting_booked_at TIMESTAMP WITH TIME ZONE,
    meeting_date TIMESTAMP WITH TIME ZONE,
    meeting_status VARCHAR(50),
    
    -- Revenue tracking
    revenue_share_amount INTEGER DEFAULT 0,
    deal_value INTEGER,
    deal_closed_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    match_reason TEXT,
    provider_approved BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_matches_match_id ON matches(match_id);
CREATE INDEX idx_matches_provider_id ON matches(provider_id);
CREATE INDEX idx_matches_buyer_id ON matches(buyer_id);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_score ON matches(match_score);

-- ==========================================
-- PROVIDER BILLING
-- ==========================================
CREATE TABLE provider_billing (
    id SERIAL PRIMARY KEY,
    billing_id VARCHAR(255) UNIQUE NOT NULL,
    provider_id VARCHAR(255) REFERENCES service_providers(provider_id),
    
    -- Charge details
    charge_type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Description
    description VARCHAR(500),
    
    -- Related match (for intro/success fees)
    match_id VARCHAR(255) REFERENCES matches(match_id),
    
    -- Stripe/ payment info
    stripe_invoice_id VARCHAR(255),
    stripe_payment_intent_id VARCHAR(255),
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    paid_at TIMESTAMP WITH TIME ZONE,
    
    -- Period
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_provider_billing_billing_id ON provider_billing(billing_id);
CREATE INDEX idx_provider_billing_provider_id ON provider_billing(provider_id);
CREATE INDEX idx_provider_billing_charge_type ON provider_billing(charge_type);
CREATE INDEX idx_provider_billing_status ON provider_billing(status);
CREATE INDEX idx_provider_billing_created_at ON provider_billing(created_at);

-- ==========================================
-- PLATFORM REVENUE SUMMARY
-- ==========================================
CREATE TABLE platform_revenue_summary (
    id SERIAL PRIMARY KEY,
    
    -- Period
    period_type VARCHAR(20) NOT NULL,
    period_start DATE NOT NULL,
    
    -- Revenue breakdown
    subscription_revenue INTEGER DEFAULT 0,
    intro_fee_revenue INTEGER DEFAULT 0,
    success_fee_revenue INTEGER DEFAULT 0,
    
    -- Totals
    total_revenue INTEGER DEFAULT 0,
    
    -- Volume metrics
    active_providers INTEGER DEFAULT 0,
    new_providers INTEGER DEFAULT 0,
    total_matches INTEGER DEFAULT 0,
    intros_sent INTEGER DEFAULT 0,
    meetings_booked INTEGER DEFAULT 0,
    deals_closed INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_platform_revenue_summary_period ON platform_revenue_summary(period_type, period_start);

-- ==========================================
-- TRIGGERS FOR UPDATED_AT
-- ==========================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_service_providers_updated_at
    BEFORE UPDATE ON service_providers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_provider_subscriptions_updated_at
    BEFORE UPDATE ON provider_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_buyer_companies_updated_at
    BEFORE UPDATE ON buyer_companies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matches_updated_at
    BEFORE UPDATE ON matches
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_provider_subscriptions_updated_at_2
    BEFORE UPDATE ON provider_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- SEED DATA - EXAMPLE PROVIDER
-- ==========================================
INSERT INTO service_providers (
    provider_id, company_name, website, description, services, industries,
    icp_criteria, case_studies, differentiator, contact_email, billing_email, active, onboarding_complete
) VALUES (
    'prov-example01',
    'CloudMigration Co',
    'https://cloudmigration.example.com',
    'Expert cloud migration services for growing companies',
    '["AWS Migration", "Azure Migration", "Cloud Strategy", "Cost Optimization"]',
    '["SaaS", "Fintech", "Healthcare"]',
    '{"funding_stage": ["Series A+", "Series B"], "employees": "50-500", "signals": ["recent_funding", "hiring_engineers"]}',
    '[{"title": "Migrated 50+ companies to AWS", "result": "Average 40% cost reduction"}]',
    'Zero-downtime migration guarantee',
    'sales@cloudmigration.example.com',
    'billing@cloudmigration.example.com',
    TRUE,
    TRUE
);

-- ==========================================
-- SEED DATA - EXAMPLE BUYER
-- ==========================================
INSERT INTO buyer_companies (
    buyer_id, company_name, website, industry, employee_count,
    funding_stage, total_funding, requirements, budget_range, timeline, signals,
    decision_maker_name, decision_maker_title, decision_maker_email, verified, active
) VALUES (
    'buyer-example01',
    'TechStartupXYZ',
    'https://techstartup.example.com',
    'SaaS',
    120,
    'series_b',
    '$20M',
    '["cloud_migration", "devops", "infrastructure"]',
    '$50K-$100K',
    '3_months',
    '["recent_funding", "hiring_engineers", "expansion"]',
    'John Smith',
    'CTO',
    'john.smith@techstartup.example.com',
    TRUE,
    TRUE
);
