from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String(255), unique=True, nullable=False, index=True)
    company = Column(String(500), nullable=False)
    website = Column(String(500))
    signal = Column(Text)
    decision_maker = Column(String(255))
    fit_score = Column(Integer, default=0, index=True)
    message_intent = Column(Text)
    status = Column(String(50), default="new", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    outbound_messages = relationship("OutboundMessage", back_populates="lead")


class CampaignRun(Base):
    __tablename__ = "campaign_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    status = Column(String(50), default="pending", index=True)
    total_leads = Column(Integer, default=0)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    outbound_messages = relationship("OutboundMessage", back_populates="campaign_run")


class OutboundMessage(Base):
    __tablename__ = "outbound_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), unique=True, nullable=False, index=True)
    run_id = Column(String(255), ForeignKey("campaign_runs.run_id"), index=True)
    lead_id = Column(String(255), ForeignKey("leads.lead_id"), index=True)
    subject = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    to_email = Column(String(500), nullable=False)
    from_email = Column(String(500), nullable=False)
    status = Column(String(50), default="queued", index=True)
    gmail_message_id = Column(String(255), index=True)
    gmail_thread_id = Column(String(255), index=True)
    sent_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Template tracking for performance analysis
    template_id = Column(String(255), ForeignKey("templates.template_id"), nullable=True, index=True)
    personalization_method = Column(String(50), default="ai_generated")  # template, custom, ai_generated
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    campaign_run = relationship("CampaignRun", back_populates="outbound_messages")
    lead = relationship("Lead", back_populates="outbound_messages")
    replies = relationship("Reply", back_populates="message")
    followups = relationship("Followup", back_populates="message")
    template = relationship("Template", back_populates="outbound_messages")


class Reply(Base):
    __tablename__ = "replies"
    
    id = Column(Integer, primary_key=True, index=True)
    reply_id = Column(String(255), unique=True, nullable=False)
    message_id = Column(String(255), ForeignKey("outbound_messages.message_id"), index=True)
    lead_id = Column(String(255), ForeignKey("leads.lead_id"), index=True)
    gmail_message_id = Column(String(255), nullable=False)
    gmail_thread_id = Column(String(255), nullable=False, index=True)
    from_email = Column(String(500), nullable=False)
    subject = Column(Text)
    body = Column(Text, nullable=False)
    classification = Column(String(50), index=True)
    processed_at = Column(DateTime(timezone=True))
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    message = relationship("OutboundMessage", back_populates="replies")


class Followup(Base):
    __tablename__ = "followups"
    
    id = Column(Integer, primary_key=True, index=True)
    followup_id = Column(String(255), unique=True, nullable=False)
    message_id = Column(String(255), ForeignKey("outbound_messages.message_id"), index=True)
    lead_id = Column(String(255), ForeignKey("leads.lead_id"), index=True)
    sequence_number = Column(Integer, nullable=False)
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(50), default="scheduled", index=True)
    subject = Column(Text)
    body = Column(Text)
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    message = relationship("OutboundMessage", back_populates="followups")


class SuppressionList(Base):
    __tablename__ = "suppression_list"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(500), unique=True, nullable=False, index=True)
    reason = Column(String(255))
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    lead_id = Column(String(255))


