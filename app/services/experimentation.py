import logging
import random
from typing import Dict, List
from sqlalchemy.orm import Session
from app.models import OutboundMessage, Experiment, ExperimentResult
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ExperimentationLayer:
    """A/B testing system for subjects, messages, CTAs with performance tracking"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_experiment(self, name: str, experiment_type: str, variants: List[Dict], target_segment: str = None, sample_size: int = 100) -> Dict:
        """Create a new A/B experiment"""
        experiment = Experiment(
            experiment_id=f"exp-{str(uuid.uuid4())[:8]}",
            name=name,
            experiment_type=experiment_type,  # subject, message, cta
            variants=variants,
            target_segment=target_segment,
            sample_size=sample_size,
            status="active",
            started_at=datetime.utcnow()
        )
        
        self.db.add(experiment)
        self.db.commit()
        
        logger.info(f"Created experiment {experiment.experiment_id}: {name}")
        
        return {
            "experiment_id": experiment.experiment_id,
            "name": name,
            "experiment_type": experiment_type,
            "variants": variants,
            "status": "active"
        }
    
    def assign_variant(self, experiment_id: str, message_id: str) -> Dict:
        """Assign a variant to a message for the experiment"""
        experiment = self.db.query(Experiment).filter(
            Experiment.experiment_id == experiment_id,
            Experiment.status == "active"
        ).first()
        
        if not experiment:
            return {"error": "Experiment not found or not active"}
        
        # Check if we've reached sample size
        if experiment.total_participants >= experiment.sample_size:
            return {"error": "Experiment sample size reached"}
        
        # Random variant assignment
        variants = experiment.variants
        selected_variant = random.choice(list(variants.keys()))
        
        # Record the assignment
        result = ExperimentResult(
            result_id=f"result-{str(uuid.uuid4())[:8]}",
            experiment_id=experiment_id,
            message_id=message_id,
            variant=selected_variant,
            replied=False,
            converted=False
        )
        
        self.db.add(result)
        
        # Update experiment participant count
        experiment.total_participants += 1
        self.db.commit()
        
        return {
            "variant": selected_variant,
            "variant_content": variants[selected_variant],
            "experiment_id": experiment_id
        }
    
    def record_outcome(self, result_id: str, replied: bool, converted: bool = False):
        """Record outcome for an experiment result"""
        result = self.db.query(ExperimentResult).filter(
            ExperimentResult.result_id == result_id
        ).first()
        
        if result:
            result.replied = replied
            if replied:
                result.replied_at = datetime.utcnow()
            result.converted = converted
            
            # Update experiment stats
            experiment = self.db.query(Experiment).filter(
                Experiment.experiment_id == result.experiment_id
            ).first()
            
            if experiment:
                self._recalculate_experiment_stats(experiment)
            
            self.db.commit()
    
    def _recalculate_experiment_stats(self, experiment: Experiment):
        """Recalculate experiment statistics"""
        results = self.db.query(ExperimentResult).filter(
            ExperimentResult.experiment_id == experiment.experiment_id
        ).all()
        
        variant_stats = {}
        
        for result in results:
            variant = result.variant
            if variant not in variant_stats:
                variant_stats[variant] = {
                    "total": 0,
                    "replies": 0,
                    "conversions": 0
                }
            
            variant_stats[variant]["total"] += 1
            if result.replied:
                variant_stats[variant]["replies"] += 1
            if result.converted:
                variant_stats[variant]["conversions"] += 1
        
        # Calculate reply rates and determine winner
        best_variant = None
        best_reply_rate = 0
        
        for variant, stats in variant_stats.items():
            if stats["total"] > 0:
                reply_rate = (stats["replies"] / stats["total"]) * 100
                if reply_rate > best_reply_rate:
                    best_reply_rate = reply_rate
                    best_variant = variant
        
        if best_variant:
            experiment.winner = best_variant
        
        # Check statistical significance (simplified)
        if experiment.total_participants >= 50:
            experiment.statistical_significance = True
            if experiment.status == "active":
                experiment.status = "completed"
                experiment.completed_at = datetime.utcnow()
    
    def get_experiment_results(self, experiment_id: str) -> Dict:
        """Get results for an experiment"""
        experiment = self.db.query(Experiment).filter(
            Experiment.experiment_id == experiment_id
        ).first()
        
        if not experiment:
            return {"error": "Experiment not found"}
        
        results = self.db.query(ExperimentResult).filter(
            ExperimentResult.experiment_id == experiment_id
        ).all()
        
        variant_stats = {}
        
        for result in results:
            variant = result.variant
            if variant not in variant_stats:
                variant_stats[variant] = {
                    "total": 0,
                    "replies": 0,
                    "conversions": 0,
                    "reply_rate": 0,
                    "conversion_rate": 0
                }
            
            variant_stats[variant]["total"] += 1
            if result.replied:
                variant_stats[variant]["replies"] += 1
            if result.converted:
                variant_stats[variant]["conversions"] += 1
            
            if variant_stats[variant]["total"] > 0:
                variant_stats[variant]["reply_rate"] = (variant_stats[variant]["replies"] / variant_stats[variant]["total"]) * 100
                variant_stats[variant]["conversion_rate"] = (variant_stats[variant]["conversions"] / variant_stats[variant]["total"]) * 100
        
        return {
            "experiment_id": experiment.experiment_id,
            "name": experiment.name,
            "experiment_type": experiment.experiment_type,
            "status": experiment.status,
            "total_participants": experiment.total_participants,
            "statistical_significance": experiment.statistical_significance,
            "winner": experiment.winner,
            "variant_stats": variant_stats,
            "started_at": experiment.started_at.isoformat() if experiment.started_at else None,
            "completed_at": experiment.completed_at.isoformat() if experiment.completed_at else None
        }
    
    def get_active_experiments(self) -> List[Dict]:
        """Get all active experiments"""
        experiments = self.db.query(Experiment).filter(
            Experiment.status == "active"
        ).all()
        
        return [
            {
                "experiment_id": exp.experiment_id,
                "name": exp.name,
                "experiment_type": exp.experiment_type,
                "total_participants": exp.total_participants,
                "sample_size": exp.sample_size
            }
            for exp in experiments
        ]
    
    def pause_experiment(self, experiment_id: str):
        """Pause an active experiment"""
        experiment = self.db.query(Experiment).filter(
            Experiment.experiment_id == experiment_id
        ).first()
        
        if experiment:
            experiment.status = "paused"
            self.db.commit()
            logger.info(f"Paused experiment {experiment_id}")
    
    def resume_experiment(self, experiment_id: str):
        """Resume a paused experiment"""
        experiment = self.db.query(Experiment).filter(
            Experiment.experiment_id == experiment_id
        ).first()
        
        if experiment:
            experiment.status = "active"
            self.db.commit()
            logger.info(f"Resumed experiment {experiment_id}")
    
    def create_subject_experiment(self, name: str, subjects: List[str]) -> Dict:
        """Helper to create a subject A/B test"""
        variants = {f"variant_{i}": subject for i, subject in enumerate(subjects)}
        return self.create_experiment(name, "subject", variants)
    
    def create_cta_experiment(self, name: str, ctas: List[str]) -> Dict:
        """Helper to create a CTA A/B test"""
        variants = {f"variant_{i}": cta for i, cta in enumerate(ctas)}
        return self.create_experiment(name, "cta", variants)
