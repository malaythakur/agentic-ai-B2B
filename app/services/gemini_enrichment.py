"""
Gemini AI Lead Enrichment Service
Uses Google's Gemini API (free tier) to research and enrich lead data
"""
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import httpx
from datetime import datetime


@dataclass
class EnrichedLead:
    """Enriched lead data structure"""
    company: str
    website: Optional[str]
    industry: Optional[str]
    employees: Optional[int]
    funding_stage: Optional[str]
    funding_amount: Optional[str]
    recent_news: List[str]
    decision_makers: List[Dict]
    pain_points: List[str]
    signals: List[str]
    tech_stack: List[str]
    competitors: List[str]
    market_position: Optional[str]
    priority_score: int
    qualification_reason: str


class GeminiEnrichmentService:
    """
    Service for enriching lead data using Gemini API
    Free tier: 60 requests per minute (enough for lead enrichment)
    """
    
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def enrich_company(self, company_name: str, known_signal: Optional[str] = None) -> EnrichedLead:
        """
        Research and enrich a company using Gemini AI
        
        Args:
            company_name: Company name to research
            known_signal: Any known signal (e.g., "hiring SDRs", "raised Series A")
        
        Returns:
            EnrichedLead with comprehensive company intelligence
        """
        # Build research prompt
        prompt = self._build_research_prompt(company_name, known_signal)
        
        # Call Gemini API
        response = await self._call_gemini(prompt)
        
        # Parse and structure the response
        enriched_data = self._parse_gemini_response(response, company_name)
        
        return enriched_data
    
    def _build_research_prompt(self, company_name: str, known_signal: Optional[str]) -> str:
        """Build a comprehensive research prompt for Gemini"""
        
        signal_context = f"\nKnown Signal: {known_signal}" if known_signal else ""
        
        prompt = f"""Research the company "{company_name}" for B2B sales outreach. Be thorough and accurate.{signal_context}

Provide a detailed JSON response with this exact structure:
{{
    "company_name": "Exact company name",
    "website": "Company website URL or null",
    "industry": "Primary industry (e.g., SaaS, Fintech, Healthcare Tech)",
    "company_size": {{
        "employees": "Number or range (e.g., 50-200)",
        "stage": "Startup, Growth, Enterprise"
    }},
    "funding": {{
        "stage": "Seed, Series A, Series B, Series C+, IPO, or Bootstrapped",
        "recent_round": "Amount and date if recent (within 12 months)",
        "total_raised": "Total funding amount"
    }},
    "decision_makers": [
        {{
            "name": "Full name or title if name unknown",
            "title": "Job title",
            "linkedin_url": "LinkedIn URL or null",
            "decision_authority": "High/Medium/Low - can they buy?"
        }}
    ],
    "recent_news": [
        "3-5 recent notable events (funding, product launches, expansions, hiring sprees)"
    ],
    "pain_points": [
        "3-5 likely business challenges they face based on their industry and stage"
    ],
    "buying_signals": [
        "Observable signals that indicate they might need our solution"
    ],
    "tech_stack": ["Known or likely technologies they use"],
    "competitors": ["Main competitors"],
    "market_position": "Brief summary of their market position and growth trajectory",
    "outreach_urgency": "High/Medium/Low - how urgent is it to reach out now?",
    "outreach_angle": "Best angle for initial outreach (e.g., scaling challenge, efficiency gain, competitive pressure)"
}}

Be factual. If you don't know something, use null or empty arrays. Focus on actionable sales intelligence.
"""
        return prompt
    
    async def _call_gemini(self, prompt: str) -> Dict:
        """Call Gemini API with the research prompt"""
        
        url = f"{self.GEMINI_API_URL}?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
                "topP": 0.8,
                "topK": 40
            }
        }
        
        try:
            response = await self.client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Gemini API error: {e}")
    
    def _parse_gemini_response(self, response: Dict, company_name: str) -> EnrichedLead:
        """Parse Gemini response into structured EnrichedLead"""
        
        try:
            # Extract text content from response
            candidates = response.get("candidates", [])
            if not candidates:
                return self._create_fallback_lead(company_name)
            
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                return self._create_fallback_lead(company_name)
            
            text = parts[0].get("text", "")
            
            # Extract JSON from response (it might be wrapped in markdown)
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # Try to parse the whole text
                data = json.loads(text)
            
            return self._structure_enriched_data(data, company_name)
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            # Return fallback with basic info
            return self._create_fallback_lead(company_name)
    
    def _structure_enriched_data(self, data: Dict, company_name: str) -> EnrichedLead:
        """Structure parsed data into EnrichedLead"""
        
        # Extract funding info
        funding = data.get("funding", {})
        funding_stage = funding.get("stage")
        funding_amount = funding.get("recent_round")
        
        # Extract company size
        company_size = data.get("company_size", {})
        employees_str = company_size.get("employees", "")
        employees = self._parse_employee_count(employees_str)
        
        # Calculate priority score based on signals
        priority_score = self._calculate_priority_score(data)
        
        # Build signals list
        signals = []
        recent_news = data.get("recent_news", [])
        buying_signals = data.get("buying_signals", [])
        signals.extend(recent_news[:3])
        signals.extend(buying_signals[:2])
        
        return EnrichedLead(
            company=data.get("company_name", company_name),
            website=data.get("website"),
            industry=data.get("industry"),
            employees=employees,
            funding_stage=funding_stage,
            funding_amount=funding_amount,
            recent_news=recent_news[:5],
            decision_makers=data.get("decision_makers", []),
            pain_points=data.get("pain_points", []),
            signals=signals,
            tech_stack=data.get("tech_stack", []),
            competitors=data.get("competitors", []),
            market_position=data.get("market_position"),
            priority_score=priority_score,
            qualification_reason=data.get("outreach_angle", "General B2B outreach")
        )
    
    def _parse_employee_count(self, employees_str: str) -> Optional[int]:
        """Parse employee count from string"""
        if not employees_str:
            return None
        
        # Extract first number from string
        numbers = re.findall(r'\d+', str(employees_str))
        if numbers:
            return int(numbers[0])
        return None
    
    def _calculate_priority_score(self, data: Dict) -> int:
        """Calculate lead priority score (0-100) based on enriched data"""
        score = 50  # Base score
        
        # Funding stage scoring
        funding = data.get("funding", {})
        funding_stage = funding.get("stage", "").lower()
        if "series c" in funding_stage or "series d" in funding_stage or "ipo" in funding_stage:
            score += 25
        elif "series b" in funding_stage:
            score += 20
        elif "series a" in funding_stage:
            score += 15
        elif "seed" in funding_stage:
            score += 10
        
        # Recent funding (last 6 months) is a strong signal
        recent_round = funding.get("recent_round", "")
        if recent_round and any(month in recent_round.lower() for month in ["jan", "feb", "mar", "apr", "may", "jun", "2024", "2025"]):
            score += 15
        
        # Company size (ideal: 50-500 employees)
        company_size = data.get("company_size", {})
        employees_str = company_size.get("employees", "")
        employees = self._parse_employee_count(employees_str)
        if employees:
            if 50 <= employees <= 500:
                score += 15
            elif 20 <= employees < 50:
                score += 10
        
        # Urgency signal
        urgency = data.get("outreach_urgency", "").lower()
        if urgency == "high":
            score += 15
        elif urgency == "medium":
            score += 5
        
        # Recent news signals
        recent_news = data.get("recent_news", [])
        if len(recent_news) >= 3:
            score += 10
        elif len(recent_news) >= 1:
            score += 5
        
        return min(score, 100)
    
    def _create_fallback_lead(self, company_name: str) -> EnrichedLead:
        """Create fallback lead when Gemini enrichment fails"""
        return EnrichedLead(
            company=company_name,
            website=None,
            industry=None,
            employees=None,
            funding_stage=None,
            funding_amount=None,
            recent_news=[],
            decision_makers=[],
            pain_points=[],
            signals=["Research needed"],
            tech_stack=[],
            competitors=[],
            market_position=None,
            priority_score=30,
            qualification_reason="Requires manual research"
        )
    
    async def batch_enrich(self, companies: List[str]) -> List[EnrichedLead]:
        """Enrich multiple companies in batch"""
        results = []
        
        for company in companies:
            try:
                enriched = await self.enrich_company(company)
                results.append(enriched)
            except Exception as e:
                # Add fallback on error
                results.append(self._create_fallback_lead(company))
        
        return results
    
    async def generate_outreach_message(
        self,
        lead: EnrichedLead,
        offer_type: str = "ai_automation"
    ) -> Dict[str, str]:
        """
        Generate personalized outreach message using Gemini
        
        Args:
            lead: Enriched lead data
            offer_type: Type of offer/solution
        
        Returns:
            Dict with subject and body
        """
        
        prompt = f"""Write a short, personalized cold email to {lead.decision_makers[0]['name'] if lead.decision_makers else 'the team'} at {lead.company}.

Company Context:
- Company: {lead.company}
- Industry: {lead.industry or 'Technology'}
- Size: {lead.employees or 'Unknown'} employees
- Signals: {', '.join(lead.signals[:3]) if lead.signals else 'Growing company'}
- Pain Points: {', '.join(lead.pain_points[:2]) if lead.pain_points else 'Scaling challenges'}

Our Solution: {offer_type}

Requirements:
- Max 100 words
- Personalized based on their signals
- Focus on value, not features
- One clear call-to-action (15-min call)
- Professional but conversational tone
- No generic phrases like "I hope this finds you well"

Respond ONLY with JSON:
{{
    "subject": "Compelling subject line (max 8 words)",
    "body": "Email body (max 100 words, no signatures)",
    "hook": "The specific personalization hook used"
}}
"""
        
        try:
            response = await self._call_gemini(prompt)
            
            # Extract content
            candidates = response.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                    
                    # Extract JSON
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
            
            # Fallback
            return {
                "subject": f"Quick question about {lead.company}",
                "body": f"Hi there,\n\nI noticed {lead.company} is {lead.signals[0] if lead.signals else 'growing fast'}. I'd love to share how we've helped similar companies scale efficiently.\n\nWorth a 15-min chat?\n\nBest",
                "hook": "Company growth signal"
            }
            
        except Exception:
            return {
                "subject": f"Quick question about {lead.company}",
                "body": f"Hi there,\n\nI'd love to learn more about {lead.company} and explore if we can help with {lead.pain_points[0] if lead.pain_points else 'your current challenges'}.\n\nWorth a brief chat?\n\nBest",
                "hook": "General outreach"
            }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