class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(255), unique=True, nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(255), nullable=False, index=True)
    data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class LeadScore(Base):
    __tablename__ = "lead_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Signal dimensions
    signal_strength = Column(Integer, default=0)
    hiring_intensity = Column(Integer, default=0)
    funding_stage = Column(Integer, default=0)
    company_size_fit = Column(Integer, default=0)
    market_relevance = Column(Integer, default=0)
    
    # Computed scores
    priority_score = Column(Integer, default=0)
    qualification_score = Column(Integer, default=0)
    
    # Qualification decision
    is_qualified = Column(Boolean, default=False, index=True)
    qualified_at = Column(DateTime(timezone=True))
    disqualification_reason = Column(Text)
    
    # Metadata
    score_version = Column(String(50), default='v1')
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OfferStrategy(Base):
    __tablename__ = "offer_strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    
    # Signal matching
    signal_type = Column(String(100), nullable=False, index=True)
    signal_keywords = Column(JSON)
    
    # Offer definition
    offer_angle = Column(Text, nullable=False)
    message_style = Column(String(100), nullable=False)
    cta_type = Column(String(100), nullable=False)
    
    # Performance tracking
    total_sent = Column(Integer, default=0)
    total_replies = Column(Integer, default=0)
    reply_rate = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConversationMemory(Base):
    __tablename__ = "conversation_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    memory_id = Column(String(255), unique=True, nullable=False)
    lead_id = Column(String(255), ForeignKey("leads.lead_id"), index=True)
    thread_id = Column(String(255), index=True)
    
    # Conversation state
    tone = Column(String(100))
    relationship_stage = Column(String(100))
    objection_raised = Column(Text)
    last_topic = Column(Text)
    
    # Email history
    emails_sent = Column(Integer, default=0)
    replies_received = Column(Integer, default=0)
    
    # Context
    context_summary = Column(Text)
    key_points = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DeliverabilityRule(Base):
    __tablename__ = "deliverability_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(255), unique=True, nullable=False)
    domain = Column(String(255), nullable=False, index=True)
    
    # Domain health
    domain_warmed = Column(Boolean, default=False)
    warmup_start_date = Column(DateTime(timezone=True))
    warmup_end_date = Column(DateTime(timezone=True))
    
    # Send limits
    max_sends_per_hour = Column(Integer, default=30)
    max_sends_per_day = Column(Integer, default=200)
    current_hourly_count = Column(Integer, default=0)
    current_daily_count = Column(Integer, default=0)
    
    # Inbox rotation
    primary_inbox = Column(String(255))
    backup_inboxes = Column(JSON)
    
    # Health metrics
    bounce_rate = Column(Integer, default=0)
    spam_rate = Column(Integer, default=0)
    health_score = Column(Integer, default=100)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_id = Column(String(255), unique=True, nullable=False)
    
    # Metric dimensions
    dimension_type = Column(String(100), nullable=False, index=True)
    dimension_value = Column(String(255), nullable=False, index=True)
    
    # Metrics
    total_sent = Column(Integer, default=0)
    total_replies = Column(Integer, default=0)
    total_converted = Column(Integer, default=0)
    
    # Rates
    reply_rate = Column(Integer, default=0)
    conversion_rate = Column(Integer, default=0)
    
    # Statistical significance
    sample_size = Column(Integer, default=0)
    confidence_level = Column(Integer)
    
    # Trend
    trend_direction = Column(String(20))
    
    # Metadata
    period_start = Column(Date)
    period_end = Column(Date)
    
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())


