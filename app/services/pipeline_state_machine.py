import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models import Lead, PipelineState
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class PipelineStateMachine:
    """Full state flow: NEW → QUALIFIED → CONTACTED → REPLIED → INTERESTED → CALL_BOOKED → CLOSED → LOST → SUPPRESSED"""
    
    VALID_STATES = [
        "NEW",
        "QUALIFIED",
        "CONTACTED",
        "REPLIED",
        "INTERESTED",
        "CALL_BOOKED",
        "CLOSED",
        "LOST",
        "SUPPRESSED"
    ]
    
    VALID_TRANSITIONS = {
        "NEW": ["QUALIFIED", "SUPPRESSED", "LOST"],
        "QUALIFIED": ["CONTACTED", "SUPPRESSED", "LOST"],
        "CONTACTED": ["REPLIED", "SUPPRESSED", "LOST"],
        "REPLIED": ["INTERESTED", "SUPPRESSED", "LOST"],
        "INTERESTED": ["CALL_BOOKED", "SUPPRESSED", "LOST"],
        "CALL_BOOKED": ["CLOSED", "LOST"],
        "CLOSED": [],  # Terminal state
        "LOST": [],  # Terminal state
        "SUPPRESSED": []  # Terminal state
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_state(self, lead_id: str) -> Dict:
        """Get current pipeline state for a lead"""
        state = self.db.query(PipelineState).filter(
            PipelineState.lead_id == lead_id
        ).first()
        
        if not state:
            # Initialize to NEW
            state = self._initialize_state(lead_id)
        
        return {
            "lead_id": lead_id,
            "current_state": state.current_state,
            "previous_state": state.previous_state,
            "entered_current_state_at": state.entered_current_state_at.isoformat() if state.entered_current_state_at else None,
            "time_in_state_seconds": state.time_in_state_seconds,
            "total_pipeline_days": state.total_pipeline_days,
            "state_history": state.state_history or [],
            "stage_data": state.stage_data
        }
    
    def transition(self, lead_id: str, new_state: str, stage_data: Dict = None) -> Dict:
        """Transition a lead to a new pipeline state"""
        if new_state not in self.VALID_STATES:
            raise ValueError(f"Invalid state: {new_state}")
        
        current_state_obj = self.db.query(PipelineState).filter(
            PipelineState.lead_id == lead_id
        ).first()
        
        if not current_state_obj:
            current_state_obj = self._initialize_state(lead_id)
        
        current_state = current_state_obj.current_state
        
        # Validate transition
        if new_state not in self.VALID_TRANSITIONS.get(current_state, []):
            logger.warning(f"Invalid transition from {current_state} to {new_state}")
            return {
                "success": False,
                "error": f"Invalid transition from {current_state} to {new_state}",
                "valid_transitions": self.VALID_TRANSITIONS.get(current_state, [])
            }
        
        # Calculate time in current state
        if current_state_obj.entered_current_state_at:
            time_in_state = (datetime.utcnow() - current_state_obj.entered_current_state_at).total_seconds()
        else:
            time_in_state = 0
        
        # Update state history
        state_history = current_state_obj.state_history or []
        state_history.append({
            "from": current_state,
            "to": new_state,
            "at": datetime.utcnow().isoformat(),
            "time_in_previous_state": time_in_state
        })
        
        # Update state
        previous_state = current_state_obj.current_state
        current_state_obj.previous_state = previous_state
        current_state_obj.current_state = new_state
        current_state_obj.entered_current_state_at = datetime.utcnow()
        current_state_obj.time_in_state_seconds = 0
        current_state_obj.total_pipeline_days = (datetime.utcnow() - current_state_obj.created_at).days
        current_state_obj.state_history = state_history
        current_state_obj.stage_data = stage_data or {}
        
        self.db.commit()
        
        # Update lead status to match pipeline state
        lead = self.db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if lead:
            lead.status = new_state.lower()
            self.db.commit()
        
        logger.info(f"Transitioned lead {lead_id} from {previous_state} to {new_state}")
        
        return {
            "success": True,
            "lead_id": lead_id,
            "previous_state": previous_state,
            "new_state": new_state,
            "time_in_previous_state": time_in_state,
            "total_pipeline_days": current_state_obj.total_pipeline_days
        }
    
    def _initialize_state(self, lead_id: str) -> PipelineState:
        """Initialize a lead to NEW state"""
        state = PipelineState(
            state_id=f"state-{str(uuid.uuid4())[:8]}",
            lead_id=lead_id,
            current_state="NEW",
            previous_state=None,
            entered_current_state_at=datetime.utcnow(),
            time_in_state_seconds=0,
            total_pipeline_days=0,
            state_history=[],
            stage_data={}
        )
        self.db.add(state)
        self.db.commit()
        return state
    
    def auto_transition_on_email_sent(self, lead_id: str):
        """Auto-transition when email is sent"""
        current = self.get_state(lead_id)
        
        if current["current_state"] == "NEW":
            return self.transition(lead_id, "QUALIFIED", {"reason": "email_sent"})
        elif current["current_state"] == "QUALIFIED":
            return self.transition(lead_id, "CONTACTED", {"reason": "email_sent"})
        
        return {"success": True, "message": "No auto-transition needed"}
    
    def auto_transition_on_reply(self, lead_id: str, classification: str):
        """Auto-transition based on reply classification"""
        current = self.get_state(lead_id)
        
        if classification == "interested":
            if current["current_state"] in ["CONTACTED", "REPLIED"]:
                return self.transition(lead_id, "INTERESTED", {"reason": f"reply_{classification}"})
            elif current["current_state"] == "INTERESTED":
                return {"success": True, "message": "Already in INTERESTED state"}
        elif classification in ["not_interested", "unsubscribe"]:
            return self.transition(lead_id, "LOST" if classification == "not_interested" else "SUPPRESSED", 
                                {"reason": f"reply_{classification}"})
        elif classification == "not_now":
            # Stay in current state but note the response
            return {"success": True, "message": "Lead not now - staying in current state"}
        
        return {"success": True, "message": "No state change needed"}
    
    def auto_transition_on_call_booked(self, lead_id: str):
        """Auto-transition when call is booked"""
        current = self.get_state(lead_id)
        
        if current["current_state"] == "INTERESTED":
            return self.transition(lead_id, "CALL_BOOKED", {"reason": "call_booked"})
        
        return {"success": True, "message": "Not in INTERESTED state"}
    
    def auto_transition_on_deal_closed(self, lead_id: str, won: bool):
        """Auto-transition when deal is closed"""
        if won:
            return self.transition(lead_id, "CLOSED", {"reason": "deal_won"})
        else:
            return self.transition(lead_id, "LOST", {"reason": "deal_lost"})
    
    def get_pipeline_velocity(self, days: int = 30) -> Dict:
        """Get pipeline velocity metrics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        states = self.db.query(PipelineState).filter(
            PipelineState.created_at >= cutoff_date
        ).all()
        
        velocity_by_state = {}
        for state_name in self.VALID_STATES:
            velocity_by_state[state_name] = 0
        
        total_leads = len(states)
        moved_forward = 0
        
        for state in states:
            velocity_by_state[state.current_state] += 1
            if state.state_history and len(state.state_history) > 1:
                moved_forward += 1
        
        return {
            "period_days": days,
            "total_leads": total_leads,
            "leads_moved_forward": moved_forward,
            "pipeline_velocity": round((moved_forward / total_leads * 100) if total_leads > 0 else 0, 2),
            "distribution_by_state": velocity_by_state
        }
    
    def get_stuck_leads(self, state: str, days: int = 7) -> list:
        """Get leads stuck in a state for too long"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stuck_leads = self.db.query(PipelineState).filter(
            PipelineState.current_state == state,
            PipelineState.entered_current_state_at < cutoff_date
        ).all()
        
        return [
            {
                "lead_id": lead.lead_id,
                "state": lead.current_state,
                "days_in_state": (datetime.utcnow() - lead.entered_current_state_at).days
            }
            for lead in stuck_leads
        ]
    
    def get_conversion_funnel(self) -> Dict:
        """Get conversion funnel by state"""
        funnel = {}
        
        for state_name in self.VALID_STATES:
            count = self.db.query(PipelineState).filter(
                PipelineState.current_state == state_name
            ).count()
            funnel[state_name] = count
        
        # Calculate conversion rates
        total_new = funnel.get("NEW", 0)
        conversion_rates = {}
        
        for state_name in self.VALID_STATES:
            if total_new > 0:
                conversion_rates[state_name] = round((funnel[state_name] / total_new) * 100, 2)
            else:
                conversion_rates[state_name] = 0
        
        return {
            "counts": funnel,
            "conversion_rates": conversion_rates,
            "total_leads": sum(funnel.values())
        }
