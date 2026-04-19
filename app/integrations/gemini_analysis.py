"""
Gemini API Integration for AI-Powered Company Analysis

Uses Google Gemini API to analyze company descriptions, extract signals,
and provide insights for prospect scoring.
"""

import os
import logging
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


class GeminiAnalysisService:
    """Service for AI-powered company analysis using Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini analysis service
        
        Args:
            api_key: Gemini API key
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set, Gemini features will be disabled")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "gemini-pro"  # Free tier model
    
    def _make_request(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """
        Make request to Gemini API
        
        Args:
            prompt: Text prompt
            temperature: Creativity temperature (0-1)
            
        Returns:
            Generated text or None if error
        """
        if not self.api_key:
            logger.error("Gemini API key not configured")
            return None
        
        import requests
        
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 2048
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini API request failed: {e}")
            return None
    
    def analyze_company_description(self, description: str) -> Dict:
        """
        Analyze company description to extract insights
        
        Args:
            description: Company description text
            
        Returns:
            Analysis dict with industry, tech stack, signals
        """
        prompt = f"""Analyze this company description and extract the following information in JSON format:
{description}

Return a JSON object with these fields:
- industry: The primary industry
- tech_stack: List of technologies mentioned
- business_model: The business model (e.g., SaaS, marketplace, consulting)
- target_market: The target customer segment
- signals: List of growth signals (e.g., "enterprise focus", "high growth", "expanding")
- confidence: Your confidence in this analysis (0-1)

Return ONLY the JSON, no other text."""
        
        response = self._make_request(prompt, temperature=0.3)
        
        if response:
            try:
                # Extract JSON from response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                logger.error("Failed to parse Gemini response as JSON")
        
        # Fallback to basic analysis
        return {
            "industry": "unknown",
            "tech_stack": [],
            "business_model": "unknown",
            "target_market": "unknown",
            "signals": [],
            "confidence": 0.0
        }
    
    def extract_signals_from_text(self, text: str, signal_types: List[str]) -> List[Dict]:
        """
        Extract specific signals from text
        
        Args:
            text: Text to analyze
            signal_types: Types of signals to extract (e.g., ["funding", "hiring", "growth"])
            
        Returns:
            List of signal dicts
        """
        prompt = f"""Extract signals from this text: {text}

Look for these types of signals: {", ".join(signal_types)}

For each signal found, return:
- type: The signal type
- value: The signal value (e.g., "$50M Series B", "hiring 10 engineers")
- confidence: Your confidence (0-1)

Return as JSON array of objects, no other text."""
        
        response = self._make_request(prompt, temperature=0.5)
        
        if response:
            try:
                json_start = response.find("[")
                json_end = response.rfind("]") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        return []
    
    def score_company_fit(
        self,
        company_description: str,
        provider_services: List[str],
        provider_industries: List[str]
    ) -> Dict:
        """
        Score how well a company fits as a buyer for a provider
        
        Args:
            company_description: Buyer company description
            provider_services: Services offered by provider
            provider_industries: Industries provider targets
            
        Returns:
            Score dict with breakdown
        """
        prompt = f"""Score the fit between this buyer company and provider.

Buyer company: {company_description}

Provider services: {", ".join(provider_services)}
Provider target industries: {", ".join(provider_industries)}

Return a JSON object with:
- fit_score: Overall fit score (0-100)
- service_fit: How well buyer needs match provider services (0-100)
- industry_fit: How well buyer industry matches provider targets (0-100)
- readiness_score: How ready buyer is to purchase (0-100)
- reasoning: Brief explanation of the score

Return ONLY the JSON, no other text."""
        
        response = self._make_request(prompt, temperature=0.3)
        
        if response:
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Fallback scoring
        return {
            "fit_score": 50,
            "service_fit": 50,
            "industry_fit": 50,
            "readiness_score": 50,
            "reasoning": "Unable to analyze with AI, using default score"
        }
    
    def generate_personalized_intro(
        self,
        buyer_company: str,
        buyer_signals: List[str],
        provider_company: str,
        provider_services: List[str],
        provider_case_study: Optional[str] = None
    ) -> str:
        """
        Generate personalized introduction email
        
        Args:
            buyer_company: Buyer company name
            buyer_signals: Signals about buyer (e.g., "raised $20M", "hiring engineers")
            provider_company: Provider company name
            provider_services: Services offered
            provider_case_study: Optional case study to include
            
        Returns:
            Generated email text
        """
        signals_text = ", ".join(buyer_signals)
        services_text = ", ".join(provider_services)
        
        prompt = f"""Write a personalized introduction email from {provider_company} to {buyer_company}.