class PipelineState(Base):
    __tablename__ = "pipeline_states"
    
    id = Column(Integer, primary_key=True, index=True)
    state_id = Column(String(255), unique=True, nullable=False)
    lead_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Current state
    current_state = Column(String(50), default='NEW', index=True)
    previous_state = Column(String(50))
    
    # State transitions
    entered_current_state_at = Column(DateTime(timezone=True), server_default=func.now())
    state_history = Column(JSON, default=list)
    
    # Pipeline metrics
    time_in_state_seconds = Column(Integer, default=0)
    total_pipeline_days = Column(Integer, default=0)
    
    # Stage-specific data
    stage_data = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Experiment(Base):
    __tablename__ = "experiments"
    
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    experiment_type = Column(String(100), nullable=False, index=True)
    
    # Variants
    variants = Column(JSON, nullable=False)
    
    # Targeting
    target_segment = Column(String(100))
    sample_size = Column(Integer)
    
    # Status
    status = Column(String(50), default='active', index=True)
    statistical_significance = Column(Boolean, default=False)
    winner = Column(String(255))
    
    # Timeline
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Results
    total_participants = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ExperimentResult(Base):
    __tablename__ = "experiment_results"
    
    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(String(255), unique=True, nullable=False)
    experiment_id = Column(String(255), ForeignKey("experiments.experiment_id"), index=True)
    message_id = Column(String(255), ForeignKey("outbound_messages.message_id"))
    
    variant = Column(String(255), nullable=False, index=True)
    
    # Outcomes
    replied = Column(Boolean, default=False)
    replied_at = Column(DateTime(timezone=True))
    converted = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HumanEscalationQueue(Base):
    __tablename__ = "human_escalation_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    escalation_id = Column(String(255), unique=True, nullable=False)
    lead_id = Column(String(255), ForeignKey("leads.lead_id"))
    message_id = Column(String(255), ForeignKey("outbound_messages.message_id"))
    reply_id = Column(String(255), ForeignKey("replies.reply_id"))
    
    # Escalation reason
    escalation_reason = Column(String(100), nullable=False)
    priority = Column(String(50), default='normal', index=True)
    
    # Context
    context_summary = Column(Text)
    
    # Assignment
    assigned_to = Column(String(255))
    assigned_at = Column(DateTime(timezone=True))
    
    # Resolution
    status = Column(String(50), default='pending', index=True)
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Deal(Base):
    __tablename__ = "deals"
    
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(String(255), unique=True, nullable=False)
    lead_id = Column(String(255), ForeignKey("leads.lead_id"), index=True)
    
    # Deal details
    deal_name = Column(String(500))
    deal_value = Column(Integer)
    deal_stage = Column(String(50), default='prospecting', index=True)
    
    # Probability
    win_probability = Column(Integer, default=0)
    
    # Timeline
    expected_close_date = Column(Date)
    actual_close_date = Column(Date)
    
    # Owner
    owner_id = Column(String(255))
    owner_type = Column(String(50), default='system', index=True)
    
    # Source tracking
    source_campaign = Column(String(255))
    source_message_id = Column(String(255), ForeignKey("outbound_messages.message_id"))
    
    # Status
    status = Column(String(50), default='open', index=True)
    lost_reason = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Template(Base):
    """Message templates for AI personalization"""
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Template metadata
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)  # funding, hiring, product_launch, etc.
    description = Column(Text)
    
    # Template content
    subject_template = Column(Text, nullable=False)
    body_template = Column(Text, nullable=False)
    
    # Signal matching keywords (JSON array of keywords that trigger this template)
    signal_keywords = Column(JSON, default=list)
    
    # Performance tracking
    usage_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    positive_reply_count = Column(Integer, default=0)
    reply_rate = Column(Integer, default=0)  # Stored as percentage (e.g., 25 = 25%)
    performance_score = Column(Integer, default=50)  # 0-100 score for ranking
    
    # A/B testing
    variant_of = Column(String(255), nullable=True)  # Stores template_id as string reference (soft reference, no FK constraint)
    is_active = Column(Boolean, default=True, index=True)
    is_default = Column(Boolean, default=False)  # Default template for category
    
    # Versioning
    version = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    outbound_messages = relationship("OutboundMessage", back_populates="template")


# ==========================================
# B2B MATCHMAKING PLATFORM MODELS
# ==========================================

