"""
MASS MATCHMAKING ENGINE
Generate intelligent matches for 2000+ providers with 2000+ buyers
Strategy: Industry-first filtering + AI scoring + batch processing
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker
from app.models import ServiceProvider, BuyerCompany, Match
from dotenv import load_dotenv
from typing import List, Tuple, Dict
from dataclasses import dataclass
from datetime import datetime
import uuid
import time

load_dotenv()

@dataclass
class MatchCandidate:
    provider: ServiceProvider
    buyer: BuyerCompany
    score: int
    reasons: List[str]

class MassMatchmakingEngine:
    """
    Enterprise-grade matchmaking for massive datasets
    - Industry-first bucketing for performance
    - Multi-factor scoring algorithm
    - Batch database operations
    - Deduplication across existing matches
    """
    
    def __init__(self, db, batch_size=100):
        self.db = db
        self.batch_size = batch_size
        self.match_buffer = []
        self.total_created = 0
        self.skipped = 0
        self.existing_pairs = set()
        self._load_existing_matches()
    
    def _load_existing_matches(self):
        """Load existing match pairs to avoid duplicates"""
        print("Loading existing matches for deduplication...")
        matches = self.db.query(Match.provider_id, Match.buyer_id).all()
        self.existing_pairs = {(m[0], m[1]) for m in matches}
        print(f"  Found {len(self.existing_pairs)} existing matches")
    
    def is_duplicate_match(self, provider_id: str, buyer_id: str) -> bool:
        return (provider_id, buyer_id) in self.existing_pairs
    
    def calculate_match_score(self, provider: ServiceProvider, buyer: BuyerCompany) -> Tuple[int, List[str]]:
        """
        AI-powered match scoring algorithm
        Returns: (score 0-100, list of match reasons)
        """
        score = 0
        reasons = []
        
        # Factor 1: Industry Match (0-25 points)
        if provider.industries and buyer.industry:
            provider_industries = [ind.lower() for ind in provider.industries]
            if buyer.industry.lower() in provider_industries:
                score += 25
                reasons.append(f"Industry: {buyer.industry}")
            else:
                # Partial match - check if any overlap
                for p_ind in provider.industries:
                    if any(word in p_ind.lower() for word in buyer.industry.lower().split()):
                        score += 15
                        reasons.append(f"Related industry: {p_ind}")
                        break
        
        # Factor 2: Service-Signal Fit (0-40 points)
        if provider.services and buyer.signals:
            services = [s.lower() for s in provider.services]
            signals = buyer.signals if isinstance(buyer.signals, list) else []
            
            for service in services:
                for signal in signals:
                    signal_lower = signal.lower()
                    # Direct service mention in signal
                    if service in signal_lower:
                        score += 40
                        reasons.append(f"{service} matches {signal[:40]}")
                        break
                    # Partial match
                    elif any(word in signal_lower for word in service.split()):
                        score += 25
                        reasons.append(f"Service fit: {service}")
                        break
        
        # Factor 3: Requirements Match (0-25 points)
        if provider.services and buyer.requirements:
            services = [s.lower() for s in provider.services]
            requirements = buyer.requirements if isinstance(buyer.requirements, list) else []
            
            for service in services:
                for req in requirements:
                    if service in req.lower():
                        score += 25
                        reasons.append(f"Fulfills requirement: {req[:40]}")
                        break
        
        # Factor 4: Company Size Compatibility (0-10 points)
        # Small providers <-> Small buyers, Enterprise <-> Enterprise
        if provider.icp_criteria and isinstance(provider.icp_criteria, dict):
            target_size = provider.icp_criteria.get('target_company_size', '').lower()
            if buyer.employee_count:
                if target_size == 'small' and buyer.employee_count < 50:
                    score += 10
                    reasons.append("Size: Small business fit")
                elif target_size == 'mid' and 50 <= buyer.employee_count < 500:
                    score += 10
                    reasons.append("Size: Mid-market fit")
                elif target_size == 'enterprise' and buyer.employee_count >= 500:
                    score += 10
                    reasons.append("Size: Enterprise fit")
        
        return min(score, 100), reasons[:3]  # Cap at 100, return top 3 reasons
    
    def create_match(self, candidate: MatchCandidate):
        """Create a match record"""
        match = Match(
            match_id=f"match-{str(uuid.uuid4())[:8]}",
            provider_id=candidate.provider.provider_id,
            buyer_id=candidate.buyer.buyer_id,
            match_score=candidate.score,
            status="pending",
            match_reason="; ".join(candidate.reasons),
            provider_approved=False,
            response_received=False,
            followup_count=0
        )
        
        self.match_buffer.append(match)
        self.existing_pairs.add((candidate.provider.provider_id, candidate.buyer.buyer_id))
        
        if len(self.match_buffer) >= self.batch_size:
            self.flush_matches()
    
    def flush_matches(self):
        """Batch insert matches to database"""
        if not self.match_buffer:
            return
        
        try:
            self.db.bulk_save_objects(self.match_buffer)
            self.db.commit()
            self.total_created += len(self.match_buffer)
            
            if self.total_created % 500 == 0:
                print(f"  Progress: {self.total_created} matches created...")
            
            self.match_buffer = []
        except Exception as e:
            print(f"  [ERROR] Batch insert failed: {e}")
            self.db.rollback()
    
    def run_mass_matchmaking(self, min_score_threshold=30):
        """
        Main matchmaking engine
        Strategy: Industry bucketing for O(N) performance instead of O(N^2)
        """
        print("\n" + "=" * 80)
        print(f"MASS MATCHMAKING ENGINE - Threshold: {min_score_threshold}+ points")
        print("=" * 80)
        
        start_time = time.time()
        
        # Load all data
        print("\n[1/4] Loading provider and buyer data...")
        providers = self.db.query(ServiceProvider).filter(
            ServiceProvider.active == True
        ).all()
        
        buyers = self.db.query(BuyerCompany).filter(
            BuyerCompany.active == True
        ).all()
        
        print(f"  Providers: {len(providers)}")
        print(f"  Buyers: {len(buyers)}")
        print(f"  Potential combinations: {len(providers) * len(buyers):,}")
        
        # Strategy: Bucket by industry for efficient matching
        print("\n[2/4] Bucketing by industry...")
        
        buyer_buckets = {}  # industry -> list of buyers
        for buyer in buyers:
            ind = buyer.industry or "unknown"
            if ind not in buyer_buckets:
                buyer_buckets[ind] = []
            buyer_buckets[ind].append(buyer)
        
        provider_buckets = {}  # industry -> list of providers
        for provider in providers:
            if provider.industries:
                for ind in provider.industries:
                    if ind not in provider_buckets:
                        provider_buckets[ind] = []
                    provider_buckets[ind].append(provider)
        
        print(f"  Buyer buckets: {len(buyer_buckets)}")
        print(f"  Provider buckets: {len(provider_buckets)}")
        
        # Match within same industry buckets
        print("\n[3/4] Generating matches...")
        
        candidates_evaluated = 0
        high_quality_matches = 0
        
        # First: Match within same industry (higher quality)
        for industry in set(buyer_buckets.keys()) & set(provider_buckets.keys()):
            industry_buyers = buyer_buckets.get(industry, [])
            industry_providers = provider_buckets.get(industry, [])
            
            print(f"\n  Processing {industry}: {len(industry_providers)} providers, {len(industry_buyers)} buyers")
            
            for provider in industry_providers:
                for buyer in industry_buyers:
                    # Skip if already matched
                    if self.is_duplicate_match(provider.provider_id, buyer.buyer_id):
                        self.skipped += 1
                        continue
                    
                    # Calculate match score
                    score, reasons = self.calculate_match_score(provider, buyer)
                    candidates_evaluated += 1
                    
                    # Only create high-quality matches
                    if score >= min_score_threshold:
                        candidate = MatchCandidate(provider, buyer, score, reasons)
                        self.create_match(candidate)
                        high_quality_matches += 1
        
        # Second: Cross-industry matching for broader coverage (lower threshold)
        print("\n[4/4] Cross-industry matching...")
        
        cross_industry_matches = 0
        for provider in providers[:500]:  # Limit to avoid explosion
            for industry, buyers_in_ind in buyer_buckets.items():
                # Skip if already processed above
                if provider.industries and industry in provider.industries:
                    continue
                
                for buyer in buyers_in_ind[:20]:  # Sample 20 buyers per industry
                    if self.is_duplicate_match(provider.provider_id, buyer.buyer_id):
                        continue
                    
                    score, reasons = self.calculate_match_score(provider, buyer)
                    candidates_evaluated += 1
                    
                    # Lower threshold for cross-industry
                    if score >= 50:
                        candidate = MatchCandidate(provider, buyer, score, reasons)
                        self.create_match(candidate)
                        cross_industry_matches += 1
                        high_quality_matches += 1
        
        # Flush remaining matches
        self.flush_matches()
        
        elapsed = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 80)
        print("MATCHMAKING COMPLETE")
        print("=" * 80)
        
        final_match_count = self.db.query(Match).count()
        
        print(f"""
