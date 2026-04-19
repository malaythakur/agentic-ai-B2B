from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import uuid
import json

from app.database import get_db
from app.auth import get_current_user, get_current_admin_user, check_rate_limit
from app.services.lead_loader import LeadLoader
from app.services.batch_builder import BatchBuilder
from app.services.gmail_sender import GmailSender
from app.classifiers.reply_classifier import ReplyClassifier
from app.services.lead_qualification import LeadQualificationEngine
from app.services.pipeline_state_machine import PipelineStateMachine
from app.services.crm import CRMLayer
from app.services.experimentation import ExperimentationLayer
from app.services.human_escalation import HumanEscalationLayer
from app.services.feedback_learning import FeedbackLearningLoop
from app.services.prospect_discovery import ProspectDiscoveryService
from app.services.prospect_scoring import ProspectScoringService
from app.services.outbound_outreach import OutboundOutreachService
from app.services.lead_enrichment_pipeline import LeadEnrichmentPipeline
from app.services.transactional_billing import TransactionalBillingService
from app.workers.tasks import import_leads_task, generate_batch_task, send_batch_task, classify_reply_task, autonomous_discovery_task

# B2B Matchmaking Platform Services
from app.services.b2b_buyer_discovery import B2BBuyerDiscoveryService
from app.services.b2b_response_tracking import B2BResponseTrackingService
from app.services.b2b_followup_service import B2BFollowupService
from app.services.b2b_provider_dashboard import B2BProviderDashboardService
from app.services.b2b_analytics_dashboard import B2BAnalyticsDashboardService
from app.services.b2b_provider_discovery import B2BProviderDiscoveryService

# B2B Celery Tasks
from app.workers.tasks import (
    run_b2b_buyer_discovery_task,
    check_buyer_responses_task,
    run_b2b_followups_task
)
from app.services.b2b_provider_discovery import run_b2b_provider_discovery_task
from app.models import CampaignRun, OutboundMessage, Lead, Event
from app.validators import (
    CreateLeadRequest,
    UpdateLeadRequest,
    BulkCreateLeadRequest,
    LeadResponse,
    LeadListResponse,
    BulkLeadResponse,
    CreateTemplateRequest,
    UpdateTemplateRequest
)

router = APIRouter()


class ImportLeadsRequest(BaseModel):
    json_path: str = "data/leads.json"


class GenerateBatchRequest(BaseModel):
    from_email: str
    max_leads: int = 50
    min_fit_score: int = 7


class ClassifyReplyRequest(BaseModel):
    reply_id: str