class ServiceProvider(Base):
    """Service providers who pay for platform access"""
    __tablename__ = "service_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Company info
    company_name = Column(String(255), nullable=False)
    website = Column(String(500))
    description = Column(Text)
    
    # Services offered
    services = Column(JSON, default=list)  # ["AWS Migration", "Cloud Strategy"]
    industries = Column(JSON, default=list)  # ["SaaS", "Fintech"]
    
    # Ideal Customer Profile (ICP)
    icp_criteria = Column(JSON, default=dict)  # {
        # "funding_stage": ["Series A+", "late_stage"],
        # "employees": "50-500",
        # "signals": ["recent_funding", "hiring_engineers"]
    # }
    
    # Case studies & social proof
    case_studies = Column(JSON, default=list)  # [{"title": "Migrated 50+ companies", "result": "..."}]
    differentiator = Column(Text)  # "Zero-downtime migration guarantee"
    
    # Contact & billing
    contact_email = Column(String(500), nullable=False)
    billing_email = Column(String(500))
    
    # Status
    active = Column(Boolean, default=True, index=True)
    onboarding_complete = Column(Boolean, default=False)

    # Automation opt-in consent
    auto_outreach_enabled = Column(Boolean, default=False)
    outreach_consent_status = Column(String(50), default="pending")  # pending, consented, declined
    outreach_consent_date = Column(DateTime(timezone=True))
    opt_in_email_sent_at = Column(DateTime(timezone=True))
    provider_response_received_at = Column(DateTime(timezone=True))
    provider_response_text = Column(Text)  # Store provider's actual response
    sentiment_analysis_result = Column(JSON)  # Store sentiment analysis

    # Automation settings
    automation_settings = Column(JSON, default=dict)  # {
        # "max_emails_per_day": 30,
        # "min_match_score": 70,
        # "auto_approve_matches": True,
        # "template_type": "intro"
    # }

    # Stripe/customer IDs
    stripe_customer_id = Column(String(255))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    subscriptions = relationship("ProviderSubscription", back_populates="provider")
    matches = relationship("Match", back_populates="provider")
    billings = relationship("ProviderBilling", back_populates="provider")


class ProviderSubscription(Base):
    """Subscription plans for service providers"""
    __tablename__ = "provider_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(String(255), unique=True, nullable=False, index=True)
    provider_id = Column(String(255), ForeignKey("service_providers.provider_id"), index=True)
    
    # Plan details
    plan_type = Column(String(50), nullable=False)  # basic, premium, enterprise
    plan_name = Column(String(255))  # "Basic - $500/month"
    
    # Pricing
    monthly_amount = Column(Integer, default=0)  # in cents (e.g., 50000 = $500)
    intro_fee_per_meeting = Column(Integer, default=0)  # e.g., 5000 = $50
    
    # Limits
    max_matches_per_month = Column(Integer, default=50)
    max_intros_per_month = Column(Integer, default=100)
    
    # Usage tracking
    matches_used_this_month = Column(Integer, default=0)
    intros_sent_this_month = Column(Integer, default=0)
    meetings_booked_this_month = Column(Integer, default=0)
    
    # Billing cycle
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    
    # Status
    status = Column(String(50), default='active', index=True)  # active, cancelled, past_due
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    provider = relationship("ServiceProvider", back_populates="subscriptions")


