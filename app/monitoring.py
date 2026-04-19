"""Prometheus metrics and monitoring integration"""
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Application info
app_info = Info('ai_saas', 'Application information')

# HTTP metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Business metrics
leads_imported_total = Counter(
    'leads_imported_total',
    'Total leads imported'
)

emails_sent_total = Counter(
    'emails_sent_total',
    'Total emails sent',
    ['status']  # sent, failed
)

emails_sent_duration_seconds = Histogram(
    'emails_sent_duration_seconds',
    'Email send duration in seconds'
)

replies_received_total = Counter(
    'replies_received_total',
    'Total replies received',
    ['classification']  # interested, not_now, not_interested, unsubscribe
)

pipeline_transitions_total = Counter(
    'pipeline_transitions_total',
    'Total pipeline state transitions',
    ['from_state', 'to_state']
)

# Gauge metrics
pipeline_leads_gauge = Gauge(
    'pipeline_leads',
    'Number of leads in pipeline by state',
    ['state']
)

queue_size_gauge = Gauge(
    'queue_size',
    'Number of messages in queue',
    ['status']  # queued, sent, failed
)

escalation_queue_gauge = Gauge(
    'escalation_queue_size',
    'Number of items in escalation queue',
    ['priority']
)

deliverability_health_score = Gauge(
    'deliverability_health_score',
    'Domain health score',
    ['domain']
)

# External API metrics
gmail_api_calls_total = Counter(
    'gmail_api_calls_total',
    'Total Gmail API calls',
    ['status']  # success, error
)

openai_api_calls_total = Counter(
    'openai_api_calls_total',
    'Total OpenAI API calls',
    ['status', 'operation']  # success/error, subject/body/classification
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half_open, 2=open)',
    ['name']
)

# Celery metrics
celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']  # success, failure, retry
)


class MetricsCollector:
    """Helper class to collect and record metrics"""
    
    @staticmethod
    def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    @staticmethod
    def record_email_sent(status: str, duration: Optional[float] = None):
        """Record email sent metrics"""
        emails_sent_total.labels(status=status).inc()
        if duration:
            emails_sent_duration_seconds.observe(duration)
    
    @staticmethod
    def record_reply_received(classification: str):
        """Record reply received metrics"""
        replies_received_total.labels(classification=classification).inc()
    
    @staticmethod
    def record_pipeline_transition(from_state: str, to_state: str):
        """Record pipeline transition metrics"""
        pipeline_transitions_total.labels(
            from_state=from_state,
            to_state=to_state
        ).inc()
    
    @staticmethod
    def update_pipeline_gauge(state: str, count: int):
        """Update pipeline leads gauge"""
        pipeline_leads_gauge.labels(state=state).set(count)
    
    @staticmethod
    def update_queue_gauge(status: str, count: int):
        """Update queue size gauge"""
        queue_size_gauge.labels(status=status).set(count)
    
    @staticmethod
    def record_gmail_api_call(status: str):
        """Record Gmail API call metrics"""
        gmail_api_calls_total.labels(status=status).inc()
    
    @staticmethod
    def record_openai_api_call(status: str, operation: str):
        """Record OpenAI API call metrics"""
        openai_api_calls_total.labels(status=status, operation=operation).inc()
    
    @staticmethod
    def record_celery_task(task_name: str, status: str):
        """Record Celery task metrics"""
        celery_tasks_total.labels(task_name=task_name, status=status).inc()
    
    @staticmethod
    def update_circuit_breaker_state(name: str, state_value: int):
        """Update circuit breaker state gauge (0=closed, 1=half_open, 2=open)"""
        circuit_breaker_state.labels(name=name).set(state_value)
    
    @staticmethod
    def set_app_info(version: str, environment: str):
        """Set application info metrics"""
        app_info.info({'version': version, 'environment': environment})


def get_metrics_response() -> Response:
    """Generate Prometheus metrics response"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


class TimingContext:
    """Context manager for timing operations"""
    
    def __init__(self, metric: Histogram, labels: dict = None):
        self.metric = metric
        self.labels = labels or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if self.labels:
            self.metric.labels(**self.labels).observe(duration)
        else:
            self.metric.observe(duration)
