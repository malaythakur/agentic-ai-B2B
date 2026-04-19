"""Template Service for AI-personalized message generation"""
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
import json
import re

from app.models import Template, Lead, OutboundMessage
from app.logging_config import logger as app_logger

logger = app_logger


class TemplateService:
    """Service for template management, matching, and AI personalization"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_template(
        self,
        name: str,
        category: str,
        subject_template: str,
        body_template: str,
        signal_keywords: List[str] = None,
        description: str = None,
        is_default: bool = False,
        variant_of: str = None
    ) -> Template:
        """Create a new message template"""
        
        if is_default:
            self._unset_category_defaults(category)
        
        template = Template(
            template_id=f"template-{str(uuid.uuid4())[:8]}",
            name=name,
            category=category,
            description=description,
            subject_template=subject_template,
            body_template=body_template,
            signal_keywords=signal_keywords or [],
            is_default=is_default,
            variant_of=variant_of,
            is_active=True,
            usage_count=0,
            reply_count=0,
            positive_reply_count=0,
            reply_rate=0,
            performance_score=50,
            version=1
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        logger.info(f"Created template {template.template_id}: {name}")
        return template
    
    def get_template(self, template_id: str) -> Optional[Template]:
        """Get template by ID"""
        return self.db.query(Template).filter(
            Template.template_id == template_id,
            Template.is_active == True
        ).first()
    
    def list_templates(
        self,
        category: str = None,
        is_active: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[Template]:
        """List templates with filters"""
        query = self.db.query(Template)
        
        if category:
            query = query.filter(Template.category == category)
        if is_active is not None:
            query = query.filter(Template.is_active == is_active)
        
        return query.order_by(Template.performance_score.desc()).offset(offset).limit(limit).all()
    
    def update_template(self, template_id: str, **updates) -> Optional[Template]:
        """Update a template"""
        template = self.get_template(template_id)
        if not template:
            return None
        
        if updates.get('is_default') and not template.is_default:
            self._unset_category_defaults(template.category)
        
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        if any(f in updates for f in ['subject_template', 'body_template', 'signal_keywords']):
            template.version += 1
        
        self.db.commit()
        self.db.refresh(template)
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """Soft delete a template"""
        template = self.get_template(template_id)
        if not template:
            return False
        
        template.is_active = False
        self.db.commit()
        return True
    
    def _unset_category_defaults(self, category: str):
        """Unset default flag for all templates in category"""
        self.db.query(Template).filter(
            Template.category == category,
            Template.is_default == True
        ).update({"is_default": False})
        self.db.commit()
    
    def match_template_to_lead(self, lead: Lead) -> Tuple[Optional[Template], float]:
        """Match best template to lead based on signal keywords"""
        signal = lead.signal.lower() if lead.signal else ""
        
        templates = self.db.query(Template).filter(
            Template.is_active == True
        ).all()
        
        if not templates:
            return None, 0.0
        
        best_template = None
        best_score = 0
        
        for template in templates:
            score = self._calculate_match_score(signal, template)
            if score > best_score:
                best_score = score
                best_template = template
        
        if best_score < 0.3:
            default_template = self._get_default_template()
            if default_template:
                return default_template, 0.5
        
        return best_template, best_score
    
    def _calculate_match_score(self, signal: str, template: Template) -> float:
        """Calculate how well a template matches a signal"""
        if not template.signal_keywords:
            return 0.1
        
        matches = sum(1 for keyword in template.signal_keywords if keyword.lower() in signal)
        keyword_score = matches / max(len(template.signal_keywords), 1)
        performance_bonus = template.performance_score / 200
        
        return keyword_score + performance_bonus
    
    def _get_default_template(self) -> Optional[Template]:
        """Get the default template"""
        default = self.db.query(Template).filter(
            Template.is_default == True,
            Template.is_active == True
        ).first()
        
        if default:
            return default
        
        return self.db.query(Template).filter(
            Template.is_active == True
        ).order_by(Template.performance_score.desc()).first()
    
    def personalize_message(
        self,
        lead: Lead,
        template: Template,
        offer_angle: str = None
    ) -> Dict[str, str]:
        """Personalize a template for a specific lead"""
        
        if lead.message_intent and lead.message_intent.strip():
            return {
                "subject": self._extract_subject_from_message(lead.message_intent),
                "body": lead.message_intent,
                "template_id": None,
                "personalization_method": "custom"
            }
        
        if not template:
            return self._generate_pure_ai(lead, offer_angle)
        
        subject = self._personalize_subject(template.subject_template, lead)
        body = self._personalize_body(template.body_template, lead, offer_angle)
        
        return {
            "subject": subject,
            "body": body,
            "template_id": template.template_id,
            "personalization_method": "template_ai"
        }
    
    def _personalize_subject(self, template_subject: str, lead: Lead) -> str:
        """Personalize subject line with lead data"""
        subject = template_subject
        replacements = {
            "{{company}}": lead.company,
            "{{decision_maker}}": lead.decision_maker or "there",
            "{{signal}}": lead.signal[:50] + "..." if len(lead.signal) > 50 else lead.signal,
        }
        
        for placeholder, value in replacements.items():
            if value:
                subject = subject.replace(placeholder, value)
        
        return subject
    
    def _personalize_body(self, template_body: str, lead: Lead, offer_angle: str = None) -> str:
        """Personalize email body with lead data"""
        body = template_body
        replacements = {
            "{{company}}": lead.company,
            "{{decision_maker}}": lead.decision_maker or "there",
            "{{website}}": lead.website or "your site",
            "{{signal}}": lead.signal,
            "{{pain_point}}": lead.pain_point or "growing efficiently",
            "{{urgency_reason}}": lead.urgency_reason or "",
            "{{custom_hook}}": lead.custom_hook or "",
            "{{offer_angle}}": offer_angle or "",
        }
        
        for placeholder, value in replacements.items():
            if value:
                body = body.replace(placeholder, value)
        
        return body
    
    def _extract_subject_from_message(self, message: str) -> str:
        """Extract or generate subject from custom message"""
        lines = message.strip().split('\n')
        if len(lines) > 0 and len(lines[0]) < 100 and lines[0]:
            return lines[0]
        return "Quick question"
    
    def _generate_pure_ai(self, lead: Lead, offer_angle: str = None) -> Dict[str, str]:
        """Generate message purely with AI (fallback)"""
        return {
            "subject": f"Quick question about {lead.company}",
            "body": lead.message or f"Hi {lead.decision_maker or 'there'},\n\nI noticed {lead.signal}. Would love to chat.",
            "template_id": None,
            "personalization_method": "ai_generated"
        }
    
    def seed_default_templates(self):
        """Seed database with default templates if none exist"""
        existing = self.db.query(Template).first()
        if existing:
            return
        
        defaults = [
            {
                "name": "Funding Announcement",
                "category": "funding",
                "subject_template": "Congrats on the {{company}} raise, {{decision_maker}}",
                "body_template": """Hi {{decision_maker}},

