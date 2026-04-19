"""
Crunchbase API Integration for Company Data Enrichment

Uses Crunchbase API to fetch funding information, investor data,
and company details for prospect enrichment.
"""

import os
import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CrunchbaseEnrichmentService:
    """Service for enriching company data using Crunchbase API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Crunchbase enrichment service
        
        Args:
            api_key: Crunchbase API key
        """
        self.api_key = api_key or os.getenv("CRUNCHBASE_API_KEY")
        if not self.api_key:
            logger.warning("CRUNCHBASE_API_KEY not set, Crunchbase features will be disabled")
        
        self.base_url = "https://api.crunchbase.com/api/v4"
        self.headers = {}
        if self.api_key:
            self.headers["X-CB-API-Key"] = self.api_key
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make authenticated request to Crunchbase API
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response or None if error
        """
        if not self.api_key:
            logger.error("Crunchbase API key not configured")
            return None
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Crunchbase API request failed: {e}")
            return None
    
    def search_organizations(
        self,
        query: str,
        organization_types: Optional[List[str]] = None,
        funding_stage: Optional[str] = None,
        location_countries: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search for organizations on Crunchbase
        
        Args:
            query: Search query
            organization_types: Filter by type (e.g., ["company", "investor"])
            funding_stage: Filter by funding stage (e.g., "series_b")
            location_countries: Filter by country codes (e.g., ["USA", "GBR"])
            limit: Maximum results
            
        Returns:
            List of organization data
        """
        params = {
            "query": query,
            "limit": limit
        }
        
        if organization_types:
            params["field_ids"] = f"organization_types[{','.join(organization_types)}]"
        if funding_stage:
            params["field_ids"] = f"funding_stage[{funding_stage}]"
        if location_countries:
            params["field_ids"] = f"location_identifiers[{','.join(location_countries)}]"
        
        result = self._make_request("/searches/organizations", params)
        
        if result and "entities" in result:
            return result["entities"]
        return []
    
    def get_organization(self, organization_id: str) -> Optional[Dict]:
        """
        Get detailed organization information
        
        Args:
            organization_id: Crunchbase organization ID (e.g., "apple")
            
        Returns:
            Organization data dict
        """
        result = self._make_request(f"/entities/organizations/{organization_id}")
        return result
    
    def get_funding_rounds(self, organization_id: str) -> List[Dict]:
        """
        Get funding rounds for an organization
        
        Args:
            organization_id: Crunchbase organization ID
            
        Returns:
            List of funding round data
        """
        result = self._make_request(f"/entities/organizations/{organization_id}/funding_rounds")
        
        if result and "items" in result:
            return result["items"]
        return []
    
    def get_investors(self, organization_id: str) -> List[Dict]:
        """
        Get investors for an organization
        
        Args:
            organization_id: Crunchbase organization ID
            
        Returns:
            List of investor data
        """
        result = self._make_request(f"/entities/organizations/{organization_id}/investors")
        
        if result and "items" in result:
            return result["items"]
        return []
    
    def get_company_by_domain(self, domain: str) -> Optional[Dict]:
        """
        Get company information by domain
        
        Args:
            domain: Company domain (e.g., "stripe.com")
            
        Returns:
            Company data dict
        """
        # Search for the domain
        params = {
            "query": domain,
            "field_ids": "domain",
            "limit": 1
        }
        
        result = self._make_request("/searches/organizations", params)
        
        if result and "entities" in result and len(result["entities"]) > 0:
            org_id = result["entities"][0].get("properties", {}).get("identifier", {}).get("uuid")
            if org_id:
                return self.get_organization(org_id)
        
        return None
    
    def extract_funding_signals(self, organization_id: str) -> Dict:
        """
        Extract funding-related signals from organization data
        
        Args:
            organization_id: Crunchbase organization ID
            
        Returns:
            Funding signals dict
        """
        funding_rounds = self.get_funding_rounds(organization_id)
        
        if not funding_rounds:
            return {
                "total_funding": 0,
                "latest_round": None,
                "latest_round_date": None,
                "investor_count": 0,
                "funding_stages": []
            }
        
        total_funding = 0
        latest_round = None
        latest_round_date = None
        funding_stages = []
        investors = set()
        
        for round_data in funding_rounds:
            properties = round_data.get("properties", {})
            
            # Add to total funding
            money_raised = properties.get("money_raised_usd", 0)
            if money_raised:
                total_funding += money_raised
            
            # Track latest round
            announced_on = properties.get("announced_on")
            if announced_on:
                round_date = datetime.fromisoformat(announced_on.replace("Z", "+00:00"))
                if not latest_round_date or round_date > latest_round_date:
                    latest_round_date = round_date
                    latest_round = {
                        "type": properties.get("investment_type"),
                        "amount": money_raised,
                        "date": announced_on
                    }
            
            # Track funding stages
            investment_type = properties.get("investment_type")
            if investment_type:
                funding_stages.append(investment_type)
            
            # Track investors
            for investor in properties.get("investor_identifiers", []):
                investors.add(investor.get("value"))
        
        return {
            "total_funding": total_funding,
            "latest_round": latest_round,
            "latest_round_date": latest_round_date.isoformat() if latest_round_date else None,
            "investor_count": len(investors),
            "funding_stages": list(set(funding_stages))
        }
    
    def find_companies_by_funding_stage(
        self,
        funding_stage: str,
        industry: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Find companies by funding stage
        
        Args:
            funding_stage: Funding stage (e.g., "series_a", "series_b")
            industry: Filter by industry
            location: Filter by location
            limit: Maximum results
            
        Returns:
            List of company data
        """
        query_parts = [funding_stage]
        
        if industry:
            query_parts.append(industry)
        
        query = " ".join(query_parts)
        
        companies = self.search_organizations(
            query=query,
            funding_stage=funding_stage,
            location_countries=[location] if location else None,
            limit=limit
        )
        
        # Enrich with funding signals
        enriched_companies = []
        for company in companies[:limit]:
            properties = company.get("properties", {})
            org_id = properties.get("identifier", {}).get("uuid")
            
            if org_id:
                funding_signals = self.extract_funding_signals(org_id)
                
                enriched_company = {
                    "company_name": properties.get("name"),
                    "website": properties.get("website"),
                    "description": properties.get("short_description"),
                    "funding_signals": funding_signals,
                    "crunchbase_id": org_id,
                    "industry": properties.get("category_groups", [])
                }
                
                enriched_companies.append(enriched_company)
        
        return enriched_companies
    
    def get_rate_limit_status(self) -> Dict:
        """
        Get current rate limit status
        
        Returns:
            Rate limit info dict
        """
        return {
            "has_api_key": bool(self.api_key),
            "plan": "free" if self.api_key else "none",
            "daily_limit": 100,  # Free tier limit
            "monthly_limit": 5000  # Free tier limit
        }


# Example usage
if __name__ == "__main__":
    service = CrunchbaseEnrichmentService()
    
    # Find Series B companies
    companies = service.find_companies_by_funding_stage("series_b", limit=5)
    print(f"Found {len(companies)} Series B companies")
    for company in companies[:3]:
        print(f"\n{company['company_name']}")
        print(f"  Funding: ${company['funding_signals']['total_funding']:,}")
        print(f"  Latest round: {company['funding_signals']['latest_round']}")
