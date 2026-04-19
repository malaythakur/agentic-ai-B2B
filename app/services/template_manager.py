"""
Email Template Management System

Manages email templates for outreach and follow-ups:
- Create and store templates
- Template variables and substitution
- A/B testing support
- Template performance tracking
- Default templates for common scenarios
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TemplateManager:
    """Service for managing email templates"""
    
    # Default templates
    DEFAULT_TEMPLATES = {
        "intro": {
            "subject": "{provider_name} + {buyer_name}",
            "body": """Hi {buyer_name} Team,

I noticed that {buyer_name} might benefit from {provider_name}'s expertise in {services}.

{signals_text}

We've helped similar companies achieve great results, and I'd love to explore how we could support your goals.

Would you be open to a brief conversation this week?

Best regards,
{provider_name}

---
To unsubscribe: {unsubscribe_link}
"""
        },
        "followup_1": {
            "subject": "Quick follow-up: {provider_name} + {buyer_name}",
            "body": """Hi {buyer_name} Team,

I wanted to follow up on my previous email about how {provider_name} could help with {services}.

I understand you're likely busy, but I thought this might be relevant given your recent activities.

Would you be open to a brief 15-minute call to explore if there's a fit?

Best regards,
{provider_name}

---
To unsubscribe: {unsubscribe_link}
"""
        },
        "followup_2": {
            "subject": "Another thought on {buyer_name}'s growth",
            "body": """Hi {buyer_name} Team,

I've been thinking about your company's trajectory and how {provider_name} could support your growth.

Here's a quick case study: We recently helped a similar company achieve [specific result] with {services}.

I'd love to share more details about how we could do the same for you.

Open to a quick chat?

Best,
{provider_name}

---
To unsubscribe: {unsubscribe_link}
"""
        },
        "followup_3": {
            "subject": "Last message regarding {buyer_name}",
            "body": """Hi {buyer_name} Team,

This is my last follow-up regarding potential collaboration between our companies.

I believe {provider_name} could add significant value to {buyer_name}, especially with {services}.

If you're interested in exploring this further, great! If not, I'll respect your inbox and won't follow up again.

Either way, I'd appreciate a quick reply so I know where we stand.

Best,
{provider_name}

---
To unsubscribe: {unsubscribe_link}
"""
        }
    }
    
    def __init__(self, db: Session):
        """
        Initialize template manager
        
        Args:
            db: Database session
        """
        self.db = db
        self.custom_templates = {}  # In production, store in database
    
    def get_template(self, template_type: str) -> Dict:
        """
        Get template by type
        
        Args:
            template_type: Type of template (intro, followup_1, etc.)
            
        Returns:
            Template dict with subject and body
        """
        # Check custom templates first
        if template_type in self.custom_templates:
            return self.custom_templates[template_type]
        
        # Return default template
        return self.DEFAULT_TEMPLATES.get(template_type, {})
    
    def create_template(
        self,
        template_id: str,
        template_type: str,
        subject: str,
        body: str,
        variables: List[str] = None
    ) -> Dict:
        """
        Create a custom template
        
        Args:
            template_id: Unique template ID
            template_type: Type of template
            subject: Email subject
            body: Email body
            variables: List of template variables
            
        Returns:
            Result of template creation
        """
        template = {
            "template_id": template_id,
            "template_type": template_type,
            "subject": subject,
            "body": body,
            "variables": variables or [],
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.custom_templates[template_id] = template
        
        logger.info(f"Created custom template: {template_id}")
        return {"success": True, "template": template}
    
    def render_template(
        self,
        template_type: str,
        variables: Dict
    ) -> Dict:
        """
        Render template with variables
        
        Args:
            template_type: Type of template
            variables: Dict of variable names to values
            
        Returns:
            Rendered email with subject and body
        """
        template = self.get_template(template_type)
        
        if not template:
            return {"success": False, "error": "Template not found"}
        
        try:
            subject = template["subject"]
            body = template["body"]
            
            # Substitute variables
            for key, value in variables.items():
                placeholder = "{" + key + "}"
                subject = subject.replace(placeholder, str(value))
                body = body.replace(placeholder, str(value))
            
            return {
                "success": True,
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            logger.error(f"Failed to render template: {e}")
            return {"success": False, "error": str(e)}
    
    def list_templates(self) -> List[Dict]:
        """
        List all available templates
        
        Returns:
            List of template info
        """
        templates = []
        
        # Add default templates
        for template_type, template in self.DEFAULT_TEMPLATES.items():
            templates.append({
                "template_type": template_type,
                "is_custom": False,
                "subject": template["subject"]
            })
        
        # Add custom templates
        for template_id, template in self.custom_templates.items():
            templates.append({
                "template_id": template_id,
                "template_type": template["template_type"],
                "is_custom": True,
                "subject": template["subject"],
                "created_at": template.get("created_at")
            })
        
        return templates
    
    def delete_template(self, template_id: str) -> Dict:
        """
        Delete a custom template
        
        Args:
            template_id: Template ID to delete
            
        Returns:
            Result of deletion
        """
        if template_id in self.custom_templates:
            del self.custom_templates[template_id]
            logger.info(f"Deleted custom template: {template_id}")
            return {"success": True, "message": "Template deleted"}
        
        return {"success": False, "error": "Template not found or is default"}
    
    def get_template_variables(self, template_type: str) -> List[str]:
        """
        Get variables used in a template
        
        Args:
            template_type: Type of template
            
        Returns:
            List of variable names
        """
        template = self.get_template(template_type)
        
        if not template:
            return []
        
        variables = set()
        
        # Extract variables from subject and body
        for text in [template.get("subject", ""), template.get("body", "")]:
            import re
            matches = re.findall(r'\{(\w+)\}', text)
            variables.update(matches)
        
        return list(variables)