Congrats on {{company}}'s recent funding. {{signal}}

{{pain_point}} is a common challenge post-funding. {{custom_hook}}

Worth a brief conversation?

Best,""",
                "signal_keywords": ["funding", "raised", "Series A", "Series B", "investment", "million"],
                "is_default": True
            },
            {
                "name": "Hiring Signal - SDR/BDR",
                "category": "hiring",
                "subject_template": "{{company}}'s SDR hiring",
                "body_template": """Hi {{decision_maker}},

Saw {{company}} is hiring SDRs. {{signal}}

Usually looks busy early, but meetings lag. {{pain_point}}

{{custom_hook}}

Volume or conversion breaking first?

Best,""",
                "signal_keywords": ["hiring", "SDR", "BDR", "sales team", "growing team"],
                "is_default": True
            },
            {
                "name": "Product Launch",
                "category": "product_launch",
                "subject_template": "{{company}} launch + outbound",
                "body_template": """Hi {{decision_maker}},

{{signal}} - exciting launch.

Quick question: are you handling the outbound volume increase manually, or do you have automation in place?

{{custom_hook}}

{{pain_point}} gets harder at scale.

Best,""",
                "signal_keywords": ["launch", "announced", "released", "new product"],
                "is_default": True
            },
            {
                "name": "Generic - Pain Point",
                "category": "general",
                "subject_template": "{{company}} - {{pain_point}}",
                "body_template": """Hi {{decision_maker}},

{{signal}}

{{pain_point}} is costing most teams 20+ hours/week. {{custom_hook}}

Worth a 10-minute conversation?

Best,""",
                "signal_keywords": [],
                "is_default": True
            }
        ]
        
        for template_data in defaults:
            self.create_template(**template_data)


def match_and_personalize(db: Session, lead: Lead, offer_angle: str = None) -> Dict[str, str]:
    """Convenience function: match template and personalize in one call"""
    service = TemplateService(db)
    template, confidence = service.match_template_to_lead(lead)
    return service.personalize_message(lead, template, offer_angle)


def initialize_default_templates(db: Session):
    """Initialize default templates on startup"""
    service = TemplateService(db)
    service.seed_default_templates()


TEMPLATE_CATEGORIES = {
    "funding": "Funding announcements, investment news",
    "hiring": "Hiring signals, team expansion",
    "product_launch": "New product announcements",
    "partnership": "Partnership announcements",
    "expansion": "Geographic or market expansion",
    "acquisition": "M&A activity",
    "general": "General purpose templates"
}


__all__ = [
    'TemplateService',
    'match_and_personalize',
    'initialize_default_templates',
    'TEMPLATE_CATEGORIES'
]
