"""Tests for services"""
import pytest
from datetime import datetime
from app.services.lead_qualification import LeadQualificationEngine
from app.services.offer_matching import OfferMatchingEngine
from app.services.pipeline_state_machine import PipelineStateMachine
from app.models import Lead, PipelineState


def test_lead_qualification_engine(db_session, sample_lead):
    """Test lead qualification engine"""
    # Create lead in database
    lead = Lead(**sample_lead)
    db_session.add(lead)
    db_session.commit()
    
    engine = LeadQualificationEngine(db_session)
    result = engine.score_lead(lead)
    
    assert result is not None
    assert "lead_id" in result
    assert "priority_score" in result
    assert "is_qualified" in result
    assert "dimension_scores" in result
    
    # Should be qualified based on high fit score and signal
    assert result["is_qualified"] == True


def test_offer_matching_engine(db_session, sample_lead):
    """Test offer matching engine"""
    lead = Lead(**sample_lead)
    db_session.add(lead)
    db_session.commit()
    
    engine = OfferMatchingEngine(db_session)
    result = engine.match_offer(lead)
    
    assert result is not None
    assert "lead_id" in result
    assert "matched_strategy" in result
    assert "offer_angle" in result
    assert "message_style" in result
    assert "cta_type" in result


def test_pipeline_state_machine(db_session, sample_lead):
    """Test pipeline state machine"""
    lead = Lead(**sample_lead)
    db_session.add(lead)
    db_session.commit()
    
    pipeline = PipelineStateMachine(db_session)
    
    # Get initial state
    state = pipeline.get_state(lead.lead_id)
    assert state["current_state"] == "NEW"
    
    # Transition to qualified
    result = pipeline.transition(lead.lead_id, "QUALIFIED")
    assert result["success"] == True
    assert result["new_state"] == "QUALIFIED"
    
    # Verify transition
    state = pipeline.get_state(lead.lead_id)
    assert state["current_state"] == "QUALIFIED"
    assert state["previous_state"] == "NEW"


def test_pipeline_invalid_transition(db_session, sample_lead):
    """Test invalid pipeline transition"""
    lead = Lead(**sample_lead)
    db_session.add(lead)
    db_session.commit()
    
    pipeline = PipelineStateMachine(db_session)
    
    # Try invalid transition (NEW -> INTERESTED directly)
    result = pipeline.transition(lead.lead_id, "INTERESTED")
    assert result["success"] == False
    assert "error" in result


def test_crm_deal_creation(db_session, sample_lead):
    """Test CRM deal creation"""
    from app.services.crm import CRMLayer
    
    lead = Lead(**sample_lead)
    db_session.add(lead)
    db_session.commit()
    
    crm = CRMLayer(db_session)
    deal = crm.create_deal(
        lead_id=lead.lead_id,
        deal_name="Test Deal",
        deal_value=25000.0,
        deal_stage="prospecting"
    )
    
    assert deal is not None
    assert "deal_id" in deal
    assert deal["deal_value"] == 25000.0


def test_conversation_memory(db_session, sample_lead):
    """Test conversation memory"""
    from app.services.conversation_memory import ConversationMemoryLayer
    
    lead = Lead(**sample_lead)
    db_session.add(lead)
    db_session.commit()
    
    memory = ConversationMemoryLayer(db_session)
    
    # Record email sent
    memory.record_email_sent("msg-001", lead.lead_id, "Test Subject", "Test Body")
    
    # Get context
    context = memory.get_conversation_context(lead.lead_id)
    assert context is not None
    assert context["emails_sent"] == 1


def test_human_escalation(db_session, sample_lead):
    """Test human escalation"""
    from app.services.human_escalation import HumanEscalationLayer
    
    lead = Lead(**sample_lead)
    db_session.add(lead)
    db_session.commit()
    
    escalation = HumanEscalationLayer(db_session)
    
    # Check for escalation
    result = escalation.evaluate_for_escalation(lead.lead_id)
    
    assert result is not None
    assert "escalate" in result


def test_feedback_learning(db_session):
    """Test feedback learning"""
    from app.services.feedback_learning import FeedbackLearningLoop
    
    learning = FeedbackLearningLoop(db_session)
    
    # Get performance report (should work even with empty database)
    report = learning.get_performance_report()
    
    assert report is not None
    assert "overall_reply_rate" in report
    assert "total_sent" in report


def test_deliverability_system(db_session):
    """Test deliverability system"""
    from app.services.deliverability import DeliverabilitySystem
    
    deliverability = DeliverabilitySystem(db_session)
    
    # Check can_send for new domain
    result = deliverability.can_send("test@example.com")
    
    assert result is not None
    assert "can_send" in result
    assert isinstance(result["can_send"], bool)


def test_experimentation_layer(db_session):
    """Test experimentation layer"""
    from app.services.experimentation import ExperimentationLayer
    
    exp = ExperimentationLayer(db_session)
    
    # Create experiment
    result = exp.create_experiment(
        name="Test Subject Experiment",
        experiment_type="subject",
        variants={"A": "Subject A", "B": "Subject B"}
    )
    
    assert result is not None
    assert "experiment_id" in result
    assert result["status"] == "active"
