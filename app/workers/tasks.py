from celery import shared_task
from app.database import SessionLocal
from app.services.lead_loader import LeadLoader
from app.services.batch_builder import BatchBuilder
from app.services.gmail_sender import GmailSender
from app.classifiers.reply_classifier import ReplyClassifier
from app.workers.celery_app import celery_app
from app.models import Match
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def import_leads_task(self, json_path: str = "data/leads.json"):
    """Import leads from JSON file into PostgreSQL"""
    db = SessionLocal()
    try:
        loader = LeadLoader(db)
        results = loader.load_from_json(json_path)
        logger.info(f"Imported leads: {results}")
        return results
    except Exception as e:
        logger.error(f"Failed to import leads: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def generate_batch_task(self, from_email: str, max_leads: int = 50, min_fit_score: int = 7):
    """Generate outbound batch from eligible leads"""
    db = SessionLocal()
    try:
        builder = BatchBuilder(db)
        results = builder.build_batch(
            from_email=from_email,
            max_leads=max_leads,
            min_fit_score=min_fit_score
        )
        logger.info(f"Generated batch: {results}")
        return results
    except Exception as e:
        logger.error(f"Failed to generate batch: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def send_message_task(self, message_id: str):
    """Send a single email message"""
    db = SessionLocal()
    try:
        sender = GmailSender(db)
        result = sender.send_message(message_id)
        logger.info(f"Sent message {message_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send message {message_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def send_batch_task(self, run_id: str, rate_limit: int = 10):
    """Send all messages in a batch"""
    db = SessionLocal()
    try:
        sender = GmailSender(db)
        results = sender.send_batch(run_id, rate_limit=rate_limit)
        logger.info(f"Sent batch {run_id}: {results}")
        return results
    except Exception as e:
        logger.error(f"Failed to send batch {run_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def classify_reply_task(self, reply_id: str):
    """Classify a reply and update lead state"""
    db = SessionLocal()
    try:
        classifier = ReplyClassifier(db)
        result = classifier.classify_and_process(reply_id)
        logger.info(f"Classified reply {reply_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to classify reply {reply_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task
def schedule_followups_task():
    """Schedule follow-ups for leads that need them"""
    db = SessionLocal()
    try:
        from app.services.followup_scheduler import FollowupScheduler
        scheduler = FollowupScheduler(db)
        results = scheduler.schedule_followups()
        logger.info(f"Scheduled follow-ups: {results}")
        return results
    except Exception as e:
        logger.error(f"Failed to schedule follow-ups: {e}")
    finally:
        db.close()


@celery_app.task
def daily_batch_generation_task():
    """Daily task to generate and send outbound batches"""
    db = SessionLocal()
    try:
        # Import leads
        loader = LeadLoader(db)
        import_results = loader.load_from_json("data/leads.json")
        
        # Generate batch
        builder = BatchBuilder(db)
        batch_results = builder.build_batch(from_email="your-email@gmail.com")
        
        # Send batch
        if batch_results["messages_created"] > 0:
            run_id = batch_results["run_id"]
            send_batch_task.delay(run_id)
        
        logger.info(f"Daily batch generation completed: {import_results}, {batch_results}")
        return {"import": import_results, "batch": batch_results}
    except Exception as e:
        logger.error(f"Daily batch generation failed: {e}")
    finally:
        db.close()


# Advanced Workflow Tasks

@celery_app.task
def daily_qualification_scoring_task():
    """Daily task to score all leads using the qualification engine"""
    db = SessionLocal()
    try:
        from app.services.lead_qualification import LeadQualificationEngine
        engine = LeadQualificationEngine(db)
        results = engine.batch_score_leads()
        logger.info(f"Daily qualification scoring completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Daily qualification scoring failed: {e}")
    finally:
        db.close()


@celery_app.task
def hourly_deliverability_reset_task():
    """Hourly task to reset hourly send counts"""
    db = SessionLocal()
    try:
        from app.services.deliverability import DeliverabilitySystem
        deliverability = DeliverabilitySystem(db)
        deliverability.reset_hourly_counts()
        logger.info("Hourly deliverability reset completed")
        return {"status": "completed"}
    except Exception as e:
        logger.error(f"Hourly deliverability reset failed: {e}")
    finally:
        db.close()


@celery_app.task
def daily_deliverability_reset_task():
    """Daily task to reset daily send counts and check warmup progress"""
    db = SessionLocal()
    try:
        from app.services.deliverability import DeliverabilitySystem
        deliverability = DeliverabilitySystem(db)
        deliverability.reset_daily_counts()
        logger.info("Daily deliverability reset completed")
        return {"status": "completed"}
    except Exception as e:
        logger.error(f"Daily deliverability reset failed: {e}")
    finally:
        db.close()


@celery_app.task
def pipeline_monitoring_task():
    """Task to monitor pipeline and identify stuck leads"""
    db = SessionLocal()
    try:
        from app.services.pipeline_state_machine import PipelineStateMachine
        pipeline = PipelineStateMachine(db)
        
        # Get stuck leads
        stuck_leads = pipeline.get_stuck_leads("CONTACTED", days=7)
        logger.info(f"Found {len(stuck_leads)} stuck leads in CONTACTED state")
        
        return {"stuck_leads": stuck_leads}
    except Exception as e:
        logger.error(f"Pipeline monitoring failed: {e}")
    finally:
        db.close()


@celery_app.task
def feedback_learning_task():
    """Task to calculate trends and update performance metrics"""
    db = SessionLocal()
    try:
        from app.services.feedback_learning import FeedbackLearningLoop
        learning = FeedbackLearningLoop(db)
        learning.calculate_trends(days=7)
        logger.info("Feedback learning task completed")
        return {"status": "completed"}
    except Exception as e:
        logger.error(f"Feedback learning task failed: {e}")
    finally:
        db.close()


@celery_app.task
def auto_escalation_task():
    """Task to auto-escalate high-value leads"""
    db = SessionLocal()
    try:
        from app.services.human_escalation import HumanEscalationLayer
        escalation = HumanEscalationLayer(db)
        results = escalation.auto_escalate_high_value_leads(min_priority_score=85)
        logger.info(f"Auto-escalation task completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Auto-escalation task failed: {e}")
    finally:
        db.close()


@celery_app.task
def send_due_followups_task():
    """Task to send follow-ups that are due"""
    db = SessionLocal()
    try:
        from app.services.followup_scheduler import FollowupScheduler
        scheduler = FollowupScheduler(db)
        results = scheduler.send_due_followups()
        logger.info(f"Send due follow-ups task completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Send due follow-ups task failed: {e}")
    finally:
        db.close()


# Billionaire CEO Automation Tasks

@celery_app.task
def automation_cycle_task(from_email: str):
    """Run complete daily automation cycle"""
    db = SessionLocal()
    try:
        from app.services.tiered_automation import TieredAutomationService
        
        service = TieredAutomationService(db)
        results = service.run_daily_automation_cycle(from_email)
        logger.info(f"Automation cycle completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Automation cycle failed: {e}")
    finally:
        db.close()


@celery_app.task
def lead_ingestion_crunchbase_task(query: str, limit: int = 100):
    """Ingest leads from Crunchbase API"""
    db = SessionLocal()
    try:
        from app.services.lead_ingestion import LeadIngestionService
        import asyncio
        
        service = LeadIngestionService(db)
        results = asyncio.run(service.ingest_from_crunchbase(query, limit=limit))
        logger.info(f"Crunchbase ingestion completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Crunchbase ingestion failed: {e}")
    finally:
        db.close()


@celery_app.task
def signal_detection_batch_task(company_names: list):
    """Detect signals for multiple companies"""
    db = SessionLocal()
    try:
        from app.services.signal_detection import SignalDetectionService
        import asyncio
        
        service = SignalDetectionService(db)
        results = asyncio.run(service.monitor_signals_batch(company_names))
        logger.info(f"Signal detection batch completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Signal detection batch failed: {e}")
    finally:
        db.close()


@celery_app.task
def auto_suppress_bounces_task(bounce_threshold: int = 3):
    """Automatically suppress bouncing emails"""
    db = SessionLocal()
    try:
        from app.services.safeguards import SafeguardsService
        service = SafeguardsService(db)
        results = service.auto_suppress_bounces(bounce_threshold)
        logger.info(f"Auto-suppress bounces completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Auto-suppress bounces failed: {e}")
    finally:
        db.close()


@celery_app.task
def auto_suppress_unsubscribes_task():
    """Automatically suppress unsubscribe requests"""
    db = SessionLocal()
    try:
        from app.services.safeguards import SafeguardsService
        service = SafeguardsService(db)
        results = service.auto_suppress_unsubscribes()
        logger.info(f"Auto-suppress unsubscribes completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Auto-suppress unsubscribes failed: {e}")
    finally:
        db.close()


@celery_app.task
def batch_optimize_templates_task(limit: int = 10):
    """Batch optimize templates with A/B testing"""
    db = SessionLocal()
    try:
        from app.services.ab_testing import ABTestingService
        service = ABTestingService(db)
        results = service.batch_optimize_templates(limit)
        logger.info(f"Batch template optimization completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Batch template optimization failed: {e}")
    finally:
        db.close()


@celery_app.task
def tier_promotion_task():
    """Auto-promote Tier 2 leads that have improved to Tier 1"""
    db = SessionLocal()
    try:
        from app.services.tiered_automation import TieredAutomationService
        service = TieredAutomationService(db)
        results = service.auto_promote_tier_2_to_tier_1()
        logger.info(f"Tier promotion completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Tier promotion failed: {e}")
    finally:
        db.close()


@celery_app.task
def ai_personalize_messages_task(run_id: str):
    """AI-generate personalized content for all messages in a batch"""
    db = SessionLocal()
    try:
        from app.services.ai_email_generator import AIEmailGenerator
        from app.models import OutboundMessage
        
        generator = AIEmailGenerator(db)
        messages = db.query(OutboundMessage).filter(
            OutboundMessage.run_id == run_id
        ).all()
        
        updated = 0
        for message in messages:
            if generator.update_outbound_message_with_ai(message.message_id):
                updated += 1
        
        logger.info(f"AI personalized {updated} messages in batch {run_id}")
        return {"run_id": run_id, "personalized": updated}
    except Exception as e:
        logger.error(f"AI personalization failed: {e}")
    finally:
        db.close()


@celery_app.task
def automated_followup_check_task():
    """Check and send automated follow-ups every 4 hours"""
    db = SessionLocal()
    try:
        from app.services.followup_automation import FollowUpAutomation
        
        automation = FollowUpAutomation(db)
        results = automation.run_followup_check()
        
        logger.info(f"Follow-up check: {results['followups_sent']} sent, {results['suppressed']} suppressed")
        return results
    except Exception as e:
        logger.error(f"Follow-up automation failed: {e}")
    finally:
        db.close()


@celery_app.task
def process_new_reply_task(reply_id: str):
    """Process a new reply and take automated action"""
    db = SessionLocal()
    try:
        from app.services.followup_automation import ReplyAutoResponder
        
        responder = ReplyAutoResponder(db)
        result = responder.process_new_reply(reply_id)
        
        logger.info(f"Reply {reply_id} processed: {result}")
        return result
    except Exception as e:
        logger.error(f"Reply processing failed: {e}")
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def autonomous_discovery_task(self):
    """
    Autonomous Lead Discovery - Zero Touch Lead Generation
    
    This task runs continuously to:
    1. Discover leads from free data sources (GitHub, NewsAPI, Product Hunt, HN, job boards)
    2. Enrich with Gemini AI (free tier: 60 req/min)
    3. Auto-qualify with intelligent scoring
    4. Ingest qualified leads into pipeline
    
    Runs every 6 hours via Celery Beat
    """
    import asyncio
    from app.services.autonomous_discovery import AutonomousDiscoveryEngine
    from app.config import settings
    
    db = SessionLocal()
    try:
        # Check for required API key
        if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not configured - autonomous discovery disabled")
            return {"status": "disabled", "reason": "GEMINI_API_KEY not set"}
        
        # Initialize discovery engine
        engine = AutonomousDiscoveryEngine(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY,
            newsapi_key=getattr(settings, 'NEWSAPI_KEY', None)
        )
        
        # Run discovery cycle
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(engine.run_discovery_cycle())
        finally:
            loop.run_until_complete(engine.close())
            loop.close()
        
        logger.info(f"Autonomous discovery complete: {results['ingested']} leads ingested from {results['discovered']} discovered")
        
        # If we discovered leads, trigger batch generation
        if results['ingested'] > 0:
            logger.info(f"New leads discovered - triggering batch generation in 5 minutes")
            daily_batch_generation_task.apply_async(countdown=300)
        
        return results
        
    except Exception as e:
        logger.error(f"Autonomous discovery failed: {e}")
        # Retry in 1 hour
        raise self.retry(exc=e, countdown=3600)
    finally:
        db.close()


@celery_app.task
def discovery_analytics_task():
    """Analyze discovery performance and optimize sources"""
    db = SessionLocal()
    try:
        from app.services.autonomous_discovery import AutonomousDiscoveryEngine
        from app.config import settings
        
        if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
            return {"status": "disabled"}
        
        engine = AutonomousDiscoveryEngine(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY,
            newsapi_key=getattr(settings, 'NEWSAPI_KEY', None)
        )
        
        analytics = engine.get_discovery_analytics()
        
        logger.info(f"Discovery analytics: {analytics}")
        return analytics
        
    except Exception as e:
        logger.error(f"Discovery analytics failed: {e}")
    finally:
        db.close()


# ==========================================
# B2B MATCHMAKING PLATFORM TASKS
# ==========================================

@celery_app.task
def auto_match_all_task(min_score: int = 70, limit_per_buyer: int = 3):
    """
    Automatically create matches for all active buyers
    
    Runs daily to match buyers with relevant service providers
    """
    db = SessionLocal()
    try:
        from app.services.matchmaking_engine import MatchmakingEngine
        
        engine = MatchmakingEngine(db)
        results = engine.auto_match_all(min_score=min_score, limit_per_buyer=limit_per_buyer)
        
        logger.info(f"Auto-match completed: {results['matches_created']} matches created for {results['total_buyers']} buyers")
        return results
    except Exception as e:
        logger.error(f"Auto-match failed: {e}")
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def send_match_intro_task(self, match_id: str, from_email: str = None):
    """
    Send introduction email for a specific match
    
    Retries up to 3 times if sending fails
    """
    db = SessionLocal()
    try:
        from app.services.intro_generator import IntroGenerator
        
        generator = IntroGenerator(db)
        result = generator.send_intro(match_id, from_email)
        
        if result and "error" in result:
            logger.warning(f"Intro send failed for match {match_id}: {result['error']}")
            raise self.retry(exc=Exception(result["error"]), countdown=300)
        
        logger.info(f"Intro sent for match {match_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to send intro for match {match_id}: {e}")
        raise self.retry(exc=e, countdown=300)
    finally:
        db.close()


@celery_app.task
def send_batch_intros_task(provider_id: str = None, max_intros: int = 10):
    """
    Send introduction emails for all approved matches in batch
    
    Can be scoped to a specific provider or run for all
    """
    db = SessionLocal()
    try:
        from app.services.intro_generator import IntroGenerator
        
        generator = IntroGenerator(db)
        results = generator.send_batch_intros(provider_id, max_intros)
        
        logger.info(f"Batch intros sent: {results['sent']} sent, {results['failed']} failed")
        return results
    except Exception as e:
        logger.error(f"Batch intro sending failed: {e}")
    finally:
        db.close()


@celery_app.task
def reset_provider_usage_counters_task():
    """
    Reset monthly usage counters for all active subscriptions
    
    Runs at the start of each month
    """
    db = SessionLocal()
    try:
        from app.services.provider_management import ProviderManagementService
        
        service = ProviderManagementService(db)
        service.reset_usage_counters()
        
        logger.info("Provider usage counters reset completed")
        return {"status": "completed"}
    except Exception as e:
        logger.error(f"Usage counter reset failed: {e}")
    finally:
        db.close()


@celery_app.task
def calculate_platform_revenue_summary_task():
    """
    Calculate and save daily revenue summary
    
    Runs daily to track platform performance
    """
    db = SessionLocal()
    try:
        from app.services.platform_billing import PlatformBillingService
        from datetime import datetime, timedelta
        
        service = PlatformBillingService(db)
        
        # Save yesterday's summary
        yesterday = datetime.utcnow() - timedelta(days=1)
        summary = service.save_revenue_summary("daily", yesterday)
        
        logger.info(f"Daily revenue summary saved: ${summary.total_revenue / 100:.2f}")
        return {
            "status": "completed",
            "revenue": summary.total_revenue / 100,
            "date": yesterday.isoformat()
        }
    except Exception as e:
        logger.error(f"Revenue summary calculation failed: {e}")
    finally:
        db.close()


@celery_app.task
def monthly_revenue_report_task():
    """
    Generate monthly revenue report
    
    Runs on the 1st of each month
    """
    db = SessionLocal()
    try:
        from app.services.platform_billing import PlatformBillingService
        from datetime import datetime
        
        service = PlatformBillingService(db)
        
        # Save last month's summary
        now = datetime.utcnow()
        if now.month == 1:
            last_month = now.replace(year=now.year - 1, month=12, day=1)
        else:
            last_month = now.replace(month=now.month - 1, day=1)
        
        summary = service.save_revenue_summary("monthly", last_month)
        
        logger.info(f"Monthly revenue report: ${summary.total_revenue / 100:.2f}")
        return {
            "status": "completed",
            "month": last_month.strftime("%Y-%m"),
            "revenue": summary.total_revenue / 100,
            "active_providers": summary.active_providers,
            "deals_closed": summary.deals_closed
        }
    except Exception as e:
        logger.error(f"Monthly revenue report failed: {e}")
    finally:
        db.close()


@celery_app.task
def matchmaking_platform_automation_task():
    """
    Complete platform automation cycle
    
    Combines match creation and intro sending in one task
    Runs every few hours during business hours
    """
    db = SessionLocal()
    try:
        from app.services.matchmaking_engine import MatchmakingEngine
        from app.services.intro_generator import IntroGenerator
        from app.models import Match
        
        results = {
            "matches_created": 0,
            "intros_sent": 0,
            "errors": []
        }
        
        # Step 1: Create new matches
        engine = MatchmakingEngine(db)
        match_results = engine.auto_match_all(min_score=70, limit_per_buyer=2)
        results["matches_created"] = match_results.get("matches_created", 0)
        
        # Step 2: Send intros for newly approved matches
        generator = IntroGenerator(db)
        
        approved_matches = db.query(Match).filter(
            Match.status == "approved"
        ).limit(20).all()
        
        for match in approved_matches:
            try:
                result = generator.send_intro(match.match_id)
                if result and "error" not in result:
                    results["intros_sent"] += 1
            except Exception as e:
                results["errors"].append(f"Match {match.match_id}: {str(e)}")
        
        logger.info(f"Platform automation: {results['matches_created']} matches, {results['intros_sent']} intros")
        return results
    except Exception as e:
        logger.error(f"Platform automation failed: {e}")
    finally:
        db.close()


@celery_app.task
def import_leads_as_buyers_task(leads_json_path: str = "data/leads.json"):
    """
    Import existing leads as buyer companies
    
    Useful for migrating from direct sales to platform model
    """
    db = SessionLocal()
    try:
        import json
        from app.services.buyer_management import BuyerManagementService
        from app.models import Lead
        
        service = BuyerManagementService(db)
        
        # Load leads from JSON
        with open(leads_json_path, 'r') as f:
            leads_data = json.load(f)
        
        created_buyers = []
        for lead_data in leads_data[:50]:  # Limit to 50 per batch
            try:
                buyer = service.import_from_lead(
                    lead_id=lead_data.get("lead_id"),
                    requirements=["general_services"],
                    timeline="exploring"
                )
                if buyer:
                    created_buyers.append(buyer.buyer_id)
            except Exception as e:
                logger.warning(f"Failed to import lead {lead_data.get('lead_id')}: {e}")
        
        logger.info(f"Imported {len(created_buyers)} leads as buyers")
        return {"created": len(created_buyers), "buyer_ids": created_buyers}
    except Exception as e:
        logger.error(f"Import leads as buyers failed: {e}")
    finally:
        db.close()


@celery_app.task
def notify_providers_of_new_matches_task():
    """
    Notify providers about new pending matches
    
    Could integrate with email/Slack notifications
    """
    db = SessionLocal()
    try:
        from app.models import Match, ServiceProvider
        from sqlalchemy import func
        
        # Find providers with new pending matches
        pending_by_provider = db.query(
            Match.provider_id,
            func.count(Match.id).label('pending_count')
        ).filter(
            Match.status == 'pending'
        ).group_by(
            Match.provider_id
        ).all()
        
        notifications = []
        for provider_id, count in pending_by_provider:
            provider = db.query(ServiceProvider).filter(
                ServiceProvider.provider_id == provider_id
            ).first()
            
            if provider:
                notifications.append({
                    "provider_id": provider_id,
                    "provider_email": provider.contact_email,
                    "pending_matches": count
                })
                
                # Here you would send actual notification
                logger.info(f"Would notify {provider.contact_email} about {count} pending matches")
        
        return {
            "status": "completed",
            "providers_notified": len(notifications),
            "notifications": notifications
        }
    except Exception as e:
        logger.error(f"Provider notification failed: {e}")
    finally:
        db.close()


# ==========================================
# AUTOMATED B2B OUTBOUND WORKFLOW TASKS
# ==========================================

@celery_app.task(bind=True, max_retries=3)
def discover_providers_task(self, tech_stack: list = None, industries: list = None, limit: int = 50):
    """Automated provider discovery via GitHub"""
    from app.services.prospect_discovery import ProspectDiscoveryService
    
    db = SessionLocal()
    try:
        service = ProspectDiscoveryService()
        
        tech_stack = tech_stack or ["react", "kubernetes", "python"]
        industries = industries or ["SaaS", "Fintech"]
        
        providers = service.discover_providers(
            tech_stack=tech_stack,
            industries=industries,
            min_stars=50,
            limit=limit
        )
        
        logger.info(f"Discovered {len(providers)} providers")
        return {"status": "completed", "count": len(providers), "providers": providers}
    except Exception as e:
        logger.error(f"Provider discovery failed: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def discover_buyers_task(self, industries: list = None, funding_stage: str = "series_b", limit: int = 50):
    """Automated buyer discovery via Crunchbase/GitHub"""
    from app.services.prospect_discovery import ProspectDiscoveryService
    
    db = SessionLocal()
    try:
        service = ProspectDiscoveryService()
        
        industries = industries or ["SaaS", "Fintech", "Healthcare"]
        
        buyers = service.discover_buyers(
            industries=industries,
            funding_stage=funding_stage,
            limit=limit
        )
        
        logger.info(f"Discovered {len(buyers)} buyers")
        return {"status": "completed", "count": len(buyers), "buyers": buyers}
    except Exception as e:
        logger.error(f"Buyer discovery failed: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def enrich_prospects_task(self, prospect_ids: list = None):
    """Automated prospect enrichment via GitHub, Crunchbase, Gemini"""
    from app.services.lead_enrichment_pipeline import LeadEnrichmentPipeline
    from app.database import SessionLocal
    from app.models import ServiceProvider, BuyerCompany
    
    db = SessionLocal()
    try:
        pipeline = LeadEnrichmentPipeline()
        
        # If no specific IDs, enrich all recent prospects
        if not prospect_ids:
            providers = db.query(ServiceProvider).filter(
                ServiceProvider.enriched_at.is_(None)
            ).limit(50).all()
            buyers = db.query(BuyerCompany).filter(
                BuyerCompany.enriched_at.is_(None)
            ).limit(50).all()
            
            prospects = []
            for p in providers:
                prospects.append({
                    "company_name": p.company_name,
                    "website": p.website,
                    "description": p.description,
                    "repository": p.github_repo
                })
            for b in buyers:
                prospects.append({
                    "company_name": b.company_name,
                    "website": b.website,
                    "description": b.description,
                    "repository": b.github_repo
                })
        else:
            prospects = [{"prospect_id": pid} for pid in prospect_ids]
        
        enriched = pipeline.batch_enrich_leads(prospects)
        
        logger.info(f"Enriched {len(enriched)} prospects")
        return {"status": "completed", "count": len(enriched), "prospects": enriched}
    except Exception as e:
        logger.error(f"Prospect enrichment failed: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def score_prospects_task(self, prospect_ids: list = None, min_score: int = 60):
    """Automated prospect scoring"""
    from app.services.prospect_scoring import ProspectScoringService
    from app.database import SessionLocal
    from app.models import ServiceProvider, BuyerCompany
    
    db = SessionLocal()
    try:
        service = ProspectScoringService()
        
        # Get prospects to score
        providers = db.query(ServiceProvider).filter(
            ServiceProvider.score_data.is_(None)
        ).limit(100).all()
        
        prospects = []
        for p in providers:
            prospects.append({
                "company_name": p.company_name,
                "industry": p.industries[0] if p.industries else "SaaS",
                "tech_stack": p.services,
                "employee_count": 100,
                "funding_signals": {},
                "signals": [],
                "value_signals": {}
            })
        
        ranked = service.rank_prospects(prospects, limit=100)
        top = service.get_top_prospects(prospects, min_score=min_score, limit=50)
        
        logger.info(f"Scored {len(ranked)} prospects, {len(top)} above threshold")
        return {"status": "completed", "ranked_count": len(ranked), "top_count": len(top), "top_prospects": top}
    except Exception as e:
        logger.error(f"Prospect scoring failed: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def match_providers_to_buyers_task(self):
    """Automated provider-buyer matching"""
    from app.services.matchmaking_engine import MatchmakingEngine
    from app.database import SessionLocal
    from app.models import ServiceProvider, BuyerCompany
    
    db = SessionLocal()
    try:
        engine = MatchmakingEngine(db)
        
        # Get top providers and buyers
        providers = db.query(ServiceProvider).filter(
            ServiceProvider.active == True,
            ServiceProvider.score_data.isnot(None)
        ).limit(50).all()
        
        buyers = db.query(BuyerCompany).filter(
            BuyerCompany.active == True,
            BuyerCompany.verified == True
        ).limit(50).all()
        
        matches_created = 0
        for provider in providers:
            for buyer in buyers:
                try:
                    # Check if match already exists
                    existing = db.query(Match).filter(
                        Match.provider_id == provider.provider_id,
                        Match.buyer_id == buyer.buyer_id
                    ).first()
                    
                    if not existing:
                        match = engine.create_match(
                            provider.provider_id,
                            buyer.buyer_id,
                            auto_approve=False
                        )
                        matches_created += 1
                except Exception as e:
                    logger.warning(f"Failed to create match: {e}")
                    continue
        
        db.commit()
        logger.info(f"Created {matches_created} new matches")
        return {"status": "completed", "matches_created": matches_created}
    except Exception as e:
        logger.error(f"Matching failed: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def send_outreach_sequence_task(self, match_id: str):
    """Send automated outreach sequence for a match"""
    from app.services.outbound_outreach import OutboundOutreachService
    from app.database import SessionLocal
    from app.models import Match, ServiceProvider, BuyerCompany
    
    db = SessionLocal()
    try:
        service = OutboundOutreachService()
        
        match = db.query(Match).filter(Match.match_id == match_id).first()
        if not match:
            logger.error(f"Match not found: {match_id}")
            return {"status": "error", "message": "Match not found"}
        
        provider = db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == match.provider_id
        ).first()
        buyer = db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id == match.buyer_id
        ).first()
        
        if not provider or not buyer:
            logger.error(f"Provider or buyer not found for match {match_id}")
            return {"status": "error", "message": "Provider or buyer not found"}
        
        # Generate and send intro to buyer
        provider_dict = {
            "company_name": provider.company_name,
            "services": provider.services,
            "case_studies": provider.case_studies,
            "contact_email": provider.contact_email
        }
        
        buyer_dict = {
            "company_name": buyer.company_name,
            "decision_maker_email": buyer.decision_maker_email,
            "signals": [],
            "funding_signals": {},
            "tech_stack": buyer.requirements
        }
        
        # Send intro
        result = service.send_outreach(
            prospect=buyer_dict,
            provider=provider_dict,
            template_type="intro",
            channel="email"
        )
        
        # Update match status
        match.status = "intro_sent"
        match.intro_sent_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Sent outreach for match {match_id}: {result.get('status')}")
        return {"status": "completed", "match_id": match_id, "outreach_result": result}
    except Exception as e:
        logger.error(f"Outreach failed for match {match_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def track_responses_task(self):
    """Track email responses (opens, clicks, replies)"""
    from app.integrations.gmail_thread_fetcher import GmailThreadFetcher
    from app.database import SessionLocal
    from app.models import Match
    
    db = SessionLocal()
    try:
        # Get matches with sent intros
        matches = db.query(Match).filter(
            Match.status == "intro_sent",
            Match.intro_sent_at > datetime.utcnow() - timedelta(days=7)
        ).all()
        
        responses_tracked = 0
        for match in matches:
            try:
                # Check for replies via Gmail API (if configured)
                # This would integrate with GmailThreadFetcher
                # For now, just update status if reply detected
                match.replies_checked_at = datetime.utcnow()
                responses_tracked += 1
            except Exception as e:
                logger.warning(f"Failed to track response for match {match.match_id}: {e}")
                continue
        
        db.commit()
        logger.info(f"Tracked responses for {responses_tracked} matches")
        return {"status": "completed", "responses_tracked": responses_tracked}
    except Exception as e:
        logger.error(f"Response tracking failed: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def schedule_meeting_task(self, match_id: str):
    """Schedule meeting for interested prospect"""
    from app.services.transactional_billing import TransactionalBillingService
    from app.database import SessionLocal
    from app.models import Match
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    try:
        match = db.query(Match).filter(Match.match_id == match_id).first()
        if not match:
            return {"status": "error", "message": "Match not found"}
        
        # Update match to meeting booked
        match.status = "meeting_booked"
        match.meeting_booked_at = datetime.utcnow()
        match.meeting_date = datetime.utcnow() + timedelta(days=7)
        
        # Record meeting fee
        billing_service = TransactionalBillingService()
        billing = billing_service.record_meeting_fee(
            prospect_id=match.buyer_id,
            provider_id=match.provider_id
        )
        
        db.commit()
        logger.info(f"Scheduled meeting for match {match_id}, billing: {billing.billing_id}")
        return {"status": "completed", "match_id": match_id, "billing_id": billing.billing_id}
    except Exception as e:
        logger.error(f"Meeting scheduling failed: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def track_deals_and_invoice_task(self):
    """Track closed deals and generate invoices"""
    from app.services.transactional_billing import TransactionalBillingService
    from app.database import SessionLocal
    from app.models import Match, ProviderBilling
    
    db = SessionLocal()
    try:
        billing_service = TransactionalBillingService()
        
        # Find matches with closed deals but no success fee billed
        matches = db.query(Match).filter(
            Match.status == "closed_won",
            Match.deal_value > 0,
            Match.deal_closed_at.isnot(None)
        ).all()
        
        invoices_generated = 0
        for match in matches:
            # Check if success fee already billed
            existing_billing = db.query(ProviderBilling).filter(
                ProviderBilling.match_id == match.match_id,
                ProviderBilling.charge_type == "success_fee"
            ).first()
            
            if not existing_billing:
                # Record success fee (5%)
                billing = billing_service.record_success_fee(
                    prospect_id=match.buyer_id,
                    provider_id=match.provider_id,
                    deal_value_cents=match.deal_value,
                    percentage=5.0
                )
                invoices_generated += 1
                logger.info(f"Generated success fee for match {match.match_id}: ${billing.amount/100}")
        
        db.commit()
        logger.info(f"Generated {invoices_generated} success fee invoices")
        return {"status": "completed", "invoices_generated": invoices_generated}
    except Exception as e:
        logger.error(f"Deal tracking failed: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def full_automation_cycle_task(self):
    """Run complete automation cycle (orchestrator task)"""
    from celery import chain
    
    logger.info("Starting full automation cycle")
    
    # Chain all tasks in sequence
    workflow = chain(
        discover_providers_task.s(),
        discover_buyers_task.s(),
        enrich_prospects_task.s(),
        score_prospects_task.s(),
        match_providers_to_buyers_task.s(),
        send_outreach_sequence_task.s(),  # This would need to iterate over matches
    )
    
    result = workflow.apply_async()
    
    logger.info(f"Full automation cycle started: {result.id}")
    return {"status": "completed", "workflow_id": result.id}


# ============================================================================
# B2B Matchmaking Platform Tasks
# ============================================================================

@celery_app.task(bind=True, max_retries=3)
def run_b2b_buyer_discovery_task(self):
    """
    Run B2B buyer discovery task
    
    Discovers buyers from free sources (GitHub, NewsAPI, Hacker News, Product Hunt)
    Enriches with Gemini AI
    Auto-matches to providers
    """
    import asyncio
    from app.services.b2b_buyer_discovery import B2BBuyerDiscoveryService
    from app.settings import settings
    
    db = SessionLocal()
    try:
        service = B2BBuyerDiscoveryService(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY,
            newsapi_key=getattr(settings, 'NEWSAPI_KEY', None)
        )
        
        results = asyncio.run(service.run_buyer_discovery())
        
        logger.info(f"B2B buyer discovery completed: {results['discovered']} discovered, {results['created']} created, {results['matched']} matched")
        return {
            "status": "success",
            "discovered": results["discovered"],
            "created": results["created"],
            "matched": results["matched"]
        }
        
    except Exception as e:
        logger.error(f"B2B buyer discovery failed: {e}")
        raise self.retry(exc=e, countdown=300)  # 5 min retry
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def run_b2b_provider_discovery_task(self):
    """
    Run B2B provider discovery task
    
    Discovers service providers from free sources (Clutch, G2, GitHub, etc.)
    Enriches with Gemini AI
    Auto-sends opt-in emails
    """
    import asyncio
    from app.services.b2b_provider_discovery import B2BProviderDiscoveryService
    from app.settings import settings
    
    db = SessionLocal()
    try:
        service = B2BProviderDiscoveryService(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY,
            platform_email=settings.PLATFORM_EMAIL or "platform@example.com",
            dry_run=False
        )
        
        results = asyncio.run(service.run_provider_discovery())
        
        logger.info(f"B2B provider discovery completed: {results['discovered']} discovered, {results['created']} created, {results['optin_sent']} opt-in emails sent")
        return {
            "status": "success",
            "discovered": results["discovered"],
            "created": results["created"],
            "optin_sent": results["optin_sent"]
        }
        
    except Exception as e:
        logger.error(f"B2B provider discovery failed: {e}")
        raise self.retry(exc=e, countdown=300)  # 5 min retry
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def check_buyer_responses_task(self):
    """
    Check buyer responses to B2B outreach
    
    Monitors Gmail for replies
    Classifies responses using AI
    Updates match statuses
    """
    from app.services.b2b_response_tracking import B2BResponseTrackingService
    from app.settings import settings
    
    db = SessionLocal()
    try:
        service = B2BResponseTrackingService(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY
        )
        
        results = service.check_all_pending_responses()
        
        logger.info(f"Buyer response checking completed: {results['responses_found']} responses found out of {results['checked']} checked")
        return {
            "status": "success",
            "checked": results["checked"],
            "responses_found": results["responses_found"],
            "processed": len(results["processed"])
        }
        
    except Exception as e:
        logger.error(f"Buyer response checking failed: {e}")
        raise self.retry(exc=e, countdown=300)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def run_b2b_followups_task(self):
    """
    Run B2B follow-up sequences
    
    Sends Day 3, 7, 14 follow-ups to buyers who haven't responded
    """
    from app.services.b2b_followup_service import B2BFollowupService
    
    db = SessionLocal()
    try:
        service = B2BFollowupService(db)
        results = service.process_all_followups()
        
        logger.info(f"B2B follow-ups completed: {results['sent']} sent, {results['skipped']} skipped")
        return {
            "status": "success",
            "followups_sent": results["sent"],
            "skipped": results["skipped"],
            "errors": len(results["errors"])
        }
        
    except Exception as e:
        logger.error(f"B2B follow-ups failed: {e}")
        raise self.retry(exc=e, countdown=300)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def run_b2b_full_cycle_task(self):
    """
    Run complete B2B automation cycle
    
    Orchestrates discovery, response checking, and follow-ups
    """
    from celery import chain, group
    
    logger.info("Starting B2B full automation cycle")
    
    # Run discovery first
    discovery_result = run_b2b_buyer_discovery_task.delay()
    
    # Then check responses (independent of discovery)
    check_responses_result = check_buyer_responses_task.delay()
    
    # Then run follow-ups (should run after response check)
    followups_result = run_b2b_followups_task.delay()
    
    logger.info("B2B full cycle tasks queued")
    
    return {
        "status": "queued",
        "discovery_task_id": discovery_result.id,
        "responses_task_id": check_responses_result.id,
        "followups_task_id": followups_result.id
    }


# B2B Scheduled Tasks Configuration Notes:
# Add these to your Celery Beat schedule in celery_app.py:
#
# 'run-b2b-buyer-discovery': {
#     'task': 'app.workers.tasks.run_b2b_buyer_discovery_task',
#     'schedule': 21600.0,  # Every 6 hours
# },
# 'check-buyer-responses': {
#     'task': 'app.workers.tasks.check_buyer_responses_task',
#     'schedule': 3600.0,  # Every hour
# },
# 'run-b2b-followups': {
#     'task': 'app.workers.tasks.run_b2b_followups_task',
#     'schedule': 86400.0,  # Every day
# },
