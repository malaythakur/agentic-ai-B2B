from celery import Celery
from app.settings import settings

celery_app = Celery(
    'ai_saas',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    worker_pool='solo',  # Windows-compatible pool (prefork fails on Windows)
    broker_connection_retry_on_startup=True,  # Suppress Celery 6.0 deprecation warning
)

# Celery Beat Schedule
celery_app.conf.beat_schedule = {
    'daily-batch-generation': {
        'task': 'app.workers.tasks.daily_batch_generation_task',
        'schedule': 86400.0,  # Every 24 hours
    },
    'followup-scheduling': {
        'task': 'app.workers.tasks.schedule_followups_task',
        'schedule': 3600.0,  # Every hour
    },
    'daily-qualification-scoring': {
        'task': 'app.workers.tasks.daily_qualification_scoring_task',
        'schedule': 86400.0,  # Every 24 hours
    },
    'hourly-deliverability-reset': {
        'task': 'app.workers.tasks.hourly_deliverability_reset_task',
        'schedule': 3600.0,  # Every hour
    },
    'daily-deliverability-reset': {
        'task': 'app.workers.tasks.daily_deliverability_reset_task',
        'schedule': 86400.0,  # Every 24 hours
    },
    'pipeline-monitoring': {
        'task': 'app.workers.tasks.pipeline_monitoring_task',
        'schedule': 21600.0,  # Every 6 hours
    },
    'feedback-learning': {
        'task': 'app.workers.tasks.feedback_learning_task',
        'schedule': 86400.0,  # Every 24 hours
    },
    'auto-escalation': {
        'task': 'app.workers.tasks.auto_escalation_task',
        'schedule': 43200.0,  # Every 12 hours
    },
    'send-due-followups': {
        'task': 'app.workers.tasks.send_due_followups_task',
        'schedule': 3600.0,  # Every hour
    },
    # Autonomous Discovery Tasks (Zero-Touch Lead Generation)
    'autonomous-discovery': {
        'task': 'app.workers.tasks.autonomous_discovery_task',
        'schedule': 600.0,  # Every 10 minutes - good for testing, won't hit rate limits
    },
    'discovery-analytics': {
        'task': 'app.workers.tasks.discovery_analytics_task',
        'schedule': 86400.0,  # Daily - analyze discovery performance
    },
    # B2B Matchmaking Platform Tasks (Fully Automated)
    'b2b-provider-discovery': {
        'task': 'app.workers.tasks.run_b2b_provider_discovery_task',
        'schedule': 43200.0,  # Every 12 hours - discover new service providers
    },
    'b2b-buyer-discovery': {
        'task': 'app.workers.tasks.run_b2b_buyer_discovery_task',
        'schedule': 21600.0,  # Every 6 hours - discover new buyers
    },
    'b2b-response-tracking': {
        'task': 'app.workers.tasks.check_buyer_responses_task',
        'schedule': 3600.0,  # Every hour - check for buyer replies
    },
    'b2b-followup-sequences': {
        'task': 'app.workers.tasks.run_b2b_followups_task',
        'schedule': 86400.0,  # Every day - send follow-up emails
    },
}

# Import tasks to register them with Celery
import app.workers.tasks  # noqa: E402, F401
