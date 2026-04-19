"""Auto-Optimizing A/B Testing Service for Subject Lines"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models import OutboundMessage, Reply, Template, Experiment, ExperimentResult
from app.logging_config import logger as app_logger
import random
import math

logger = app_logger


class ABTestingService:
    """Service for auto-optimizing A/B testing of subject lines"""
    
    def __init__(self, db: Session):
        self.db = db
        self.confidence_threshold = 0.95  # 95% confidence
        self.min_sample_size = 50
    
    def create_subject_line_experiment(
        self,
        experiment_name: str,
        subject_variants: List[str],
        target_segment: str = "all"
    ) -> Experiment:
        """Create an A/B test for subject lines"""
        experiment = Experiment(
            experiment_id=f"ab-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            name=experiment_name,
            experiment_type="subject_line",
            variants=subject_variants,
            target_segment=target_segment,
            status="active",
            sample_size=len(subject_variants) * self.min_sample_size
        )
        
        self.db.add(experiment)
        self.db.commit()
        
        logger.info(f"Created A/B test {experiment_id} with {len(subject_variants)} variants")
        return experiment
    
    def assign_variant(self, experiment_id: str) -> str:
        """Assign a variant to a message using weighted random selection"""
        experiment = self.db.query(Experiment).filter(
            Experiment.experiment_id == experiment_id
        ).first()
        
        if not experiment:
            return None
        
        # Get current performance of each variant
        variant_performance = self._get_variant_performance(experiment_id)
        
        # Use Thompson Sampling for variant selection
        variants = experiment.variants
        if not variant_performance:
            # Equal probability if no data yet
            return random.choice(variants)
        
        # Calculate Thompson Sampling weights
        weights = []
        for variant in variants:
            perf = variant_performance.get(variant, {"replies": 0, "sent": 0})
            replies = perf["replies"] + 1  # Beta prior
            sent = perf["sent"] - replies + 1  # Beta prior
            weight = random.betavariate(replies, sent)
            weights.append(weight)
        
        # Select variant with highest weight
        selected_idx = weights.index(max(weights))
        return variants[selected_idx]
    
    def _get_variant_performance(self, experiment_id: str) -> Dict[str, Dict]:
        """Get performance metrics for each variant"""
        results = self.db.query(ExperimentResult).filter(
            ExperimentResult.experiment_id == experiment_id
        ).all()
        
        performance = {}
        for result in results:
            variant = result.variant
            if variant not in performance:
                performance[variant] = {"sent": 0, "replies": 0}
            
            performance[variant]["sent"] += 1
            if result.replied:
                performance[variant]["replies"] += 1
        
        return performance
    
    def record_experiment_result(
        self,
        experiment_id: str,
        message_id: str,
        variant: str,
        replied: bool = False
    ):
        """Record the result of an experiment trial"""
        result = ExperimentResult(
            result_id=f"res-{message_id}",
            experiment_id=experiment_id,
            message_id=message_id,
            variant=variant,
            replied=replied
        )
        
        self.db.add(result)
        self.db.commit()
    
    def calculate_statistical_significance(
        self,
        variant_a: Dict,
        variant_b: Dict
    ) -> Dict:
        """Calculate statistical significance between two variants using Z-test"""
        # Extract data
        n1 = variant_a["sent"]
        x1 = variant_a["replies"]
        p1 = x1 / n1 if n1 > 0 else 0
        
        n2 = variant_b["sent"]
        x2 = variant_b["replies"]
        p2 = x2 / n2 if n2 > 0 else 0
        
        # Pooled proportion
        p_pooled = (x1 + x2) / (n1 + n2) if (n1 + n2) > 0 else 0
        
        # Standard error
        se = math.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
        
        if se == 0:
            return {"significant": False, "p_value": 1.0, "confidence": 0.0}
        
        # Z-score
        z_score = (p1 - p2) / se
        
        # P-value (two-tailed)
        from scipy import stats
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        
        # Confidence level
        confidence = 1 - p_value
        
        # Determine winner
        winner = "A" if p1 > p2 else "B"
        lift = ((p2 - p1) / p1 * 100) if p1 > 0 else 0
        
        return {
            "significant": confidence >= self.confidence_threshold,
            "p_value": p_value,
            "confidence": confidence,
            "winner": winner,
            "lift": lift,
            "rate_a": p1,
            "rate_b": p2
        }
    
    def analyze_experiment(self, experiment_id: str) -> Dict:
        """Analyze experiment results and determine winner"""
        experiment = self.db.query(Experiment).filter(
            Experiment.experiment_id == experiment_id
        ).first()
        
        if not experiment:
            return {"error": "Experiment not found"}
        
        performance = self._get_variant_performance(experiment_id)
        
        # Check if minimum sample size reached
        total_sent = sum(v["sent"] for v in performance.values())
        if total_sent < self.min_sample_size:
            return {
                "status": "insufficient_data",
                "total_sent": total_sent,
                "min_required": self.min_sample_size,
                "message": "Need more data to determine significance"
            }
        
        # Find best variant
        best_variant = None
        best_rate = 0
        
        for variant, metrics in performance.items():
            rate = metrics["replies"] / metrics["sent"] if metrics["sent"] > 0 else 0
            if rate > best_rate:
                best_rate = rate
                best_variant = variant
        
        # Compare with second best
        sorted_variants = sorted(
            performance.items(),
            key=lambda x: x[1]["replies"] / x[1]["sent"] if x[1]["sent"] > 0 else 0,
            reverse=True
        )
        
        if len(sorted_variants) >= 2:
            significance = self.calculate_statistical_significance(
                sorted_variants[0][1],
                sorted_variants[1][1]
            )
        else:
            significance = {"significant": False}
        
        # Update experiment if significant
        if significance.get("significant"):
            experiment.winner = best_variant
            experiment.statistical_significance = True
            experiment.status = "completed"
            experiment.completed_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Experiment {experiment_id} winner: {best_variant}")
        
        return {
            "experiment_id": experiment_id,
            "status": experiment.status,
            "total_sent": total_sent,
            "performance": performance,
            "best_variant": best_variant,
            "best_rate": best_rate,
            "statistical_significance": significance
        }
    
    def auto_optimize_subject_lines(
        self,
        template_id: str,
        current_subject: str
    ) -> Dict:
        """Automatically generate and test new subject line variants"""
        # Generate AI-powered variants
        variants = self._generate_subject_variants(current_subject)
        
        # Create experiment
        experiment = self.create_subject_line_experiment(
            experiment_name=f"Auto-optimize {template_id}",
            subject_variants=variants,
            target_segment="all"
        )
        
        return {
            "experiment_id": experiment.experiment_id,
            "variants": variants,
            "current_subject": current_subject,
            "status": "active"
        }
    
    def _generate_subject_variants(self, base_subject: str) -> List[str]:
        """Generate subject line variants using AI patterns"""
        variants = [base_subject]  # Include original
        
        # Pattern 1: Add urgency
        if "urgent" not in base_subject.lower():
            variants.append(f"Quick: {base_subject}")
        
        # Pattern 2: Personalization
        if "{{company}}" not in base_subject:
            variants.append(base_subject.replace("your", "{{company}}'s"))
        
        # Pattern 3: Question format
        if not base_subject.strip().endswith("?"):
            variants.append(f"{base_subject}?")
        
        # Pattern 4: Benefit-focused
        benefit_words = ["boost", "increase", "improve", "accelerate", "scale"]
        for word in benefit_words:
            if word not in base_subject.lower():
                variants.append(f"{word} your results: {base_subject}")
                break
        
        # Pattern 5: Short and punchy
        if len(base_subject) > 50:
            short_version = base_subject[:40] + "..."
            variants.append(short_version)
        
        return variants[:5]  # Limit to 5 variants
    
    def get_recommended_subject(self, template_id: str) -> Optional[str]:
        """Get the statistically best subject line for a template"""
        # Check for completed experiments
        completed_experiments = self.db.query(Experiment).filter(
            Experiment.experiment_type == "subject_line",
            Experiment.status == "completed",
            Experiment.statistical_significance == True
        ).order_by(Experiment.completed_at.desc()).first()
        
        if completed_experiments and completed_experiments.winner:
            return completed_experiments.winner
        
        # Fall back to template default
        template = self.db.query(Template).filter(
            Template.template_id == template_id
        ).first()
        
        if template:
            return template.subject_template
        
        return None
    
    def batch_optimize_templates(self, limit: int = 10) -> Dict:
        """Run batch optimization on multiple templates"""
        templates = self.db.query(Template).filter(
            Template.is_active == True
        ).limit(limit).all()
        
        results = {
            "total_templates": len(templates),
            "experiments_created": 0,
            "results": []
        }
        
        for template in templates:
            # Check if active experiment exists
            existing = self.db.query(Experiment).filter(
                Experiment.experiment_type == "subject_line",
                Experiment.status == "active"
            ).first()
            
            if not existing:
                optimization = self.auto_optimize_subject_lines(
                    template_id=template.template_id,
                    current_subject=template.subject_template
                )
                results["experiments_created"] += 1
                results["results"].append({
                    "template_id": template.template_id,
                    "experiment_id": optimization["experiment_id"],
                    "variants": optimization["variants"]
                })
        
        return results
    
    def get_experiment_dashboard(self) -> Dict:
        """Get overview of all experiments"""
        active = self.db.query(Experiment).filter(
            Experiment.status == "active"
        ).count()
        
        completed = self.db.query(Experiment).filter(
            Experiment.status == "completed"
        ).count()
        
        significant = self.db.query(Experiment).filter(
            Experiment.status == "completed",
            Experiment.statistical_significance == True
        ).count()
        
        # Get recent experiments
        recent = self.db.query(Experiment).order_by(
            Experiment.started_at.desc()
        ).limit(5).all()
        
        recent_data = []
        for exp in recent:
            perf = self._get_variant_performance(exp.experiment_id)
            recent_data.append({
                "experiment_id": exp.experiment_id,
                "name": exp.name,
                "status": exp.status,
                "variants_count": len(exp.variants),
                "total_sent": sum(v["sent"] for v in perf.values()),
                "winner": exp.winner
            })
        
        return {
            "summary": {
                "active": active,
                "completed": completed,
                "significant": significant
            },
            "recent_experiments": recent_data
        }