About {buyer_company}: {signals_text}

About {provider_company}: They offer {services_text}
{f"Case study: {provider_case_study}" if provider_case_study else ""}

Requirements:
- Keep it under 200 words
- Mention the specific signals about the buyer
- Be professional but conversational
- Include a clear call to action
- Don't sound like a generic sales email

Return ONLY the email body, no subject line or other text."""
        
        return self._make_request(prompt, temperature=0.8) or ""
    
    def classify_company_stage(self, description: str, employee_count: int, funding: str) -> Dict:
        """
        Classify company growth stage
        
        Args:
            description: Company description
            employee_count: Number of employees
            funding: Funding information (e.g., "$10M Series A")
            
        Returns:
            Stage classification dict
        """
        prompt = f"""Classify this company's growth stage.

Description: {description}
Employees: {employee_count}
Funding: {funding}

Return JSON with:
- stage: One of "pre-seed", "seed", "series_a", "series_b", "series_c", "growth", "mature", "enterprise"
- confidence: Your confidence (0-1)
- reasoning: Brief explanation

Return ONLY the JSON."""
        
        response = self._make_request(prompt, temperature=0.3)
        
        if response:
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Rule-based fallback
        if employee_count < 10:
            return {"stage": "pre-seed", "confidence": 0.5, "reasoning": "Small team"}
        elif employee_count < 50:
            return {"stage": "seed", "confidence": 0.5, "reasoning": "Small to medium team"}
        elif employee_count < 200:
            return {"stage": "series_a", "confidence": 0.5, "reasoning": "Medium team"}
        elif employee_count < 500:
            return {"stage": "series_b", "confidence": 0.5, "reasoning": "Growing team"}
        elif employee_count < 1000:
            return {"stage": "series_c", "confidence": 0.5, "reasoning": "Large team"}
        elif employee_count < 5000:
            return {"stage": "growth", "confidence": 0.5, "reasoning": "Large company"}
        else:
            return {"stage": "enterprise", "confidence": 0.5, "reasoning": "Very large company"}
    
    def extract_value_signals(self, description: str, website: str) -> Dict:
        """
        Extract signals about company value/revenue potential
        
        Args:
            description: Company description
            website: Company website
            
        Returns:
            Value signals dict
        """
        prompt = f"""Extract value signals about this company.

Description: {description}
Website: {website}

Return JSON with:
- estimated_revenue_range: One of "pre-revenue", "<$1M", "$1M-$10M", "$10M-$50M", "$50M-$100M", ">$100M"
- deal_size_estimate: Estimated deal size for B2B services (e.g., "$50K-$100K")
- urgency_score: How urgent their need might be (0-100)
- budget_readiness: Their readiness to spend (0-100)
- reasoning: Brief explanation

Return ONLY the JSON."""
        
        response = self._make_request(prompt, temperature=0.3)
        
        if response:
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        return {
            "estimated_revenue_range": "unknown",
            "deal_size_estimate": "unknown",
            "urgency_score": 50,
            "budget_readiness": 50,
            "reasoning": "Unable to analyze"
        }


# Example usage
if __name__ == "__main__":
    service = GeminiAnalysisService()
    
    # Analyze a company
    description = "TechStartup provides AI-powered customer service automation for e-commerce companies. We use machine learning to help businesses automate 80% of customer support queries."
    analysis = service.analyze_company_description(description)
    print("Company Analysis:")
    print(json.dumps(analysis, indent=2))
    
    # Generate intro
    intro = service.generate_personalized_intro(
        buyer_company="ShopCo",
        buyer_signals=["raised $20M Series B", "hiring 10 customer support agents"],
        provider_company="SupportAI",
        provider_services=["AI chatbots", "Customer service automation"],
        provider_case_study="Helped RetailInc reduce support costs by 60%"
    )
    print("\nGenerated Intro:")
    print(intro)