PERFORMANCE METRICS:
  Time elapsed: {elapsed:.1f} seconds
  Candidates evaluated: {candidates_evaluated:,}
  High-quality matches created: {high_quality_matches:,}
  Duplicates skipped: {self.skipped:,}
  
DATABASE STATE:
  Total matches in DB: {final_match_count:,}
  Providers matched: {len(set(m.provider_id for m in self.db.query(Match).all()))}
  Buyers matched: {len(set(m.buyer_id for m in self.db.query(Match).all()))}
  
MATCH QUALITY DISTRIBUTION:
        """)
        
        # Show score distribution
        score_ranges = [
            (90, 100, "Exceptional"),
            (80, 89, "Excellent"),
            (70, 79, "Very Good"),
            (60, 69, "Good"),
            (50, 59, "Moderate"),
            (30, 49, "Fair")
        ]
        
        for min_s, max_s, label in score_ranges:
            count = self.db.query(Match).filter(
                Match.match_score >= min_s,
                Match.match_score <= max_s
            ).count()
            if count > 0:
                bar = "█" * (count // 50)
                print(f"  {max_s:3d}+ {label:12s}: {count:5,} {bar}")
        
        return final_match_count

def show_top_matches(db, limit=20):
    """Display top scoring matches"""
    print("\n" + "=" * 80)
    print(f"TOP {limit} MATCHES BY SCORE")
    print("=" * 80)
    
    matches = db.query(Match).order_by(Match.match_score.desc()).limit(limit).all()
    
    for i, m in enumerate(matches, 1):
        provider = db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == m.provider_id
        ).first()
        
        buyer = db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id == m.buyer_id
        ).first()
        
        if provider and buyer:
            print(f"\n{i:2d}. {provider.company_name}")
            print(f"    <-> {buyer.company_name}")
            print(f"    Score: {m.match_score} | Status: {m.status}")
            if m.match_reason:
                print(f"    Why: {m.match_reason[:70]}...")

def main():
    print("=" * 80)
    print("MASS MATCHMAKING ENGINE - 2000+ PROVIDERS × 2000+ BUYERS")
    print("=" * 80)
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/outbound")
    engine = create_engine(db_url, pool_size=20)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Current state
        matches_before = db.query(Match).count()
        print(f"\nCurrent matches in database: {matches_before:,}")
        
        # Run mass matchmaking
        engine = MassMatchmakingEngine(db, batch_size=100)
        final_count = engine.run_mass_matchmaking(min_score_threshold=30)
        
        # Show top matches
        show_top_matches(db, limit=20)
        
        print("\n" + "=" * 80)
        print("✓ MASS MATCHMAKING COMPLETE")
        print("=" * 80)
        print(f"\nTotal matches created: {final_count - matches_before:,}")
        print(f"Final database total: {final_count:,}")
        
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
