"""
GitHub API Integration for Tech Signal Enrichment

Uses GitHub API to discover companies by tech stack, analyze repository activity,
and extract hiring signals from code repositories.
"""

import os
import requests
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GitHubEnrichmentService:
    """Service for enriching company data using GitHub API"""
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub enrichment service
        
        Args:
            github_token: GitHub personal access token (optional, increases rate limits)
        """
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {}
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"
        
        # Rate limit tracking
        self.rate_limit_remaining = 5000 if self.github_token else 60
        self.rate_limit_reset = None
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make authenticated request to GitHub API
        
        Args:
            endpoint: API endpoint (e.g., "/users/octocat")
            params: Query parameters
            
        Returns:
            JSON response or None if error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            # Update rate limit info
            self.rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API request failed: {e}")
            return None
    
    def search_repositories(
        self,
        query: str,
        language: Optional[str] = None,
        stars: Optional[int] = None,
        sort: str = "stars",
        per_page: int = 100
    ) -> List[Dict]:
        """
        Search GitHub repositories by query
        
        Args:
            query: Search query (e.g., "react", "kubernetes")
            language: Filter by programming language
            stars: Minimum stars
            sort: Sort order (stars, forks, updated)
            per_page: Results per page (max 100)
            
        Returns:
            List of repository data
        """
        params = {
            "q": query,
            "sort": sort,
            "per_page": per_page
        }
        
        if language:
            params["q"] += f" language:{language}"
        if stars:
            params["q"] += f" stars:>{stars}"
        
        result = self._make_request("/search/repositories", params)
        return result.get("items", []) if result else []
    
    def get_repository_activity(self, owner: str, repo: str, days: int = 30) -> Dict:
        """
        Get repository activity metrics
        
        Args:
            owner: Repository owner
            repo: Repository name
            days: Number of days to look back
            
        Returns:
            Activity metrics dict
        """
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Get commits
        commits = self._make_request(
            f"/repos/{owner}/{repo}/commits",
            {"since": since, "per_page": 100}
        )
        
        # Get issues
        issues = self._make_request(
            f"/repos/{owner}/{repo}/issues",
            {"since": since, "state": "all", "per_page": 100}
        )
        
        # Get pull requests
        pulls = self._make_request(
            f"/repos/{owner}/{repo}/pulls",
            {"state": "all", "per_page": 100}
        )
        
        return {
            "commits": len(commits) if commits else 0,
            "issues_opened": len([i for i in issues if i and i.get("state") == "open"]) if issues else 0,
            "issues_closed": len([i for i in issues if i and i.get("state") == "closed"]) if issues else 0,
            "pulls_opened": len([p for p in pulls if p and p.get("state") == "open"]) if pulls else 0,
            "pulls_merged": len([p for p in pulls if p and p.get("state") == "closed"]) if pulls else 0,
        }
    
    def extract_tech_stack_from_repo(self, owner: str, repo: str) -> List[str]:
        """
        Extract tech stack from repository
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of technologies used
        """
        tech_stack = []
        
        # Get repository details
        repo_data = self._make_request(f"/repos/{owner}/{repo}")
        if not repo_data:
            return tech_stack
        
        # Language
        if repo_data.get("language"):
            tech_stack.append(repo_data["language"])
        
        # Get languages breakdown
        languages = self._make_request(f"/repos/{owner}/{repo}/languages")
        if languages:
            tech_stack.extend(list(languages.keys()))
        
        # Get package.json if it exists (for JS projects)
        try:
            package_json = self._make_request(f"/repos/{owner}/{repo}/contents/package.json")
            if package_json and package_json.get("content"):
                import base64
                import json
                content = base64.b64decode(package_json["content"]).decode()
                pkg = json.loads(content)
                if "dependencies" in pkg:
                    tech_stack.extend(list(pkg["dependencies"].keys()))
        except:
            pass
        
        # Get requirements.txt if it exists (for Python projects)
        try:
            requirements = self._make_request(f"/repos/{owner}/{repo}/contents/requirements.txt")
            if requirements and requirements.get("content"):
                import base64
                content = base64.b64decode(requirements["content"]).decode()
                deps = [line.split("==")[0].strip() for line in content.split("\n") if line and not line.startswith("#")]
                tech_stack.extend(deps[:20])  # Limit to top 20
        except:
            pass
        
        return list(set(tech_stack))  # Deduplicate
    
    def detect_hiring_signals(self, owner: str, repo: str) -> List[Dict]:
        """
        Detect hiring signals from repository
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of hiring signal dicts
        """
        signals = []
        
        # Check for hiring-related files
        hiring_files = ["hiring.md", "careers.md", "jobs.md", "we-are-hiring.md"]
        for filename in hiring_files:
            try:
                file_data = self._make_request(f"/repos/{owner}/{repo}/contents/{filename}")
                if file_data:
                    signals.append({
                        "type": "hiring",
                        "source": "github_file",
                        "file": filename,
                        "confidence": 0.8
                    })
            except:
                pass
        
        # Check for recent hiring-related commits
        commits = self._make_request(
            f"/repos/{owner}/{repo}/commits",
            {"per_page": 20}
        )
        if commits:
            hiring_keywords = ["hire", "recruit", "job", "career", "team", "engineer"]
            for commit in commits[:10]:
                message = commit.get("commit", {}).get("message", "").lower()
                if any(keyword in message for keyword in hiring_keywords):
                    signals.append({
                        "type": "hiring",
                        "source": "commit_message",
                        "message": commit.get("commit", {}).get("message"),
                        "date": commit.get("commit", {}).get("committer", {}).get("date"),
                        "confidence": 0.6
                    })
        
        return signals
    
    def find_companies_by_tech_stack(
        self,
        tech_stack: List[str],
        min_stars: int = 10,
        limit: int = 50
    ) -> List[Dict]:
        """
        Find companies using specific tech stack
        
        Args:
            tech_stack: List of technologies to search for
            min_stars: Minimum repository stars
            limit: Maximum results
            
        Returns:
            List of company data with tech stack info
        """
        companies = {}
        
        for tech in tech_stack:
            repos = self.search_repositories(
                query=tech,
                stars=min_stars,
                per_page=min(limit // len(tech_stack), 20)
            )
            
            for repo in repos:
                owner = repo.get("owner", {}).get("login")
                if not owner or owner in companies:
                    continue
                
                # Extract company info
                company_info = {
                    "company_name": owner,
                    "website": repo.get("owner", {}).get("html_url"),
                    "repository": repo.get("full_name"),
                    "stars": repo.get("stargazers_count"),
                    "forks": repo.get("forks_count"),
                    "language": repo.get("language"),
                    "description": repo.get("description"),
                    "updated_at": repo.get("updated_at"),
                    "tech_stack": [repo.get("language")] if repo.get("language") else []
                }
                
                # Enrich with more tech stack info
                try:
                    full_tech = self.extract_tech_stack_from_repo(owner, repo.get("name"))
                    company_info["tech_stack"].extend(full_tech)
                    company_info["tech_stack"] = list(set(company_info["tech_stack"]))
                except:
                    pass
                
                companies[owner] = company_info
                
                if len(companies) >= limit:
                    break
            
            if len(companies) >= limit:
                break
        
        return list(companies.values())
    
    def get_rate_limit_status(self) -> Dict:
        """
        Get current rate limit status
        
        Returns:
            Rate limit info dict
        """
        return {
            "remaining": self.rate_limit_remaining,
            "reset_at": datetime.fromtimestamp(self.rate_limit_reset).isoformat() if self.rate_limit_reset else None,
            "has_token": bool(self.github_token)
        }


# Example usage
if __name__ == "__main__":
    service = GitHubEnrichmentService()
    
    # Find companies using React
    companies = service.find_companies_by_tech_stack(["react", "kubernetes"], min_stars=50, limit=10)
    print(f"Found {len(companies)} companies")
    for company in companies[:3]:
        print(f"\n{company['company_name']}")
        print(f"  Tech stack: {company['tech_stack']}")
        print(f"  Stars: {company['stars']}")