@router.post("/import/leads")
async def import_leads(
    request: ImportLeadsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Import leads from JSON file into PostgreSQL"""
    try:
        loader = LeadLoader(db)
        results = loader.load_from_json(request.json_path)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/leads/async")
async def import_leads_async(
    request: ImportLeadsRequest,
    background_tasks: BackgroundTasks
):
    """Import leads from JSON file asynchronously via Celery"""
    task = import_leads_task.delay(request.json_path)
    return {"status": "queued", "task_id": task.id}


@router.post("/generate/outbound-batch")
async def generate_outbound_batch(
    request: GenerateBatchRequest,
    db: Session = Depends(get_db)
):
    """Generate outbound batch from eligible leads"""
    try:
        builder = BatchBuilder(db)
        results = builder.build_batch(
            from_email=request.from_email,
            max_leads=request.max_leads,
            min_fit_score=request.min_fit_score
        )
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/outbound-batch/async")
async def generate_outbound_batch_async(
    request: GenerateBatchRequest
):
    """Generate outbound batch asynchronously via Celery"""
    task = generate_batch_task.delay(
        request.from_email,
        request.max_leads,
        request.min_fit_score
    )
    return {"status": "queued", "task_id": task.id}


@router.post("/send/batch/{run_id}")
async def send_batch(
    run_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send all messages in a batch"""
    try:
        sender = GmailSender(db)
        results = sender.send_batch(run_id)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/batch/{run_id}/async")
async def send_batch_async(run_id: str):
    """Send batch asynchronously via Celery"""
    task = send_batch_task.delay(run_id)
    return {"status": "queued", "task_id": task.id}


@router.post("/webhooks/gmail")
async def gmail_webhook(
    payload: dict,
    db: Session = Depends(get_db)
):
    """Handle Gmail push notifications for mailbox changes"""
    # This would process the Gmail webhook payload
    # and trigger thread fetching/reply classification
    return {"status": "received", "message": "Webhook processed"}


@router.post("/replies/classify")
async def classify_reply(
    request: ClassifyReplyRequest,
    db: Session = Depends(get_db)
):
    """Classify a reply and update lead state"""
    try:
        classifier = ReplyClassifier(db)
        result = classifier.classify_and_process(request.reply_id)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/replies/classify/async")
async def classify_reply_async(request: ClassifyReplyRequest):
    """Classify reply asynchronously via Celery"""
    task = classify_reply_task.delay(request.reply_id)
    return {"status": "queued", "task_id": task.id}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: Session = Depends(get_db)):
    """Get campaign run details"""
    run = db.query(CampaignRun).filter(CampaignRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    messages = db.query(OutboundMessage).filter(
        OutboundMessage.run_id == run_id
    ).all()
    
    return {
        "run": {
            "run_id": run.run_id,
            "name": run.name,
            "status": run.status,
            "total_leads": run.total_leads,
            "generated_at": run.generated_at,
            "started_at": run.started_at,
            "completed_at": run.completed_at
        },
        "messages": [
            {
                "message_id": msg.message_id,
                "lead_id": msg.lead_id,
                "subject": msg.subject,
                "to_email": msg.to_email,
                "status": msg.status,
                "sent_at": msg.sent_at
            }
            for msg in messages
        ]
    }


@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """Get system metrics"""
    total_leads = db.query(Lead).count()
    total_runs = db.query(CampaignRun).count()
    total_messages = db.query(OutboundMessage).count()
    
    sent_messages = db.query(OutboundMessage).filter(
        OutboundMessage.status == 'sent'
    ).count()
    
    failed_messages = db.query(OutboundMessage).filter(
        OutboundMessage.status == 'failed'
    ).count()
    
    queued_messages = db.query(OutboundMessage).filter(
        OutboundMessage.status == 'queued'
    ).count()
    
    from app.models import Reply
    total_replies = db.query(Reply).count()
    
    positive_replies = db.query(Reply).filter(
        Reply.classification == 'interested'
    ).count()
    
    from app.models import SuppressionList
    total_suppressed = db.query(SuppressionList).count()
    
    return {
        "leads": {
            "total": total_leads,
            "by_status": {}
        },
        "campaigns": {
            "total_runs": total_runs
        },
        "messages": {
            "total": total_messages,
            "sent": sent_messages,
            "failed": failed_messages,
            "queued": queued_messages,
            "reply_rate": round((total_replies / sent_messages * 100) if sent_messages > 0 else 0, 2)
        },
        "replies": {
            "total": total_replies,
            "positive": positive_replies,
            "positive_rate": round((positive_replies / total_replies * 100) if total_replies > 0 else 0, 2)
        },
        "suppression": {
            "total_suppressed": total_suppressed
        }
    }


# Advanced Feature Endpoints

@router.post("/discovery/run")
async def run_discovery():
    """Manually trigger autonomous lead discovery"""
    task = autonomous_discovery_task.delay()
    return {"status": "queued", "task_id": task.id, "message": "Discovery task started"}


@router.post("/qualification/score/{lead_id}")
async def score_lead(lead_id: str, db: Session = Depends(get_db)):
    """Score a lead using the qualification engine"""
    try:
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        engine = LeadQualificationEngine(db)
        result = engine.score_lead(lead)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qualification/batch")
async def batch_score_leads(db: Session = Depends(get_db)):
    """Score all leads using the qualification engine"""
    try:
        engine = LeadQualificationEngine(db)
        results = engine.batch_score_leads()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/{lead_id}")
async def get_pipeline_state(lead_id: str, db: Session = Depends(get_db)):
    """Get pipeline state for a lead"""
    try:
        pipeline = PipelineStateMachine(db)
        state = pipeline.get_state(lead_id)
        return {"status": "success", "data": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/{lead_id}/transition")
async def transition_pipeline_state(
    lead_id: str,
    new_state: str,
    db: Session = Depends(get_db)
):
    """Transition a lead to a new pipeline state"""
    try:
        pipeline = PipelineStateMachine(db)
        result = pipeline.transition(lead_id, new_state)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/funnel")
async def get_conversion_funnel(db: Session = Depends(get_db)):
    """Get conversion funnel by state"""
    try:
        pipeline = PipelineStateMachine(db)
        funnel = pipeline.get_conversion_funnel()
        return {"status": "success", "data": funnel}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crm/deals")
async def create_deal(
    lead_id: str,
    deal_name: str,
    deal_value: float,
    deal_stage: str = "prospecting",
    db: Session = Depends(get_db)
):
    """Create a new deal for a lead"""
    try:
        crm = CRMLayer(db)
        deal = crm.create_deal(lead_id, deal_name, deal_value, deal_stage)
        return {"status": "success", "data": deal}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/crm/deals/{deal_id}")
async def get_deal(deal_id: str, db: Session = Depends(get_db)):
    """Get deal details"""
    try:
        crm = CRMLayer(db)
        deal = crm.get_deal(deal_id)
        return {"status": "success", "data": deal}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/crm/pipeline-value")
async def get_pipeline_value(db: Session = Depends(get_db)):
    """Get total pipeline value"""
    try:
        crm = CRMLayer(db)
        value = crm.get_pipeline_value()
        return {"status": "success", "data": value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/crm/roi")
async def get_roi_metrics(db: Session = Depends(get_db)):
    """Get ROI metrics"""
    try:
        crm = CRMLayer(db)
        metrics = crm.get_roi_metrics()
        return {"status": "success", "data": metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments")
async def create_experiment(
    name: str,
    experiment_type: str,
    variants: dict,
    target_segment: Optional[str] = None,
    sample_size: int = 100,
    db: Session = Depends(get_db)
):
    """Create a new A/B experiment"""
    try:
        exp = ExperimentationLayer(db)
        result = exp.create_experiment(name, experiment_type, list(variants.values()), target_segment, sample_size)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments")
async def get_experiments(db: Session = Depends(get_db)):
    """Get all active experiments"""
    try:
        exp = ExperimentationLayer(db)
        experiments = exp.get_active_experiments()
        return {"status": "success", "data": experiments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}")
async def get_experiment_results(experiment_id: str, db: Session = Depends(get_db)):
    """Get results for an experiment"""
    try:
        exp = ExperimentationLayer(db)
        results = exp.get_experiment_results(experiment_id)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/escalation/queue")
async def get_escalation_queue(priority: Optional[str] = None, db: Session = Depends(get_db)):
    """Get pending escalations"""
    try:
        escalation = HumanEscalationLayer(db)
        queue = escalation.get_pending_escalations(priority)
        return {"status": "success", "data": queue}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/escalation/{escalation_id}/assign")
async def assign_escalation(escalation_id: str, assigned_to: str, db: Session = Depends(get_db)):
    """Assign an escalation to a human"""
    try:
        escalation = HumanEscalationLayer(db)
        result = escalation.assign_escalation(escalation_id, assigned_to)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/escalation/{escalation_id}/resolve")
async def resolve_escalation(escalation_id: str, resolution_notes: str, db: Session = Depends(get_db)):
    """Resolve an escalation"""
    try:
        escalation = HumanEscalationLayer(db)
        result = escalation.resolve_escalation(escalation_id, resolution_notes)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/performance")
async def get_performance_report(db: Session = Depends(get_db)):
    """Get performance report from feedback learning"""
    try:
        learning = FeedbackLearningLoop(db)
        report = learning.get_performance_report()
        return {"status": "success", "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/best-subjects")
async def get_best_subjects(limit: int = 10, db: Session = Depends(get_db)):
    """Get best performing subjects"""
    try:
        learning = FeedbackLearningLoop(db)
        subjects = learning.get_best_performing_subjects(limit)
        return {"status": "success", "data": subjects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Lead CRUD Endpoints

@router.post("/leads")
async def create_lead(
    request: CreateLeadRequest,
    db: Session = Depends(get_db)
):
    """Create a new lead directly via API (no JSON file needed)"""
    try:
        # Generate lead_id if not provided
        lead_id = request.lead_id or f"lead-{str(uuid.uuid4())[:8]}"
        
        # Check for duplicate
        existing = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Lead with ID {lead_id} already exists")
        
        # Create lead
        lead = Lead(
            lead_id=lead_id,
            company=request.company,
            website=request.website,
            signal=request.signal,
            decision_maker=request.decision_maker,
            fit_score=request.fit_score,
            pain_point=request.pain_point,
            urgency_reason=request.urgency_reason,
            custom_hook=request.custom_hook,
            message=request.message,
            followups=json.dumps(request.followups) if request.followups else None,
            status="new"
        )
        
        db.add(lead)
        db.commit()
        db.refresh(lead)
        
        # Auto-score the lead
        engine = LeadQualificationEngine(db)
        score_result = engine.score_lead(lead)
        
        return {
            "status": "success",
            "data": {
                "lead_id": lead.lead_id,
                "company": lead.company,
                "is_qualified": score_result["is_qualified"],
                "priority_score": score_result["priority_score"],
                "created_at": lead.created_at.isoformat() if lead.created_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/leads/batch")
async def create_leads_batch(
    request: BulkCreateLeadRequest,
    db: Session = Depends(get_db)
):
    """Create multiple leads in one request"""
    try:
        created_leads = []
        skipped_leads = []
        failed_leads = []
        errors = []
        
        for lead_data in request.leads:
            try:
                lead_id = lead_data.lead_id or f"lead-{str(uuid.uuid4())[:8]}"
                
                # Check for duplicates
                if request.skip_duplicates:
                    existing = db.query(Lead).filter(
                        (Lead.lead_id == lead_id) | (Lead.company == lead_data.company)
                    ).first()
                    if existing:
                        skipped_leads.append({"company": lead_data.company, "reason": "Duplicate"})
                        continue
                
                # Create lead
                lead = Lead(
                    lead_id=lead_id,
                    company=lead_data.company,
                    website=lead_data.website,
                    signal=lead_data.signal,
                    decision_maker=lead_data.decision_maker,
                    fit_score=lead_data.fit_score,
                    pain_point=lead_data.pain_point,
                    urgency_reason=lead_data.urgency_reason,
                    custom_hook=lead_data.custom_hook,
                    message=lead_data.message,
                    followups=json.dumps(lead_data.followups) if lead_data.followups else None,
                    status="new"
                )
                
                db.add(lead)
                created_leads.append(lead)
                
            except Exception as e:
                failed_leads.append({"company": lead_data.company, "error": str(e)})
                errors.append({"company": lead_data.company, "error": str(e)})
        
        db.commit()
        
        # Auto-score if requested
        if request.auto_score and created_leads:
            engine = LeadQualificationEngine(db)
            for lead in created_leads:
                engine.score_lead(lead)
        
        return {
            "status": "success",
            "data": {
                "total_submitted": len(request.leads),
                "created": len(created_leads),
                "skipped": len(skipped_leads),
                "failed": len(failed_leads),
                "errors": errors[:10],  # Limit errors in response
                "lead_ids": [lead.lead_id for lead in created_leads]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leads")
async def list_leads(
    status: Optional[str] = Query(None, description="Filter by status"),
    is_qualified: Optional[bool] = Query(None, description="Filter by qualification status"),
    min_fit_score: Optional[int] = Query(None, ge=1, le=10, description="Minimum fit score"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search company name"),
    db: Session = Depends(get_db)
):
    """List all leads with optional filters"""
    try:
        query = db.query(Lead)
        
        # Apply filters
        if status:
            query = query.filter(Lead.status == status)
        if min_fit_score:
            query = query.filter(Lead.fit_score >= min_fit_score)
        if search:
            query = query.filter(Lead.company.ilike(f"%{search}%"))
        
        # Get total count
        total = query.count()
        
        # Get qualified status if requested
        leads_data = []
        leads = query.offset((page - 1) * page_size).limit(page_size).all()
        
        for lead in leads:
            lead_dict = {
                "lead_id": lead.lead_id,
                "company": lead.company,
                "website": lead.website,
                "signal": lead.signal[:100] + "..." if len(lead.signal) > 100 else lead.signal,
                "decision_maker": lead.decision_maker,
                "fit_score": lead.fit_score,
                "status": lead.status,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
                "updated_at": lead.updated_at.isoformat() if lead.updated_at else None
            }
            
            if is_qualified is not None:
                from app.models import LeadScore
                score = db.query(LeadScore).filter(LeadScore.lead_id == lead.lead_id).first()
                lead_dict["is_qualified"] = score.is_qualified if score else False
                lead_dict["priority_score"] = score.priority_score if score else 0
            
            leads_data.append(lead_dict)
        
        return {
            "status": "success",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "leads": leads_data
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a single lead"""
    try:
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Get qualification score
        from app.models import LeadScore
        score = db.query(LeadScore).filter(LeadScore.lead_id == lead_id).first()
        
        # Get pipeline state
        from app.models import PipelineState
        pipeline = db.query(PipelineState).filter(PipelineState.lead_id == lead_id).first()
        
        return {
            "status": "success",
            "data": {
                "lead_id": lead.lead_id,
                "company": lead.company,
                "website": lead.website,
                "signal": lead.signal,
                "decision_maker": lead.decision_maker,
                "fit_score": lead.fit_score,
                "pain_point": lead.pain_point,
                "urgency_reason": lead.urgency_reason,
                "custom_hook": lead.custom_hook,
                "message": lead.message,
                "followups": json.loads(lead.followups) if lead.followups else [],
                "status": lead.status,
                "qualification": {
                    "is_qualified": score.is_qualified if score else None,
                    "priority_score": score.priority_score if score else None,
                    "dimension_scores": {
                        "signal_strength": score.signal_strength if score else 0,
                        "hiring_intensity": score.hiring_intensity if score else 0,
                        "funding_stage": score.funding_stage if score else 0,
                        "company_size_fit": score.company_size_fit if score else 0,
                        "market_relevance": score.market_relevance if score else 0
                    } if score else None
                },
                "pipeline": {
                    "current_state": pipeline.current_state if pipeline else "NEW",
                    "previous_state": pipeline.previous_state if pipeline else None,
                    "total_pipeline_days": pipeline.total_pipeline_days if pipeline else 0
                },
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
                "updated_at": lead.updated_at.isoformat() if lead.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/leads/{lead_id}")
async def update_lead(
    lead_id: str,
    request: UpdateLeadRequest,
    db: Session = Depends(get_db)
):
    """Update an existing lead"""
    try:
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Update fields
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "followups" and value is not None:
                value = json.dumps(value)
            if hasattr(lead, field):
                setattr(lead, field, value)
        
        db.commit()
        db.refresh(lead)
        
        return {
            "status": "success",
            "data": {
                "lead_id": lead.lead_id,
                "company": lead.company,
                "updated_at": lead.updated_at.isoformat() if lead.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, db: Session = Depends(get_db)):
    """Delete a lead (soft delete - adds to suppression list)"""
    try:
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Add to suppression list instead of hard delete
        from app.models import SuppressionList
        suppressed = SuppressionList(
            lead_id=lead_id,
            email=None,  # Could extract email if available
            reason="Manual deletion via API"
        )
        db.add(suppressed)
        
        # Update lead status
        lead.status = "unsubscribe"
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Lead {lead_id} deleted and added to suppression list"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# External Integration Webhooks

@router.post("/webhooks/lead-ingestion")
async def lead_ingestion_webhook(
    payload: dict,
    source: str = Query(..., description="Source system (hubspot, salesforce, zapier, etc.)"),
    api_key: str = Query(..., description="API key for authentication"),
    db: Session = Depends(get_db)
):
    """Webhook for external CRM systems to push leads directly"""
    try:
        # Validate API key (in production, use proper secret management)
        expected_key = getattr(settings, 'WEBHOOK_API_KEY', 'webhook-secret-key')
        if api_key != expected_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Transform payload based on source system
        lead_data = _transform_webhook_payload(payload, source)
        
        if not lead_data:
            raise HTTPException(status_code=400, detail=f"Unable to parse payload from {source}")
        
        # Check for duplicate by company name
        existing = db.query(Lead).filter(Lead.company == lead_data["company"]).first()
        if existing:
            return {
                "status": "skipped",
                "reason": "Duplicate company",
                "existing_lead_id": existing.lead_id
            }
        
        # Create lead
        lead = Lead(
            lead_id=f"lead-{str(uuid.uuid4())[:8]}",
            **lead_data
        )
        
        db.add(lead)
        db.commit()
        db.refresh(lead)
        
        # Auto-score
        engine = LeadQualificationEngine(db)
        score_result = engine.score_lead(lead)
        
        return {
            "status": "success",
            "data": {
                "lead_id": lead.lead_id,
                "company": lead.company,
                "source": source,
                "is_qualified": score_result["is_qualified"],
                "priority_score": score_result["priority_score"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _transform_webhook_payload(payload: dict, source: str) -> dict:
    """Transform various CRM payloads into our lead format"""
    
    if source.lower() == "hubspot":
        # HubSpot contact/company format
        properties = payload.get("properties", {})
        return {
            "company": properties.get("company", "Unknown Company"),
            "website": properties.get("website", ""),
            "signal": f"HubSpot contact: {properties.get('jobtitle', 'Unknown')}. "
                      f"Industry: {properties.get('industry', 'Unknown')}. "
                      f"Company size: {properties.get('num_employees', 'Unknown')}",
            "decision_maker": f"{properties.get('firstname', '')} {properties.get('lastname', '')}".strip(),
            "fit_score": 7,  # Default, will be rescored
            "pain_point": None,
            "urgency_reason": None,
            "custom_hook": None,
            "message": None,
            "followups": None,
            "status": "new"
        }
    
    elif source.lower() == "salesforce":
        # Salesforce lead/account format
        return {
            "company": payload.get("Company", payload.get("Name", "Unknown Company")),
            "website": payload.get("Website", ""),
            "signal": f"Salesforce lead: {payload.get('Title', 'Unknown')}. "
                      f"Industry: {payload.get('Industry', 'Unknown')}. "
                      f"Size: {payload.get('NumberOfEmployees', 'Unknown')}",
            "decision_maker": f"{payload.get('FirstName', '')} {payload.get('LastName', '')}".strip(),
            "fit_score": 7,
            "pain_point": None,
            "urgency_reason": None,
            "custom_hook": None,
            "message": None,
            "followups": None,
            "status": "new"
        }
    
    elif source.lower() == "zapier":
        # Generic Zapier format - assumes mapped fields
        return {
            "company": payload.get("company", "Unknown Company"),
            "website": payload.get("website", ""),
            "signal": payload.get("signal", "Imported via Zapier"),
            "decision_maker": payload.get("decision_maker", ""),
            "fit_score": int(payload.get("fit_score", 7)),
            "pain_point": payload.get("pain_point"),
            "urgency_reason": payload.get("urgency_reason"),
            "custom_hook": payload.get("custom_hook"),
            "message": payload.get("message"),
            "followups": json.dumps(payload.get("followups", [])) if payload.get("followups") else None,
            "status": "new"
        }
    
    elif source.lower() == "linkedin":
        # LinkedIn Sales Navigator format
        return {
            "company": payload.get("companyName", "Unknown Company"),
            "website": payload.get("companyWebsite", ""),
            "signal": f"LinkedIn: {payload.get('headline', 'Profile')}. "
                      f"Company: {payload.get('companyName', 'Unknown')}. "
                      f"Industry: {payload.get('companyIndustry', 'Unknown')}",
            "decision_maker": payload.get("fullName", ""),
            "fit_score": 7,
            "pain_point": None,
            "urgency_reason": None,
            "custom_hook": None,
            "message": None,
            "followups": None,
            "status": "new"
        }
    
    elif source.lower() == "apollo":
        # Apollo.io format
        return {
            "company": payload.get("organization", {}).get("name", "Unknown Company"),
            "website": payload.get("organization", {}).get("website_url", ""),
            "signal": f"Apollo: {payload.get('title', 'Unknown')}. "
                      f"Industry: {payload.get('organization', {}).get('industry', 'Unknown')}. "
                      f"Employees: {payload.get('organization', {}).get('estimated_num_employees', 'Unknown')}",
            "decision_maker": f"{payload.get('first_name', '')} {payload.get('last_name', '')}".strip(),
            "fit_score": 7,
            "pain_point": None,
            "urgency_reason": None,
            "custom_hook": None,
            "message": None,
            "followups": None,
            "status": "new"
        }
    
    else:
        # Generic format - assumes standard field names
        return {
            "company": payload.get("company", payload.get("companyName", "Unknown Company")),
            "website": payload.get("website", payload.get("companyWebsite", "")),
            "signal": payload.get("signal", payload.get("description", "Imported via webhook")),
            "decision_maker": payload.get("decision_maker", payload.get("contactName", "")),
            "fit_score": int(payload.get("fit_score", 7)),
            "pain_point": payload.get("pain_point"),
            "urgency_reason": payload.get("urgency_reason"),
            "custom_hook": payload.get("custom_hook"),
            "message": payload.get("message"),
            "followups": json.dumps(payload.get("followups", [])) if payload.get("followups") else None,
            "status": "new"
        }


# Template Management Endpoints

@router.post("/templates")
async def create_template(
    request: CreateTemplateRequest,
    db: Session = Depends(get_db)
):
    """Create a new message template"""
    try:
        from app.services.template_service import TemplateService
        service = TemplateService(db)
        
        template = service.create_template(
            name=request.name,
            category=request.category,
            description=request.description,
            subject_template=request.subject_template,
            body_template=request.body_template,
            signal_keywords=request.signal_keywords,
            is_default=request.is_default,
            variant_of=request.variant_of
        )
        
        return {
            "status": "success",
            "data": {
                "template_id": template.template_id,
                "name": template.name,
                "category": template.category,
                "is_default": template.is_default,
                "created_at": template.created_at.isoformat() if template.created_at else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: bool = Query(True, description="Only active templates"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List all message templates"""
    try:
        from app.services.template_service import TemplateService
        service = TemplateService(db)
        
        templates = service.list_templates(
            category=category,
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        
        return {
            "status": "success",
            "data": {
                "total": len(templates),
                "templates": [
                    {
                        "template_id": t.template_id,
                        "name": t.name,
                        "category": t.category,
                        "description": t.description,
                        "signal_keywords": t.signal_keywords,
                        "usage_count": t.usage_count,
                        "reply_rate": t.reply_rate,
                        "performance_score": t.performance_score,
                        "is_default": t.is_default,
                        "is_active": t.is_active,
                        "version": t.version
                    }
                    for t in templates
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}")
async def get_template(template_id: str, db: Session = Depends(get_db)):
    """Get a specific template"""
    try:
        from app.services.template_service import TemplateService
        service = TemplateService(db)
        
        template = service.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "status": "success",
            "data": {
                "template_id": template.template_id,
                "name": template.name,
                "category": template.category,
                "description": template.description,
                "subject_template": template.subject_template,
                "body_template": template.body_template,
                "signal_keywords": template.signal_keywords,
                "usage_count": template.usage_count,
                "reply_count": template.reply_count,
                "reply_rate": template.reply_rate,
                "performance_score": template.performance_score,
                "is_default": template.is_default,
                "is_active": template.is_active,
                "version": template.version,
                "created_at": template.created_at.isoformat() if template.created_at else None,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    db: Session = Depends(get_db)
):
    """Update a template"""
    try:
        from app.services.template_service import TemplateService
        service = TemplateService(db)
        
        updates = request.dict(exclude_unset=True)
        template = service.update_template(template_id, **updates)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "status": "success",
            "data": {
                "template_id": template.template_id,
                "name": template.name,
                "version": template.version,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, db: Session = Depends(get_db)):
    """Delete (soft delete) a template"""
    try:
        from app.services.template_service import TemplateService
        service = TemplateService(db)
        
        success = service.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "status": "success",
            "message": f"Template {template_id} deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/categories")
async def get_template_categories():
    """Get list of available template categories"""
    from app.services.template_service import TEMPLATE_CATEGORIES
    
    return {
        "status": "success",
        "data": {
            "categories": [
                {"id": k, "description": v}
                for k, v in TEMPLATE_CATEGORIES.items()
            ]
        }
    }


@router.get("/templates/performance/report")
async def get_template_performance_report(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """Get performance report for templates"""
    try:
        from app.services.template_service import TemplateService
        service = TemplateService(db)
        
        report = service.get_template_performance_report(category=category)
        
        # Add ranking
        for i, item in enumerate(report, 1):
            item["ranking"] = i
        
        return {
            "status": "success",
            "data": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/seed-defaults")
async def seed_default_templates(db: Session = Depends(get_db)):
    """Seed default templates (admin only)"""
    try:
        from app.services.template_service import initialize_default_templates
        initialize_default_templates(db)
        
        return {
            "status": "success",
            "message": "Default templates seeded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Billionaire CEO Automation Endpoints

@router.post("/automation/ingest/crunchbase")
async def ingest_from_crunchbase(
    query: str = Query(..., description="Search query for Crunchbase"),
    funding_stage: Optional[str] = Query(None, description="Filter by funding stage"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Ingest leads from Crunchbase API"""
    try:
        from app.services.lead_ingestion import LeadIngestionService
        service = LeadIngestionService(db)
        results = await service.ingest_from_crunchbase(query, funding_stage, industry, limit)
        await service.close()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/ingest/apollo")
async def ingest_from_apollo(
    industry: Optional[str] = Query(None, description="Filter by industry"),
    company_size: Optional[str] = Query(None, description="Filter by company size"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Ingest leads from Apollo.io API"""
    try:
        from app.services.lead_ingestion import LeadIngestionService
        service = LeadIngestionService(db)
        results = await service.ingest_from_apollo(industry, company_size, limit)
        await service.close()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/ingest/linkedin")
async def ingest_from_linkedin(
    keywords: str = Query(..., description="Search keywords for LinkedIn"),
    company_size: Optional[str] = Query(None, description="Filter by company size"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Ingest leads from LinkedIn Sales Navigator"""
    try:
        from app.services.lead_ingestion import LeadIngestionService
        service = LeadIngestionService(db)
        results = await service.ingest_from_linkedin_sales_nav(keywords, company_size, limit)
        await service.close()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/score/{lead_id}")
async def score_lead_ai(lead_id: str, use_ai: bool = Query(False), db: Session = Depends(get_db)):
    """Score a lead using AI-powered scoring"""
    try:
        from app.services.ai_lead_scoring import AILeadScoringService
        service = AILeadScoringService(db)
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        result = service.score_lead(lead, use_ai=use_ai)
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/score/batch")
async def batch_score_leads(
    lead_ids: List[str],
    use_ai: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Score multiple leads in batch"""
    try:
        from app.services.ai_lead_scoring import AILeadScoringService
        service = AILeadScoringService(db)
        results = service.batch_score_leads(lead_ids, use_ai=use_ai)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation/similar/{lead_id}")
async def find_similar_leads(
    lead_id: str,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Find leads similar to a given lead"""
    try:
        from app.services.ai_lead_scoring import AILeadScoringService
        service = AILeadScoringService(db)
        results = service.find_similar_leads(lead_id, limit)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/signal/detect/{company_name}")
async def detect_signals(company_name: str, db: Session = Depends(get_db)):
    """Detect all signals for a company"""
    try:
        from app.services.signal_detection import SignalDetectionService
        service = SignalDetectionService(db)
        results = await service.scan_all_signals_for_company(company_name)
        await service.close()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/signal/batch")
async def detect_signals_batch(
    company_names: List[str],
    db: Session = Depends(get_db)
):
    """Detect signals for multiple companies"""
    try:
        from app.services.signal_detection import SignalDetectionService
        service = SignalDetectionService(db)
        results = await service.monitor_signals_batch(company_names)
        await service.close()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/tier/classify")
async def classify_leads_by_tier(
    lead_ids: List[str],
    db: Session = Depends(get_db)
):
    """Classify leads into tiers based on scoring"""
    try:
        from app.services.tiered_automation import TieredAutomationService
        service = TieredAutomationService(db)
        results = service.classify_leads_by_tier(lead_ids)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/tier/process-tier1")
async def process_tier1_batch(
    from_email: str,
    max_leads: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Auto-send Tier 1 leads immediately"""
    try:
        from app.services.tiered_automation import TieredAutomationService
        service = TieredAutomationService(db)
        results = service.process_tier_1_batch(from_email, max_leads)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation/tier/review-queue")
async def get_tier2_review_queue(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get Tier 2 review queue"""
    try:
        from app.services.tiered_automation import TieredAutomationService
        service = TieredAutomationService(db)
        results = service.process_tier_2_review_queue(limit)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/tier/approve-tier2")
async def approve_tier2_leads(
    lead_ids: List[str],
    from_email: str,
    db: Session = Depends(get_db)
):
    """Approve and send Tier 2 leads"""
    try:
        from app.services.tiered_automation import TieredAutomationService
        service = TieredAutomationService(db)
        results = service.approve_tier_2_leads(lead_ids, from_email)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation/tier/stats")
async def get_automation_stats(db: Session = Depends(get_db)):
    """Get tiered automation statistics"""
    try:
        from app.services.tiered_automation import TieredAutomationService
        service = TieredAutomationService(db)
        results = service.get_automation_stats()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AutomationCycleRequest(BaseModel):
    from_email: str
    auto_approve_tier2: bool = True


@router.post("/automation/cycle/run")
async def run_automation_cycle(
    request: AutomationCycleRequest,
    db: Session = Depends(get_db)
):
    """Run complete daily automation cycle"""
    try:
        from app.services.tiered_automation import TieredAutomationService
        service = TieredAutomationService(db)
        results = service.run_daily_automation_cycle(request.from_email, request.auto_approve_tier2)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/safeguards/check/{email}")
async def check_safeguards(
    email: str,
    domain: str,
    company: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Run all safeguard checks before sending"""
    try:
        from app.services.safeguards import SafeguardsService
        service = SafeguardsService(db)
        results = service.run_all_safeguard_checks(email, domain, company)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/safeguards/suppress")
async def add_to_suppression(
    email: str,
    reason: str,
    lead_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Add email to suppression list"""
    try:
        from app.services.safeguards import SafeguardsService
        service = SafeguardsService(db)
        success = service.add_to_suppression_list(email, reason, lead_id)
        return {"status": "success", "added": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/safeguards/auto-suppress")
async def auto_suppress_bounces(
    bounce_threshold: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """Automatically suppress bouncing emails"""
    try:
        from app.services.safeguards import SafeguardsService
        service = SafeguardsService(db)
        results = service.auto_suppress_bounces(bounce_threshold)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/safeguards/auto-suppress-unsubscribes")
async def auto_suppress_unsubscribes(db: Session = Depends(get_db)):
    """Automatically suppress unsubscribe requests"""
    try:
        from app.services.safeguards import SafeguardsService
        service = SafeguardsService(db)
        results = service.auto_suppress_unsubscribes()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/safeguards/summary")
async def get_safeguards_summary(db: Session = Depends(get_db)):
    """Get safeguards status summary"""
    try:
        from app.services.safeguards import SafeguardsService
        service = SafeguardsService(db)
        results = service.get_safeguards_summary()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/abtesting/create")
async def create_ab_test(
    experiment_name: str,
    subject_variants: List[str],
    target_segment: Optional[str] = "all",
    db: Session = Depends(get_db)
):
    """Create A/B test for subject lines"""
    try:
        from app.services.ab_testing import ABTestingService
        service = ABTestingService(db)
        experiment = service.create_subject_line_experiment(experiment_name, subject_variants, target_segment)
        return {"status": "success", "data": {"experiment_id": experiment.experiment_id}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/abtesting/assign/{experiment_id}")
async def assign_variant(experiment_id: str, db: Session = Depends(get_db)):
    """Assign a variant for a message"""
    try:
        from app.services.ab_testing import ABTestingService
        service = ABTestingService(db)
        variant = service.assign_variant(experiment_id)
        return {"status": "success", "data": {"variant": variant}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/abtesting/record")
async def record_experiment_result(
    experiment_id: str,
    message_id: str,
    variant: str,
    replied: bool = False,
    db: Session = Depends(get_db)
):
    """Record experiment result"""
    try:
        from app.services.ab_testing import ABTestingService
        service = ABTestingService(db)
        service.record_experiment_result(experiment_id, message_id, variant, replied)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/abtesting/analyze/{experiment_id}")
async def analyze_experiment(experiment_id: str, db: Session = Depends(get_db)):
    """Analyze experiment results"""
    try:
        from app.services.ab_testing import ABTestingService
        service = ABTestingService(db)
        results = service.analyze_experiment(experiment_id)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/abtesting/optimize/{template_id}")
async def auto_optimize_template(template_id: str, db: Session = Depends(get_db)):
    """Auto-optimize subject lines for a template"""
    try:
        from app.services.ab_testing import ABTestingService
        service = ABTestingService(db)
        template = db.query(Template).filter(Template.template_id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        results = service.auto_optimize_subject_lines(template_id, template.subject_template)
        return {"status": "success", "data": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/abtesting/recommended/{template_id}")
async def get_recommended_subject(template_id: str, db: Session = Depends(get_db)):
    """Get statistically best subject line"""
    try:
        from app.services.ab_testing import ABTestingService
        service = ABTestingService(db)
        subject = service.get_recommended_subject(template_id)
        return {"status": "success", "data": {"subject": subject}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/abtesting/dashboard")
async def get_ab_testing_dashboard(db: Session = Depends(get_db)):
    """Get A/B testing dashboard"""
    try:
        from app.services.ab_testing import ABTestingService
        service = ABTestingService(db)
        results = service.get_experiment_dashboard()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# AI-Powered Personalization Endpoints

@router.post("/ai/personalize/{message_id}")
async def ai_personalize_message(message_id: str, db: Session = Depends(get_db)):
    """AI-generate personalized content for a message"""
    try:
        from app.services.ai_email_generator import AIEmailGenerator
        generator = AIEmailGenerator(db)
        success = generator.update_outbound_message_with_ai(message_id)
        return {"status": "success", "updated": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/personalize/batch/{run_id}")
async def ai_personalize_batch(run_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """AI-personalize all messages in a batch"""
    try:
        from app.workers.tasks import ai_personalize_messages_task
        task = ai_personalize_messages_task.delay(run_id)
        return {"status": "queued", "task_id": task.id, "run_id": run_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/generate-email/{lead_id}")
async def generate_ai_email(lead_id: str, db: Session = Depends(get_db)):
    """Generate AI-powered email for a lead"""
    try:
        from app.services.ai_email_generator import AIEmailGenerator
        from app.models import Lead
        
        generator = AIEmailGenerator(db)
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        email = generator.generate_personalized_email(lead)
        return {"status": "success", "data": email}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Automated Follow-Up Endpoints

@router.post("/automation/followup/run")
async def run_followup_automation(db: Session = Depends(get_db)):
    """Run automated follow-up check and send"""
    try:
        from app.services.followup_automation import FollowUpAutomation
        automation = FollowUpAutomation(db)
        results = automation.run_followup_check()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation/followup/stats")
async def get_followup_stats(db: Session = Depends(get_db)):
    """Get follow-up performance statistics"""
    try:
        from app.services.followup_automation import FollowUpAutomation
        automation = FollowUpAutomation(db)
        results = automation.get_followup_stats()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/reply/process/{reply_id}")
async def process_reply_automation(reply_id: str, db: Session = Depends(get_db)):
    """Process a reply and take automated action"""
    try:
        from app.services.followup_automation import ReplyAutoResponder
        responder = ReplyAutoResponder(db)
        result = responder.process_new_reply(reply_id)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Enhanced Full Automation Cycle

class FullAutomationRequest(BaseModel):
    from_email: str
    query: str = "SaaS companies"
    limit: int = 10
    auto_approve_tier2: bool = True
    ai_personalize: bool = True


@router.post("/automation/full-cycle")
async def run_full_automation_cycle(
    request: FullAutomationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Run complete end-to-end automation: ingest → score → approve → personalize → send"""
    try:
        from app.services.lead_ingestion import LeadIngestionService
        from app.services.ai_lead_scoring import AILeadScoringService
        from app.services.tiered_automation import TieredAutomationService
        from app.services.ai_email_generator import AIEmailGenerator
        from app.workers.tasks import ai_personalize_messages_task
        import asyncio
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "steps": []
        }
        
        # Step 1: Ingest leads from external source
        ingestion_service = LeadIngestionService(db)
        ingestion_result = await ingestion_service.ingest_from_crunchbase(
            query=request.query,
            limit=request.limit
        )
        await ingestion_service.close()
        results["steps"].append({"step": "ingestion", "result": ingestion_result})
        
        if ingestion_result["ingested"] == 0:
            return {"status": "no_leads", "message": "No new leads ingested", "data": results}
        
        # Step 2: AI Score all new leads
        scoring_service = AILeadScoringService(db)
        new_lead_ids = ingestion_result["leads"]
        scoring_result = scoring_service.batch_score_leads(new_lead_ids, use_ai=True)
        results["steps"].append({"step": "scoring", "result": scoring_result})
        
        # Step 3: Classify into tiers and auto-approve
        tier_service = TieredAutomationService(db)
        tier_result = tier_service.classify_leads_by_tier(new_lead_ids)
        results["steps"].append({"step": "tier_classification", "result": tier_result})
        
        # Step 4: Process tier 1 (auto-send) and auto-approve tier 2
        cycle_result = tier_service.run_daily_automation_cycle(
            request.from_email,
            auto_approve_tier2=request.auto_approve_tier2
        )
        results["steps"].append({"step": "automation_cycle", "result": cycle_result})
        
        # Step 5: AI Personalize all queued messages
        if request.ai_personalize:
            for step in cycle_result["steps"]:
                if step["step"] in ["process_tier1_batch", "auto_approve_tier2"]:
                    if "run_id" in step["result"]:
                        run_id = step["result"]["run_id"]
                        # Queue AI personalization task
                        task = ai_personalize_messages_task.delay(run_id)
                        results["steps"].append({
                            "step": "ai_personalization_queued",
                            "run_id": run_id,
                            "task_id": task.id
                        })
        
        # Step 6: Get final stats
        stats = tier_service.get_automation_stats()
        results["steps"].append({"step": "final_stats", "result": stats})
        
        logger.info(f"Full automation cycle complete: {ingestion_result['ingested']} leads processed")
        return {"status": "success", "data": results}
        
    except Exception as e:
        logger.error(f"Full automation cycle failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# B2B MATCHMAKING PLATFORM ENDPOINTS
# ==========================================

# Provider Management Endpoints

class CreateProviderRequest(BaseModel):
    company_name: str
    contact_email: str
    services: List[str]
    website: Optional[str] = None
    description: Optional[str] = None
    industries: Optional[List[str]] = None
    icp_criteria: Optional[Dict] = None
    case_studies: Optional[List[Dict]] = None
    differentiator: Optional[str] = None
    billing_email: Optional[str] = None


@router.post("/platform/providers")
async def create_provider(
    request: CreateProviderRequest,
    db: Session = Depends(get_db)
):
    """Create a new service provider on the platform"""
    try:
        from app.services.provider_management import ProviderManagementService
        service = ProviderManagementService(db)
        
        provider = service.create_provider(
            company_name=request.company_name,
            contact_email=request.contact_email,
            services=request.services,
            website=request.website,
            description=request.description,
            industries=request.industries,
            icp_criteria=request.icp_criteria,
            case_studies=request.case_studies,
            differentiator=request.differentiator,
            billing_email=request.billing_email
        )
        
        return {
            "status": "success",
            "data": {
                "provider_id": provider.provider_id,
                "company_name": provider.company_name,
                "contact_email": provider.contact_email,
                "created_at": provider.created_at.isoformat() if provider.created_at else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/providers")
async def list_providers(
    active_only: bool = Query(True),
    plan_type: str = Query(None),
    industry: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all service providers"""
    try:
        from app.services.provider_management import ProviderManagementService
        service = ProviderManagementService(db)
        
        results = service.list_providers(
            active_only=active_only,
            plan_type=plan_type,
            industry=industry,
            page=page,
            page_size=page_size
        )
        
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/providers/{provider_id}")
async def get_provider(provider_id: str, db: Session = Depends(get_db)):
    """Get provider details with stats"""
    try:
        from app.services.provider_management import ProviderManagementService
        service = ProviderManagementService(db)
        
        stats = service.get_provider_stats(provider_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return {"status": "success", "data": stats}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/platform/providers/{provider_id}")
async def update_provider(
    provider_id: str,
    updates: Dict,
    db: Session = Depends(get_db)
):
    """Update provider information"""
    try:
        from app.services.provider_management import ProviderManagementService
        service = ProviderManagementService(db)
        
        provider = service.update_provider(provider_id, **updates)
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return {
            "status": "success",
            "data": {
                "provider_id": provider.provider_id,
                "company_name": provider.company_name,
                "updated_at": provider.updated_at.isoformat() if provider.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/platform/providers/{provider_id}")
async def delete_provider(provider_id: str, db: Session = Depends(get_db)):
    """Deactivate a provider"""
    try:
        from app.services.provider_management import ProviderManagementService
        service = ProviderManagementService(db)
        
        success = service.delete_provider(provider_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return {"status": "success", "message": f"Provider {provider_id} deactivated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Provider Subscription Endpoints

@router.post("/platform/providers/{provider_id}/opt-in")
async def send_provider_optin(
    provider_id: str,
    from_email: str = Query(..., description="Platform email to send from"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Send opt-in email to provider for automated outreach consent"""
    try:
        from app.settings import settings
        from app.services.provider_optin_service import ProviderOptInService
        
        service = ProviderOptInService(
            db=db,
            gmail_credentials_path=settings.GMAIL_CREDENTIALS_PATH,
            gmail_token_path=settings.GMAIL_TOKEN_PATH,
            gemini_api_key=settings.GEMINI_API_KEY
        )
        
        result = service.send_optin_email(provider_id, from_email)
        
        if result.get("success"):
            return {"status": "success", "data": result}
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/providers/{provider_id}/check-response")
async def check_provider_response(
    provider_id: str,
    platform_email: str = Query(..., description="Platform email to check responses to"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Check if provider has responded to opt-in email"""
    try:
        from app.settings import settings
        from app.services.provider_optin_service import ProviderOptInService
        
        service = ProviderOptInService(
            db=db,
            gmail_credentials_path=settings.GMAIL_CREDENTIALS_PATH,
            gmail_token_path=settings.GMAIL_TOKEN_PATH,
            gemini_api_key=settings.GEMINI_API_KEY
        )
        
        result = service.check_provider_response(provider_id, platform_email)
        
        if result.get("success"):
            return {"status": "success", "data": result}
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/providers/{provider_id}/process-consent")
async def process_provider_consent(
    provider_id: str,
    from_email: str = Query(..., description="Platform email for acknowledgment"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Process provider consent and enable/disable automation"""
    try:
        from app.settings import settings
        from app.services.provider_optin_service import ProviderOptInService
        
        service = ProviderOptInService(
            db=db,
            gmail_credentials_path=settings.GMAIL_CREDENTIALS_PATH,
            gmail_token_path=settings.GMAIL_TOKEN_PATH,
            gemini_api_key=settings.GEMINI_API_KEY
        )
        
        result = service.process_consent(provider_id, from_email)
        
        if result.get("success"):
            return {"status": "success", "data": result}
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/providers/{provider_id}/trigger-automation")
async def trigger_provider_automation(
    provider_id: str,
    platform_email: str = Query(..., description="Platform email for sending"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Manually trigger automated buyer outreach for a provider"""
    try:
        from app.settings import settings
        from app.services.provider_automation_service import ProviderAutomationService
        
        service = ProviderAutomationService(
            db=db,
            gmail_credentials_path=settings.GMAIL_CREDENTIALS_PATH,
            gmail_token_path=settings.GMAIL_TOKEN_PATH,
            gemini_api_key=settings.GEMINI_API_KEY
        )
        
        result = service.trigger_provider_automation(provider_id, platform_email)
        
        if result.get("success"):
            return {"status": "success", "data": result}
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/providers/{provider_id}/dashboard")
async def get_provider_dashboard(
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Get provider dashboard with automation status and metrics"""
    try:
        from app.models import ServiceProvider, Match
        from datetime import datetime, timedelta
        
        provider = db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Get match statistics
        matches = db.query(Match).filter(
            Match.provider_id == provider_id
        ).all()
        
        total_matches = len(matches)
        outreach_sent = len([m for m in matches if m.intro_sent_at])
        responses_received = len([m for m in matches if m.response_received])
        meetings_booked = len([m for m in matches if m.meeting_booked_at])
        
        # Get recent activity (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_matches = [m for m in matches if m.created_at and m.created_at >= seven_days_ago]
        recent_outreach = len([m for m in matches if m.intro_sent_at and m.intro_sent_at >= seven_days_ago])
        
        # Get automation status
        automation_status = {
            "enabled": provider.auto_outreach_enabled,
            "consent_status": provider.outreach_consent_status,
            "consent_date": provider.outreach_consent_date.isoformat() if provider.outreach_consent_date else None,
            "automation_settings": provider.automation_settings
        }
        
        dashboard = {
            "provider_id": provider_id,
            "company_name": provider.company_name,
            "automation_status": automation_status,
            "statistics": {
                "total_matches": total_matches,
                "outreach_sent": outreach_sent,
                "responses_received": responses_received,
                "meetings_booked": meetings_booked,
                "response_rate": round(responses_received / outreach_sent * 100, 1) if outreach_sent > 0 else 0,
                "recent_matches": len(recent_matches),
                "recent_outreach": recent_outreach
            },
            "recent_matches": [
                {
                    "match_id": m.match_id,
                    "buyer_id": m.buyer_id,
                    "status": m.status,
                    "intro_sent_at": m.intro_sent_at.isoformat() if m.intro_sent_at else None,
                    "followup_count": m.followup_count,
                    "response_received": m.response_received
                }
                for m in matches[-10:]  # Last 10 matches
            ]
        }
        
        return {"status": "success", "data": dashboard}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/providers/{provider_id}/pause-automation")
async def pause_provider_automation(
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Pause automated outreach for a provider"""
    try:
        from app.models import ServiceProvider
        
        provider = db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        provider.auto_outreach_enabled = False
        db.commit()
        
        return {"status": "success", "message": "Automation paused"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/providers/{provider_id}/resume-automation")
async def resume_provider_automation(
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Resume automated outreach for a provider"""
    try:
        from app.models import ServiceProvider
        
        provider = db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        if provider.outreach_consent_status != "consented":
            raise HTTPException(status_code=400, detail="Provider has not consented to automation")
        
        provider.auto_outreach_enabled = True
        db.commit()
        
        return {"status": "success", "message": "Automation resumed"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/providers/{provider_id}/subscribe")
async def subscribe_provider(
    provider_id: str,
    plan_type: str = Query(..., enum=["basic", "premium", "enterprise"]),
    db: Session = Depends(get_db)
):
    """Create subscription for a provider"""
    try:
        from app.services.provider_management import ProviderManagementService
        service = ProviderManagementService(db)
        
        subscription = service.create_subscription(provider_id, plan_type)
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Provider not found or invalid plan")
        
        return {
            "status": "success",
            "data": {
                "subscription_id": subscription.subscription_id,
                "plan_type": subscription.plan_type,
                "monthly_amount": subscription.monthly_amount / 100,
                "period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/providers/{provider_id}/usage")
async def get_provider_usage(provider_id: str, db: Session = Depends(get_db)):
    """Get provider's current usage and limits"""
    try:
        from app.services.provider_management import ProviderManagementService
        service = ProviderManagementService(db)
        
        usage = service.check_usage_limits(provider_id)
        
        return {"status": "success", "data": usage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/providers/{provider_id}/billing")
async def get_provider_billing(
    provider_id: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get provider's billing history"""
    try:
        from app.services.provider_management import ProviderManagementService
        service = ProviderManagementService(db)
        
        billing = service.get_provider_billing(provider_id, limit)
        
        return {"status": "success", "data": billing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Buyer Management Endpoints

class CreateBuyerRequest(BaseModel):
    company_name: str
    requirements: List[str]
    decision_maker_email: Optional[str] = None
    decision_maker_name: Optional[str] = None
    decision_maker_title: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    funding_stage: Optional[str] = None
    total_funding: Optional[str] = None
    budget_range: Optional[str] = None
    timeline: str = "exploring"
    signals: Optional[List[str]] = None
    verified: bool = False


@router.post("/platform/buyers")
async def create_buyer(
    request: CreateBuyerRequest,
    db: Session = Depends(get_db)
):
    """Create a new buyer company"""
    try:
        from app.services.buyer_management import BuyerManagementService
        service = BuyerManagementService(db)
        
        buyer = service.create_buyer(
            company_name=request.company_name,
            requirements=request.requirements,
            decision_maker_email=request.decision_maker_email,
            decision_maker_name=request.decision_maker_name,
            decision_maker_title=request.decision_maker_title,
            website=request.website,
            industry=request.industry,
            employee_count=request.employee_count,
            funding_stage=request.funding_stage,
            total_funding=request.total_funding,
            budget_range=request.budget_range,
            timeline=request.timeline,
            signals=request.signals,
            verified=request.verified
        )
        
        return {
            "status": "success",
            "data": {
                "buyer_id": buyer.buyer_id,
                "company_name": buyer.company_name,
                "requirements": buyer.requirements,
                "created_at": buyer.created_at.isoformat() if buyer.created_at else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/buyers")
async def list_buyers(
    active_only: bool = Query(True),
    verified_only: bool = Query(False),
    industry: str = Query(None),
    timeline: str = Query(None),
    search: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all buyer companies"""
    try:
        from app.services.buyer_management import BuyerManagementService
        service = BuyerManagementService(db)
        
        results = service.list_buyers(
            active_only=active_only,
            verified_only=verified_only,
            industry=industry,
            timeline=timeline,
            search=search,
            page=page,
            page_size=page_size
        )
        
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/buyers/{buyer_id}")
async def get_buyer(buyer_id: str, db: Session = Depends(get_db)):
    """Get buyer details with matches"""
    try:
        from app.services.buyer_management import BuyerManagementService
        service = BuyerManagementService(db)
        
        details = service.get_buyer_details(buyer_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Buyer not found")
        
        return {"status": "success", "data": details}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/buyers/{buyer_id}/verify")
async def verify_buyer(buyer_id: str, db: Session = Depends(get_db)):
    """Mark a buyer as verified"""
    try:
        from app.services.buyer_management import BuyerManagementService
        service = BuyerManagementService(db)
        
        buyer = service.verify_buyer(buyer_id)
        
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")
        
        return {
            "status": "success",
            "data": {
                "buyer_id": buyer.buyer_id,
                "company_name": buyer.company_name,
                "verified": buyer.verified
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/buyers/{buyer_id}/stats")
async def get_buyer_stats(buyer_id: str, db: Session = Depends(get_db)):
    """Get buyer statistics"""
    try:
        from app.services.buyer_management import BuyerManagementService
        service = BuyerManagementService(db)
        
        stats = service.get_buyer_stats(buyer_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Buyer not found")
        
        return {"status": "success", "data": stats}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/buyers/bulk-import")
async def bulk_import_buyers(
    buyers: List[Dict],
    auto_verify: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Bulk import buyers"""
    try:
        from app.services.buyer_management import BuyerManagementService
        service = BuyerManagementService(db)
        
        results = service.bulk_import_buyers(buyers, auto_verify)
        
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Matchmaking Engine Endpoints

@router.post("/platform/matches/calculate")
async def calculate_match(
    provider_id: str,
    buyer_id: str,
    db: Session = Depends(get_db)
):
    """Calculate match score between provider and buyer"""
    try:
        from app.services.matchmaking_engine import MatchmakingEngine
        from app.models import ServiceProvider, BuyerCompany
        
        engine = MatchmakingEngine(db)
        
        provider = db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        buyer = db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id == buyer_id
        ).first()
        
        if not provider or not buyer:
            raise HTTPException(status_code=404, detail="Provider or buyer not found")
        
        score, breakdown, reason = engine.calculate_match_score(provider, buyer)
        
        return {
            "status": "success",
            "data": {
                "provider_id": provider_id,
                "provider_name": provider.company_name,
                "buyer_id": buyer_id,
                "buyer_name": buyer.company_name,
                "match_score": score,
                "score_breakdown": breakdown,
                "match_reason": reason,
                "is_viable_match": score >= engine.MIN_MATCH_SCORE
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateMatchRequest(BaseModel):
    provider_id: str
    buyer_id: str
    auto_approve: bool = False


@router.post("/platform/matches")
async def create_match(
    request: CreateMatchRequest,
    db: Session = Depends(get_db)
):
    """Create a match between provider and buyer"""
    try:
        from app.services.matchmaking_engine import MatchmakingEngine
        engine = MatchmakingEngine(db)
        
        match = engine.create_match(request.provider_id, request.buyer_id, request.auto_approve)
        
        if not match:
            raise HTTPException(status_code=400, detail="Could not create match")
        
        return {
            "status": "success",
            "data": {
                "match_id": match.match_id,
                "provider_id": match.provider_id,
                "buyer_id": match.buyer_id,
                "match_score": match.match_score,
                "status": match.status,
                "provider_approved": match.provider_approved
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/matches/auto-create")
async def auto_create_matches(
    min_score: int = Query(70, ge=0, le=100),
    limit_per_buyer: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """Automatically create matches for all buyers"""
    try:
        from app.services.matchmaking_engine import MatchmakingEngine
        engine = MatchmakingEngine(db)
        
        results = engine.auto_match_all(min_score, limit_per_buyer)
        
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/matches/{match_id}")
async def get_match(match_id: str, db: Session = Depends(get_db)):
    """Get match details"""
    try:
        from app.services.matchmaking_engine import MatchmakingEngine
        engine = MatchmakingEngine(db)
        
        details = engine.get_match_details(match_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Match not found")
        
        return {"status": "success", "data": details}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/matches/{match_id}/approve")
async def approve_match(match_id: str, db: Session = Depends(get_db)):
    """Approve a pending match"""
    try:
        from app.services.matchmaking_engine import MatchmakingEngine
        engine = MatchmakingEngine(db)
        
        match = engine.approve_match(match_id)
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        
        return {
            "status": "success",
            "data": {
                "match_id": match.match_id,
                "status": match.status,
                "provider_approved": match.provider_approved
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/matches/{match_id}/reject")
async def reject_match(
    match_id: str,
    reason: str = None,
    db: Session = Depends(get_db)
):
    """Reject a match"""
    try:
        from app.services.matchmaking_engine import MatchmakingEngine
        engine = MatchmakingEngine(db)
        
        match = engine.reject_match(match_id, reason)
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        
        return {
            "status": "success",
            "data": {
                "match_id": match.match_id,
                "status": match.status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/providers/{provider_id}/matches")
async def get_provider_matches(
    provider_id: str,
    status: str = Query(None),
    db: Session = Depends(get_db)
):
    """Get all matches for a provider"""
    try:
        from app.models import Match
        
        query = db.query(Match).filter(Match.provider_id == provider_id)
        
        if status:
            query = query.filter(Match.status == status)
        
        matches = query.order_by(Match.match_score.desc()).all()
        
        return {
            "status": "success",
            "data": [
                {
                    "match_id": m.match_id,
                    "buyer_id": m.buyer_id,
                    "buyer_name": m.buyer.company_name if m.buyer else None,
                    "match_score": m.match_score,
                    "status": m.status,
                    "intro_sent": m.intro_sent_at is not None,
                    "meeting_booked": m.meeting_booked_at is not None
                }
                for m in matches
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/buyers/{buyer_id}/matches")
async def get_buyer_matches(
    buyer_id: str,
    status: str = Query(None),
    db: Session = Depends(get_db)
):
    """Get all matches for a buyer"""
    try:
        from app.models import Match
        
        query = db.query(Match).filter(Match.buyer_id == buyer_id)
        
        if status:
            query = query.filter(Match.status == status)
        
        matches = query.order_by(Match.match_score.desc()).all()
        
        return {
            "status": "success",
            "data": [
                {
                    "match_id": m.match_id,
                    "provider_id": m.provider_id,
                    "provider_name": m.provider.company_name if m.provider else None,
                    "match_score": m.match_score,
                    "status": m.status,
                    "services": m.provider.services if m.provider else []
                }
                for m in matches
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Intro Generation & Sending Endpoints

@router.post("/platform/matches/{match_id}/preview-intro")
async def preview_intro(match_id: str, db: Session = Depends(get_db)):
    """Preview the intro email for a match"""
    try:
        from app.services.intro_generator import IntroGenerator
        generator = IntroGenerator(db)
        
        preview = generator.preview_intro(match_id)
        
        if not preview:
            raise HTTPException(status_code=404, detail="Match not found")
        
        return {"status": "success", "data": preview}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/matches/{match_id}/send-intro")
async def send_intro(
    match_id: str,
    from_email: str = None,
    test_mode: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Send introduction email for a match"""
    try:
        from app.services.intro_generator import IntroGenerator
        generator = IntroGenerator(db)
        
        result = generator.send_intro(match_id, from_email, test_mode)
        
        if not result:
            raise HTTPException(status_code=404, detail="Match not found")
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/intros/send-batch")
async def send_batch_intros(
    provider_id: str = None,
    max_intros: int = Query(10, ge=1, le=50),
    from_email: str = None,
    db: Session = Depends(get_db)
):
    """Send intros for approved matches in batch"""
    try:
        from app.services.intro_generator import IntroGenerator
        generator = IntroGenerator(db)
        
        results = generator.send_batch_intros(provider_id, max_intros, from_email)
        
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Meeting & Deal Tracking Endpoints

@router.post("/platform/matches/{match_id}/book-meeting")
async def book_meeting(
    match_id: str,
    meeting_date: datetime,
    db: Session = Depends(get_db)
):
    """Record a booked meeting for a match"""
    try:
        from app.models import Match
        from app.services.provider_management import ProviderManagementService
        
        match = db.query(Match).filter(Match.match_id == match_id).first()
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        
        match.meeting_booked_at = datetime.utcnow()
        match.meeting_date = meeting_date
        match.meeting_status = "scheduled"
        match.status = "meeting_booked"
        
        # Increment provider meeting count
        provider_service = ProviderManagementService(db)
        provider_service.increment_meeting_booked(match.provider_id)
        
        # Record intro fee billing if applicable
        from app.services.platform_billing import PlatformBillingService
        billing_service = PlatformBillingService(db)
        billing_service.record_intro_fee(match_id)
        
        db.commit()
        
        return {
            "status": "success",
            "data": {
                "match_id": match_id,
                "meeting_date": meeting_date.isoformat(),
                "status": "meeting_booked"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/platform/matches/{match_id}/close-deal")
async def close_deal(
    match_id: str,
    deal_value: int,
    platform_percentage: float = Query(5.0, ge=0, le=50),
    db: Session = Depends(get_db)
):
    """Record a closed deal and charge success fee"""
    try:
        from app.models import Match
        from app.services.platform_billing import PlatformBillingService
        
        match = db.query(Match).filter(Match.match_id == match_id).first()
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        
        match.status = "closed_won"
        match.deal_value = deal_value
        match.deal_closed_at = datetime.utcnow()
        
        # Calculate and record success fee
        billing_service = PlatformBillingService(db)
        billing = billing_service.record_success_fee(
            match_id, deal_value, platform_percentage
        )
        
        db.commit()
        
        return {
            "status": "success",
            "data": {
                "match_id": match_id,
                "deal_value": deal_value / 100,
                "platform_fee": (deal_value * platform_percentage / 100) / 100 if billing else 0,
                "status": "closed_won"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Platform Revenue & Analytics Endpoints

@router.get("/platform/revenue/summary")
async def get_revenue_summary(
    period_type: str = Query("monthly", enum=["daily", "monthly"]),
    months: int = Query(12, ge=1, le=24),
    db: Session = Depends(get_db)
):
    """Get platform revenue summary"""
    try:
        from app.services.provider_management import ProviderManagementService
        service = ProviderManagementService(db)
        
        from datetime import datetime, timedelta
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30 * months)
        
        summaries = service.get_platform_revenue_summary(
            period_type=period_type,
            start_date=start_date,
            end_date=end_date
        )
        
        return {"status": "success", "data": summaries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/revenue/report")
async def get_revenue_report(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """Get comprehensive revenue report"""
    try:
        from app.services.platform_billing import PlatformBillingService
        service = PlatformBillingService(db)
        
        report = service.generate_revenue_report(start_date, end_date)
        
        return {"status": "success", "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/revenue/forecast")
async def get_revenue_forecast(
    months: int = Query(3, ge=1, le=12),
    db: Session = Depends(get_db)
):
    """Get revenue forecast based on current subscriptions"""
    try:
        from app.services.platform_billing import PlatformBillingService
        service = PlatformBillingService(db)
        
        forecast = service.get_revenue_forecast(months)
        
        return {"status": "success", "data": forecast}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/revenue/unit-economics")
async def get_unit_economics(db: Session = Depends(get_db)):
    """Get unit economics (LTV, CAC, etc.)"""
    try:
        from app.services.platform_billing import PlatformBillingService
        service = PlatformBillingService(db)
        
        economics = service.get_unit_economics()
        
        return {"status": "success", "data": economics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/analytics/dashboard")
async def get_platform_dashboard(db: Session = Depends(get_db)):
    """Get comprehensive platform dashboard"""
    try:
        from app.models import ServiceProvider, BuyerCompany, Match, ProviderSubscription
        from app.services.platform_billing import PlatformBillingService
        
        # Count totals
        total_providers = db.query(ServiceProvider).filter(
            ServiceProvider.active == True
        ).count()
        
        total_buyers = db.query(BuyerCompany).filter(
            BuyerCompany.active == True
        ).count()
        
        verified_buyers = db.query(BuyerCompany).filter(
            BuyerCompany.active == True,
            BuyerCompany.verified == True
        ).count()
        
        total_matches = db.query(Match).count()
        
        pending_matches = db.query(Match).filter(
            Match.status == "pending"
        ).count()
        
        approved_matches = db.query(Match).filter(
            Match.status == "approved"
        ).count()
        
        intro_sent = db.query(Match).filter(
            Match.status == "intro_sent"
        ).count()
        
        meetings_booked = db.query(Match).filter(
            Match.meeting_booked_at.isnot(None)
        ).count()
        
        deals_closed = db.query(Match).filter(
            Match.status == "closed_won"
        ).count()
        
        # Get MRR
        active_subs = db.query(ProviderSubscription).filter(
            ProviderSubscription.status == "active"
        ).all()
        
        mrr = sum(s.monthly_amount for s in active_subs) / 100
        
        # Get current month revenue
        from datetime import datetime
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        billing_service = PlatformBillingService(db)
        monthly_revenue = billing_service.calculate_monthly_revenue(now.year, now.month)
        
        return {
            "status": "success",
            "data": {
                "providers": {
                    "total_active": total_providers,
                    "with_active_subscription": len(active_subs)
                },
                "buyers": {
                    "total_active": total_buyers,
                    "verified": verified_buyers,
                    "verification_rate": round(verified_buyers / total_buyers * 100, 1) if total_buyers > 0 else 0
                },
                "matches": {
                    "total": total_matches,
                    "pending": pending_matches,
                    "approved": approved_matches,
                    "intro_sent": intro_sent,
                    "meetings_booked": meetings_booked,
                    "deals_closed": deals_closed,
                    "conversion_rate": round(meetings_booked / intro_sent * 100, 1) if intro_sent > 0 else 0
                },
                "revenue": {
                    "mrr": mrr,
                    "this_month": monthly_revenue
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Complete Platform Automation

@router.post("/platform/automation/run")
async def run_platform_automation(
    create_matches: bool = Query(True),
    send_intros: bool = Query(True),
    max_intros_per_provider: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Run complete platform automation cycle"""
    try:
        results = {
            "matches_created": 0,
            "intros_sent": 0,
            "errors": []
        }
        
        # Step 1: Auto-create matches
        if create_matches:
            from app.services.matchmaking_engine import MatchmakingEngine
            engine = MatchmakingEngine(db)
            match_results = engine.auto_match_all(min_score=70, limit_per_buyer=3)
            results["matches_created"] = match_results.get("matches_created", 0)
        
        # Step 2: Send intros for approved matches
        if send_intros:
            from app.services.intro_generator import IntroGenerator
            from app.models import Match, ServiceProvider
            
            generator = IntroGenerator(db)
            
            # Get all approved matches
            approved_matches = db.query(Match).filter(
                Match.status == "approved"
            ).all()
            
            # Group by provider to respect limits
            intros_by_provider = {}
            for match in approved_matches:
                if match.provider_id not in intros_by_provider:
                    intros_by_provider[match.provider_id] = []
                intros_by_provider[match.provider_id].append(match)
            
            # Send intros respecting limits
            for provider_id, matches in intros_by_provider.items():
                limited_matches = matches[:max_intros_per_provider]
                for match in limited_matches:
                    try:
                        result = generator.send_intro(match.match_id)
                        if result and "error" not in result:
                            results["intros_sent"] += 1
                    except Exception as e:
                        results["errors"].append(f"Match {match.match_id}: {str(e)}")
        
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# OUTBOUND-FIRST PROSPECT DISCOVERY ENDPOINTS
# ==========================================

class DiscoverProvidersRequest(BaseModel):
    tech_stack: List[str]
    industries: Optional[List[str]] = None
    min_stars: int = 50
    limit: int = 50


class DiscoverBuyersRequest(BaseModel):
    industries: List[str]
    funding_stage: Optional[str] = None
    employee_range: Optional[str] = None
    limit: int = 50


class EnrichLeadRequest(BaseModel):
    company_name: str
    website: Optional[str] = None
    description: Optional[str] = None
    repository: Optional[str] = None


class ScoreProspectsRequest(BaseModel):
    prospects: List[Dict]
    target_criteria: Optional[Dict] = None
    min_score: int = 60
    limit: int = 20


class SendOutreachRequest(BaseModel):
    prospect: Dict
    provider: Dict
    template_type: str = "intro"
    channel: str = "email"


@router.post("/outbound/discover/providers")
async def discover_providers(request: DiscoverProvidersRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Discover service providers by tech stack and industry"""
    try:
        service = ProspectDiscoveryService()
        providers = service.discover_providers(
            tech_stack=request.tech_stack,
            industries=request.industries,
            min_stars=request.min_stars,
            limit=request.limit
        )
        return {"status": "success", "data": {"count": len(providers), "providers": providers}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outbound/discover/buyers")
async def discover_buyers(request: DiscoverBuyersRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Discover buyer companies by industry and funding stage"""
    try:
        service = ProspectDiscoveryService()
        buyers = service.discover_buyers(
            industries=request.industries,
            funding_stage=request.funding_stage,
            employee_range=request.employee_range,
            limit=request.limit
        )
        return {"status": "success", "data": {"count": len(buyers), "buyers": buyers}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outbound/enrich/lead")
async def enrich_lead(request: EnrichLeadRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Enrich a single lead with all available data sources"""
    try:
        pipeline = LeadEnrichmentPipeline()
        enriched = pipeline.enrich_lead(request.dict())
        summary = pipeline.get_enrichment_summary(enriched)
        return {"status": "success", "data": {"lead": enriched, "summary": summary}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outbound/score/prospects")
async def score_prospects(request: ScoreProspectsRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Score and rank prospects"""
    try:
        service = ProspectScoringService()
        top = service.get_top_prospects(
            prospects=request.prospects,
            target_criteria=request.target_criteria,
            min_score=request.min_score,
            limit=request.limit
        )
        return {"status": "success", "data": {"count": len(top), "top_prospects": top}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outbound/outreach/send")
async def send_outreach(request: SendOutreachRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Send outreach to prospect"""
    try:
        # Initialize Gmail sender with database
        from app.services.gmail_sender import GmailSender
        try:
            gmail_sender = GmailSender(db)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gmail initialization failed: {str(e)}")
        
        service = OutboundOutreachService()
        service.gmail_sender = gmail_sender
        result = service.send_outreach(
            prospect=request.prospect,
            provider=request.provider,
            template_type=request.template_type,
            channel=request.channel
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# TRANSACTIONAL BILLING ENDPOINTS
# ==========================================

class RecordIntroFeeRequest(BaseModel):
    prospect_id: str
    provider_id: str
    outreach_id: Optional[str] = None


class RecordMeetingFeeRequest(BaseModel):
    prospect_id: str
    provider_id: str
    outreach_id: Optional[str] = None


class RecordSuccessFeeRequest(BaseModel):
    prospect_id: str
    provider_id: str
    deal_value_cents: int
    percentage: Optional[float] = None


@router.post("/billing/record/intro-fee")
async def record_intro_fee(request: RecordIntroFeeRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_admin_user)):
    """Record fee for sending a qualified intro"""
    try:
        service = TransactionalBillingService()
        billing = service.record_intro_fee(
            prospect_id=request.prospect_id,
            provider_id=request.provider_id,
            outreach_id=request.outreach_id
        )
        return {"status": "success", "data": {"billing_id": billing.billing_id, "amount_usd": billing.amount / 100}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/billing/record/meeting-fee")
async def record_meeting_fee(request: RecordMeetingFeeRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_admin_user)):
    """Record fee for booking a meeting"""
    try:
        service = TransactionalBillingService()
        billing = service.record_meeting_fee(
            prospect_id=request.prospect_id,
            provider_id=request.provider_id,
            outreach_id=request.outreach_id
        )
        return {"status": "success", "data": {"billing_id": billing.billing_id, "amount_usd": billing.amount / 100}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/billing/record/success-fee")
async def record_success_fee(request: RecordSuccessFeeRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_admin_user)):
    """Record success fee on closed deal"""
    try:
        service = TransactionalBillingService()
        billing = service.record_success_fee(
            prospect_id=request.prospect_id,
            provider_id=request.provider_id,
            deal_value_cents=request.deal_value_cents,
            percentage=request.percentage
        )
        return {"status": "success", "data": {"billing_id": billing.billing_id, "amount_usd": billing.amount / 100}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/billing/provider/{provider_id}/balance")
async def get_provider_balance(provider_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get outstanding balance for a provider"""
    try:
        service = TransactionalBillingService()
        balance = service.get_provider_outstanding_balance(provider_id)
        return {"status": "success", "data": balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# B2B Matchmaking Platform Endpoints
# ============================================================================

# B2B Provider Discovery Endpoints

@router.post("/b2b/providers/discovery/run")
async def run_b2b_provider_discovery(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Manually trigger autonomous B2B provider discovery
    
    Discovers service providers from free sources:
    - Clutch.co (service directories)
    - G2 (software providers)
    - GoodFirms (B2B services)
    - GitHub (tech companies)
    - Google Search (general discovery)
    
    Auto-enriches with Gemini AI and sends opt-in emails
    """
    try:
        from app.settings import settings
        service = B2BProviderDiscoveryService(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY,
            platform_email=getattr(settings, 'PLATFORM_EMAIL', 'platform@example.com'),
            dry_run=False
        )
        
        import asyncio
        results = await service.run_provider_discovery()
        
        return {
            "status": "success",
            "message": "B2B provider discovery completed",
            "data": {
                "discovered": results["discovered"],
                "created": results["created"],
                "optin_sent": results["optin_sent"],
                "sources": results["sources"],
                "providers": results["providers"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/b2b/providers/discovery/run/async")
async def run_b2b_provider_discovery_async(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Trigger B2B provider discovery asynchronously via Celery
    
    Runs in background and discovers/enriches providers + sends opt-in emails
    """
    task = run_b2b_provider_discovery_task.delay()
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "B2B provider discovery started in background. Providers will be discovered and opt-in emails sent automatically."
    }


@router.get("/b2b/providers/discovery/stats")
async def get_b2b_provider_discovery_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get B2B provider discovery statistics"""
    try:
        from app.settings import settings
        service = B2BProviderDiscoveryService(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY,
            platform_email=getattr(settings, 'PLATFORM_EMAIL', 'platform@example.com'),
            dry_run=True  # Just for stats
        )
        
        stats = service.get_discovery_stats()
        return {"status": "success", "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# B2B Buyer Discovery Endpoints

@router.post("/b2b/discovery/run")
async def run_b2b_buyer_discovery(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Manually trigger autonomous B2B buyer discovery
    
    Discovers buyers from free sources (GitHub, NewsAPI, Hacker News, Product Hunt, Job Boards)
    Enriches with Gemini AI
    Auto-matches to providers
    """
    try:
        from app.settings import settings
        service = B2BBuyerDiscoveryService(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY,
            newsapi_key=getattr(settings, 'NEWSAPI_KEY', None)
        )
        
        import asyncio
        results = await service.run_buyer_discovery()
        
        return {
            "status": "success",
            "message": "B2B buyer discovery completed",
            "data": {
                "discovered": results["discovered"],
                "created": results["created"],
                "matched": results["matched"],
                "buyers": results["buyers"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/b2b/discovery/run/async")
async def run_b2b_buyer_discovery_async(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Trigger B2B buyer discovery asynchronously via Celery
    
    Runs in background and discovers/enriches/matches buyers automatically
    """
    task = run_b2b_buyer_discovery_task.delay()
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "B2B buyer discovery started in background"
    }


@router.get("/b2b/discovery/stats")
async def get_b2b_discovery_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get B2B buyer discovery statistics"""
    try:
        from app.settings import settings
        service = B2BBuyerDiscoveryService(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY,
            newsapi_key=getattr(settings, 'NEWSAPI_KEY', None)
        )
        
        stats = service.get_discovery_stats()
        return {"status": "success", "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# B2B Response Tracking Endpoints

@router.post("/b2b/responses/check")
async def check_b2b_buyer_responses(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Check for buyer responses to B2B outreach
    
    Monitors Gmail for replies and classifies them using AI
    """
    try:
        from app.settings import settings
        service = B2BResponseTrackingService(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY
        )
        
        results = service.check_all_pending_responses()
        return {
            "status": "success",
            "data": {
                "checked": results["checked"],
                "responses_found": results["responses_found"],
                "processed": results["processed"],
                "errors": results["errors"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/b2b/responses/check/async")
async def check_b2b_buyer_responses_async(
    current_user: dict = Depends(get_current_admin_user)
):
    """Trigger buyer response checking asynchronously via Celery"""
    task = check_buyer_responses_task.delay()
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Buyer response checking started in background"
    }


@router.get("/b2b/responses/stats")
async def get_b2b_response_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get B2B response tracking statistics"""
    try:
        from app.settings import settings
        service = B2BResponseTrackingService(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY
        )
        
        stats = service.get_response_stats()
        return {"status": "success", "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# B2B Follow-up Endpoints

@router.post("/b2b/followups/run")
async def run_b2b_followups(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Run B2B follow-up sequences
    
    Sends Day 3, 7, 14 follow-ups to buyers who haven't responded
    """
    try:
        service = B2BFollowupService(db)
        results = service.process_all_followups()
        
        return {
            "status": "success",
            "data": {
                "followups_sent": results["sent"],
                "skipped": results["skipped"],
                "errors": results["errors"],
                "details": results["details"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/b2b/followups/run/async")
async def run_b2b_followups_async(
    current_user: dict = Depends(get_current_admin_user)
):
    """Trigger follow-up sequences asynchronously via Celery"""
    task = run_b2b_followups_task.delay()
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "B2B follow-ups started in background"
    }


@router.get("/b2b/followups/stats")
async def get_b2b_followup_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get B2B follow-up statistics"""
    try:
        service = B2BFollowupService(db)
        stats = service.get_followup_stats()
        return {"status": "success", "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# B2B Provider Dashboard Endpoints

@router.get("/b2b/providers/{provider_id}/dashboard")
async def get_provider_dashboard(
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get complete provider dashboard
    
    Returns: overview, automation status, matches, outreach, analytics, settings
    """
    try:
        service = B2BProviderDashboardService(db)
        dashboard = service.get_dashboard(provider_id)
        
        if not dashboard:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return {"status": "success", "data": dashboard}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/b2b/providers/{provider_id}/automation/pause")
async def pause_provider_automation(
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Pause provider automation"""
    try:
        service = B2BProviderDashboardService(db)
        result = service.pause_automation(provider_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return {"status": "success", "message": "Automation paused"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/b2b/providers/{provider_id}/automation/resume")
async def resume_provider_automation(
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Resume provider automation"""
    try:
        service = B2BProviderDashboardService(db)
        result = service.resume_automation(provider_id)
        
        if not result:
            raise HTTPException(status_code=400, detail="Cannot resume automation - check consent status")
        
        return {"status": "success", "message": "Automation resumed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/b2b/providers/{provider_id}/matches/{match_id}")
async def get_match_details(
    provider_id: str,
    match_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific match"""
    try:
        service = B2BProviderDashboardService(db)
        details = service.get_match_details(provider_id, match_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Match not found")
        
        return {"status": "success", "data": details}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/b2b/providers/{provider_id}/settings")
async def update_provider_settings(
    provider_id: str,
    settings: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update provider automation settings"""
    try:
        service = B2BProviderDashboardService(db)
        result = service.update_settings(provider_id, settings)
        
        if not result:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return {"status": "success", "message": "Settings updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/b2b/providers/{provider_id}/export")
async def export_provider_data(
    provider_id: str,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Export provider data (matches, outreach, etc.)"""
    try:
        service = B2BProviderDashboardService(db)
        data = service.export_data(provider_id, format)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# B2B Analytics Dashboard Endpoints

@router.get("/b2b/analytics/dashboard")
async def get_b2b_analytics_dashboard(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Get full B2B platform analytics dashboard
    
    Returns: overview, provider analytics, buyer analytics, outreach analytics, revenue, trends
    """
    try:
        service = B2BAnalyticsDashboardService(db)
        dashboard = service.get_full_dashboard()
        return {"status": "success", "data": dashboard}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/b2b/analytics/overview")
async def get_b2b_overview(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get B2B platform overview metrics"""
    try:
        service = B2BAnalyticsDashboardService(db)
        overview = service._get_overview_metrics()
        return {"status": "success", "data": overview}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/b2b/analytics/providers")
async def get_b2b_provider_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get provider performance analytics"""
    try:
        service = B2BAnalyticsDashboardService(db)
        analytics = service._get_provider_analytics()
        return {"status": "success", "data": analytics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/b2b/analytics/buyers")
async def get_b2b_buyer_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get buyer engagement analytics"""
    try:
        service = B2BAnalyticsDashboardService(db)
        analytics = service._get_buyer_analytics()
        return {"status": "success", "data": analytics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/b2b/analytics/outreach")
async def get_b2b_outreach_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get outreach performance analytics"""
    try:
        service = B2BAnalyticsDashboardService(db)
        analytics = service._get_outreach_analytics()
        return {"status": "success", "data": analytics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/b2b/analytics/revenue")
async def get_b2b_revenue_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Get revenue analytics (admin only)"""
    try:
        service = B2BAnalyticsDashboardService(db)
        analytics = service._get_revenue_analytics()
        return {"status": "success", "data": analytics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/b2b/analytics/funnel")
async def get_b2b_conversion_funnel(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get B2B conversion funnel analytics"""
    try:
        service = B2BAnalyticsDashboardService(db)
        funnel = service._get_conversion_funnel()
        return {"status": "success", "data": funnel}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/b2b/analytics/top-performers")
async def get_b2b_top_performers(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get top performing providers"""
    try:
        service = B2BAnalyticsDashboardService(db)
        performers = service._get_top_performers()
        return {"status": "success", "data": performers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/b2b/analytics/compare")
async def compare_providers(
    request: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Compare multiple providers"""
    try:
        provider_ids = request.get("provider_ids", [])
        if not provider_ids:
            raise HTTPException(status_code=400, detail="provider_ids required")
        
        service = B2BAnalyticsDashboardService(db)
        comparison = service.get_provider_comparison(provider_ids)
        return {"status": "success", "data": comparison}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/b2b/analytics/export")
async def export_b2b_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """Export full B2B analytics report"""
    try:
        service = B2BAnalyticsDashboardService(db)
        report = service.export_analytics_report()
        return {"status": "success", "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# B2B System Health & Status
# ============================================================================

@router.get("/b2b/health")
async def b2b_health_check(db: Session = Depends(get_db)):
    """Check B2B platform health status"""
    try:
        # Check database connectivity
        total_providers = db.query(ServiceProvider).count()
        total_buyers = db.query(BuyerCompany).count()
        total_matches = db.query(Match).count()
        
        return {
            "status": "healthy",
            "data": {
                "providers": total_providers,
                "buyers": total_buyers,
                "matches": total_matches,
                "database": "connected"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"B2B platform unhealthy: {str(e)}")
