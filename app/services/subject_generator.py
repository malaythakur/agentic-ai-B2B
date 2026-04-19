from typing import List
from app.models import Lead
from app.settings import settings
import openai


class SubjectGenerator:
    """Service for generating subject lines using LLM"""
    
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.subject_templates = [
            "{company}: {signal_summary}",
            "Quick question about {company}",
            "{signal_hook}",
            "{decision_maker} at {company}",
            "Regarding {company}'s recent {signal_type}",
        ]
    
    def generate(self, lead: Lead) -> str:
        """Generate a subject line for a lead"""
        try:
            # Use LLM for subject generation
            prompt = self._build_prompt(lead)
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at writing cold email subject lines that get opened. Keep them under 50 characters, personalized, and relevant to the recipient's situation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            subject = response.choices[0].message.content.strip()
            return subject
        except Exception as e:
            # Fallback to template-based generation
            return self._generate_from_template(lead)
    
    def _build_prompt(self, lead: Lead) -> str:
        """Build prompt for LLM"""
        prompt = f"""
Generate a compelling email subject line for this lead:

Company: {lead.company}
Decision Maker: {lead.decision_maker}
Signal: {lead.signal[:200]}...
Fit Score: {lead.fit_score}

The subject should be:
- Under 50 characters
- Personalized to the company/decision maker
- Relevant to their signal/situation
- Not salesy or spammy

Return only the subject line, nothing else.
"""
        return prompt
    
    def _generate_from_template(self, lead: Lead) -> str:
        """Generate subject from template as fallback"""
        import random
        
        signal_summary = self._extract_signal_summary(lead.signal)
        signal_hook = self._extract_hook(lead.signal)
        signal_type = self._extract_signal_type(lead.signal)
        
        template = random.choice(self.subject_templates)
        subject = template.format(
            company=lead.company,
            signal_summary=signal_summary,
            signal_hook=signal_hook,
            decision_maker=lead.decision_maker or "Team",
            signal_type=signal_type
        )
        
        return subject[:50]  # Ensure under 50 chars
    
    def _extract_signal_summary(self, signal: str) -> str:
        """Extract short summary from signal"""
        if not signal:
            return "growth"
        
        # Take first 30 chars
        return signal[:30].split()[0] if len(signal) > 30 else signal[:30]
    
    def _extract_hook(self, signal: str) -> str:
        """Extract hook from signal"""
        if "hiring" in signal.lower():
            return "hiring update"
        elif "funding" in signal.lower() or "series" in signal.lower():
            return "funding news"
        elif "launched" in signal.lower():
            return "product launch"
        else:
            return "quick question"
    
    def _extract_signal_type(self, signal: str) -> str:
        """Extract signal type"""
        if not signal:
            return "update"
        
        signal_lower = signal.lower()
        if "hiring" in signal_lower:
            return "hiring"
        elif "funding" in signal_lower or "series" in signal_lower:
            return "funding"
        elif "launched" in signal_lower:
            return "launch"
        else:
            return "news"
