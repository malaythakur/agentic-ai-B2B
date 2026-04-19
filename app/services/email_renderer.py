from app.models import Lead
from app.settings import settings
import openai


class EmailRenderer:
    """Service for rendering email bodies from lead data"""
    
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
    
    def render(self, lead: Lead) -> str:
        """Render email body for a lead"""
        try:
            # Use LLM for light personalization polishing
            prompt = self._build_prompt(lead)
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at writing personalized cold emails. Keep them concise (under 150 words), relevant to the recipient's situation, and focused on starting a conversation. No salesy language."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            body = response.choices[0].message.content.strip()
            return body
        except Exception as e:
            # Fallback to template-based rendering
            return self._render_from_template(lead)
    
    def _build_prompt(self, lead: Lead) -> str:
        """Build prompt for LLM"""
        prompt = f"""
Write a personalized cold email for this lead:

Company: {lead.company}
Decision Maker: {lead.decision_maker}
Signal: {lead.signal}
Fit Score: {lead.fit_score}
Base Message: {lead.message_intent}

The email should:
- Be under 150 words
- Reference their specific situation (signal)
- Be conversational, not salesy
- End with a clear, low-friction call to action
- Feel like it was written by a human who did research

Return only the email body, nothing else.
"""
        return prompt
    
    def _render_from_template(self, lead: Lead) -> str:
        """Render email from template as fallback"""
        if lead.message_intent:
            return lead.message_intent
        
        # Fallback template
        signal_hook = self._extract_signal_hook(lead.signal)
        
        body = f"""Hi {lead.decision_maker or 'there'},

{signal_hook}

I noticed {lead.company} is {self._extract_activity(lead.signal)}.

Would you be open to a quick conversation about this?

Best,
"""
        return body
    
    def _extract_signal_hook(self, signal: str) -> str:
        """Extract hook from signal"""
        if not signal:
            return "I hope this finds you well."
        
        # Extract first meaningful sentence
        sentences = signal.split('.')
        for sentence in sentences[:2]:
            if len(sentence.strip()) > 20:
                return sentence.strip() + "."
        
        return "I hope this finds you well."
    
    def _extract_activity(self, signal: str) -> str:
        """Extract activity from signal"""
        if not signal:
            return "growing"
        
        signal_lower = signal.lower()
        if "hiring" in signal_lower:
            return "expanding your team"
        elif "funding" in signal_lower or "series" in signal_lower:
            return "scaling rapidly"
        elif "launched" in signal_lower:
            return "launching new products"
        else:
            return "making moves"
