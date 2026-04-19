"""Pydantic validation models for all API endpoints"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict
from datetime import datetime


class ImportLeadsRequest(BaseModel):
    """Request model for importing leads"""
    json_path: str = Field(default="data/leads.json", min_length=1, max_length=500)
    
    @validator('json_path')
    def validate_json_path(cls, v):
        if not v.endswith('.json'):
            raise ValueError('Path must end with .json')
        return v


class GenerateBatchRequest(BaseModel):
    """Request model for generating outbound batch"""
    from_email: EmailStr
    max_leads: int = Field(default=50, ge=1, le=500)
    min_fit_score: int = Field(default=7, ge=1, le=10)
    
    @validator('from_email')
    def validate_from_email(cls, v):
        if not v.endswith(('@gmail.com', '@company.com')):
            raise ValueError('Email must be from allowed domain')
        return v


class ClassifyReplyRequest(BaseModel):
    """Request model for classifying a reply"""
    reply_id: str = Field(..., min_length=1, max_length=255)


class PipelineTransitionRequest(BaseModel):
    """Request model for pipeline transition"""
    new_state: str = Field(..., pattern="^(NEW|QUALIFIED|CONTACTED|REPLIED|INTERESTED|CALL_BOOKED|CLOSED|LOST|SUPPRESSED)$")
    stage_data: Optional[Dict] = None


class CreateDealRequest(BaseModel):
    """Request model for creating a deal"""
    lead_id: str = Field(..., min_length=1, max_length=255)
    deal_name: str = Field(..., min_length=1, max_length=500)
    deal_value: float = Field(..., ge=0)
    deal_stage: str = Field(default="prospecting")
    
    @validator('deal_stage')
    def validate_deal_stage(cls, v):
        allowed_stages = ["prospecting", "qualification", "needs_analysis", "value_proposition", 
                         "proposal", "negotiation", "closing"]
        if v not in allowed_stages:
            raise ValueError(f'Stage must be one of: {allowed_stages}')
        return v


class CreateExperimentRequest(BaseModel):
    """Request model for creating an experiment"""
    name: str = Field(..., min_length=1, max_length=255)
    experiment_type: str = Field(..., pattern="^(subject|message|cta)$")
    variants: Dict[str, str]
    target_segment: Optional[str] = None
    sample_size: int = Field(default=100, ge=10, le=10000)
    
    @validator('variants')
    def validate_variants(cls, v):
        if len(v) < 2:
            raise ValueError('At least 2 variants required for A/B test')
        if len(v) > 5:
            raise ValueError('Maximum 5 variants allowed')
        return v


class EscalationAssignRequest(BaseModel):
    """Request model for assigning an escalation"""
    assigned_to: str = Field(..., min_length=1, max_length=255)


class EscalationResolveRequest(BaseModel):
    """Request model for resolving an escalation"""
    resolution_notes: str = Field(..., min_length=1, max_length=5000)


class IdempotencyRequest(BaseModel):
    """Request model with idempotency key"""
    idempotency_key: Optional[str] = Field(None, min_length=10, max_length=255)


class WebhookPayload(BaseModel):
    """Request model for Gmail webhook"""
    emailAddress: EmailStr
    historyId: int
    
    
class LeadScoreResponse(BaseModel):
    """Response model for lead scoring"""
    lead_id: str
    priority_score: float
    is_qualified: bool
    disqualification_reason: Optional[str]
    recommended_action: str
    dimension_scores: Dict[str, int]


class PipelineStateResponse(BaseModel):
    """Response model for pipeline state"""
    lead_id: str
    current_state: str
    previous_state: Optional[str]
    time_in_state_seconds: int
    total_pipeline_days: int
    state_history: List[Dict]


class DealResponse(BaseModel):
    """Response model for deal"""
    deal_id: str
    lead_id: str
    deal_name: str
    deal_value: float
    deal_stage: str
    win_probability: int
    status: str
    created_at: datetime


class MetricsResponse(BaseModel):
    """Response model for system metrics"""
    leads: Dict
    campaigns: Dict
    messages: Dict
    replies: Dict
    suppression: Dict
    timestamp: datetime


class ExperimentResponse(BaseModel):
    """Response model for experiment"""
    experiment_id: str
    name: str
    experiment_type: str
    status: str
    total_participants: int
    winner: Optional[str]
    variant_stats: Dict


class PerformanceReportResponse(BaseModel):
    """Response model for performance report"""
    overall_reply_rate: float
    total_sent: int
    total_replied: int
    best_performing_subjects: List[Dict]
    recommendations: Dict
    generated_at: datetime


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str]
    code: Optional[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str
    version: str
    timestamp: datetime
    checks: Dict[str, bool]


class CreateLeadRequest(BaseModel):
    """Request model for creating a lead"""
    lead_id: Optional[str] = Field(None, min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=500)
    website: Optional[str] = Field(None, max_length=500)
    signal: str = Field(..., min_length=10, max_length=2000)
    decision_maker: Optional[str] = Field(None, max_length=255)
    fit_score: int = Field(default=7, ge=1, le=10)
    pain_point: Optional[str] = Field(None, max_length=1000)
    urgency_reason: Optional[str] = Field(None, max_length=500)
    custom_hook: Optional[str] = Field(None, max_length=1000)
    message: Optional[str] = Field(None, max_length=5000)
    followups: Optional[List[str]] = Field(default_factory=list)
    
    @validator('website')
    def validate_website(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Website must start with http:// or https://')
        return v


class UpdateLeadRequest(BaseModel):
    """Request model for updating a lead"""
    company: Optional[str] = Field(None, min_length=1, max_length=500)
    website: Optional[str] = Field(None, max_length=500)
    signal: Optional[str] = Field(None, min_length=10, max_length=2000)
    decision_maker: Optional[str] = Field(None, max_length=255)
    fit_score: Optional[int] = Field(None, ge=1, le=10)
    pain_point: Optional[str] = Field(None, max_length=1000)
    urgency_reason: Optional[str] = Field(None, max_length=500)
    custom_hook: Optional[str] = Field(None, max_length=1000)
    message: Optional[str] = Field(None, max_length=5000)
    followups: Optional[List[str]] = None
    status: Optional[str] = Field(None, pattern="^(new|sent|replied|positive|not_now|not_interested|unsubscribe|bounced|failed)$")
    
    @validator('website')
    def validate_website(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Website must start with http:// or https://')
        return v


class LeadResponse(BaseModel):
    """Response model for a lead"""
    lead_id: str
    company: str
    website: Optional[str]
    signal: str
    decision_maker: Optional[str]
    fit_score: int
    pain_point: Optional[str]
    urgency_reason: Optional[str]
    custom_hook: Optional[str]
    message: Optional[str]
    followups: Optional[List[str]]
    status: str
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    """Response model for listing leads"""
    total: int
    page: int
    page_size: int
    leads: List[LeadResponse]


class BulkCreateLeadRequest(BaseModel):
    """Request model for bulk lead creation"""
    leads: List[CreateLeadRequest]
    skip_duplicates: bool = Field(default=True, description="Skip leads with duplicate company names")
    auto_score: bool = Field(default=True, description="Automatically run qualification scoring after import")
    
    @validator('leads')
    def validate_leads(cls, v):
        if len(v) > 1000:
            raise ValueError('Maximum 1000 leads per bulk request')
        if len(v) == 0:
            raise ValueError('At least one lead required')
        return v


class BulkLeadResponse(BaseModel):
    """Response model for bulk lead operations"""
    total_submitted: int
    created: int
    skipped: int
    failed: int
    errors: List[Dict]
    lead_ids: List[str]


# Template Validators

class CreateTemplateRequest(BaseModel):
    """Request model for creating a message template"""
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    subject_template: str = Field(..., min_length=1, max_length=500)
    body_template: str = Field(..., min_length=10, max_length=10000)
    signal_keywords: List[str] = Field(default_factory=list)
    is_default: bool = Field(default=False)
    variant_of: Optional[str] = Field(None, description="ID of parent template if this is a variant")


class UpdateTemplateRequest(BaseModel):
    """Request model for updating a message template"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    subject_template: Optional[str] = Field(None, min_length=1, max_length=500)
    body_template: Optional[str] = Field(None, min_length=10, max_length=10000)
    signal_keywords: Optional[List[str]] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Response model for a template"""
    template_id: str
    name: str
    category: str
    description: Optional[str]
    subject_template: str
    body_template: str
    signal_keywords: List[str]
    usage_count: int
    reply_count: int
    reply_rate: int
    performance_score: int
    is_default: bool
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class TemplateListResponse(BaseModel):
    """Response model for listing templates"""
    total: int
    templates: List[TemplateResponse]


class TemplatePerformanceReport(BaseModel):
    """Response model for template performance"""
    template_id: str
    name: str
    category: str
    usage_count: int
    reply_count: int
    positive_reply_count: int
    reply_rate: int
    performance_score: int
    ranking: int  # Position in category ranking