class BuyerCompany(Base):
    """Companies looking for services (buyers)"""
    __tablename__ = "buyer_companies"
    
    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Company info
    company_name = Column(String(255), nullable=False)
    website = Column(String(500))
    industry = Column(String(100))
    
    # Company signals
    employee_count = Column(Integer)
    funding_stage = Column(String(50))  # seed, series_a, series_b, etc.
    total_funding = Column(String(100))  # "$20M"
    
    # What they need
    requirements = Column(JSON, default=list)  # ["cloud_migration", "devops"]
    budget_range = Column(String(100))  # "$10K-$50K"
    timeline = Column(String(50))  # immediate, 3_months, 6_months, exploring
    
    # Signals indicating need
    signals = Column(JSON, default=list)  # ["hiring_devops", "recent_funding"]
    
    # Decision maker
    decision_maker_name = Column(String(255))
    decision_maker_title = Column(String(255))
    decision_maker_email = Column(String(500))
    
    # Status
    verified = Column(Boolean, default=False, index=True)
    active = Column(Boolean, default=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    matches = relationship("Match", back_populates="buyer")


class Match(Base):
    """AI-calculated matches between providers and buyers"""
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # References
    provider_id = Column(String(255), ForeignKey("service_providers.provider_id"), index=True)
    buyer_id = Column(String(255), ForeignKey("buyer_companies.buyer_id"), index=True)
    
    # Match scoring
    match_score = Column(Integer, default=0)  # 0-100 AI-calculated fit
    
    # Score breakdown
    score_breakdown = Column(JSON, default=dict)  # {
        # "service_fit": 95,
        # "size_fit": 80,
        # "timing_fit": 70,
        # "budget_fit": 85,
        # "signal_fit": 90
    # }
    
    # Match status workflow
    status = Column(String(50), default='pending', index=True)  # 
        # pending → approved → intro_sent → meeting_booked → closed_won/closed_lost
    
    # Intro tracking
    intro_sent_at = Column(DateTime(timezone=True))
    intro_message_id = Column(String(255))  # Reference to outbound_messages
    
    # Follow-up tracking
    followup_count = Column(Integer, default=0)  # Number of follow-ups sent
    last_followup_sent_at = Column(DateTime(timezone=True))
    response_received = Column(Boolean, default=False)
    response_received_at = Column(DateTime(timezone=True))
    
    # Meeting tracking
    meeting_booked_at = Column(DateTime(timezone=True))
    meeting_date = Column(DateTime(timezone=True))
    meeting_status = Column(String(50))  # scheduled, completed, no_show, cancelled
    
    # Revenue tracking
    revenue_share_amount = Column(Integer, default=0)  # Platform's cut in cents
    deal_value = Column(Integer)  # Total deal value if known
    deal_closed_at = Column(DateTime(timezone=True))
    
    # Metadata
    match_reason = Column(Text)  # AI explanation of why this is a good match
    provider_approved = Column(Boolean, default=False)  # Provider reviewed & approved
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    provider = relationship("ServiceProvider", back_populates="matches")
    buyer = relationship("BuyerCompany", back_populates="matches")


class ProviderBilling(Base):
    """Billing records for platform revenue tracking"""
    __tablename__ = "provider_billing"
    
    id = Column(Integer, primary_key=True, index=True)
    billing_id = Column(String(255), unique=True, nullable=False, index=True)
    provider_id = Column(String(255), ForeignKey("service_providers.provider_id"), index=True)
    
    # Charge details
    charge_type = Column(String(50), nullable=False, index=True)  # subscription, intro_fee, success_fee
    amount = Column(Integer, nullable=False)  # in cents
    currency = Column(String(3), default='USD')
    
    # Description
    description = Column(String(500))  # "Monthly subscription - Basic Plan"
    
    # Related match (for intro/success fees)
    match_id = Column(String(255), ForeignKey("matches.match_id"))
    
    # Stripe/ payment info
    stripe_invoice_id = Column(String(255))
    stripe_payment_intent_id = Column(String(255))
    
    # Status
    status = Column(String(50), default='pending', index=True)  # pending, paid, failed, refunded
    paid_at = Column(DateTime(timezone=True))
    
    # Period
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    provider = relationship("ServiceProvider", back_populates="billings")


class PlatformRevenueSummary(Base):
    """Daily/Monthly revenue aggregation for platform analytics"""
    __tablename__ = "platform_revenue_summary"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Period
    period_type = Column(String(20), nullable=False, index=True)  # daily, monthly
    period_start = Column(Date, nullable=False, index=True)
    
    # Revenue breakdown
    subscription_revenue = Column(Integer, default=0)  # Monthly fees
    intro_fee_revenue = Column(Integer, default=0)    # Pay-per-meeting
    success_fee_revenue = Column(Integer, default=0)  # % of closed deals
    
    # Totals
    total_revenue = Column(Integer, default=0)
    
    # Volume metrics
    active_providers = Column(Integer, default=0)
    new_providers = Column(Integer, default=0)
    total_matches = Column(Integer, default=0)
    intros_sent = Column(Integer, default=0)
    meetings_booked = Column(Integer, default=0)
    deals_closed = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
