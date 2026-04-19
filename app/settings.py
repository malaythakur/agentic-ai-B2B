from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Gmail API
    GMAIL_CREDENTIALS_PATH: str = "data/credentials.json"
    GMAIL_TOKEN_PATH: str = "data/token.json"
    GMAIL_SCOPES: str = "https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.modify"
    
    # OpenAI
    OPENAI_API_KEY: str

    # Gemini
    GEMINI_API_KEY: Optional[str] = None

    # GitHub
    GITHUB_TOKEN: Optional[str] = None

    # NewsAPI
    NEWSAPI_KEY: Optional[str] = None

    # FastAPI / Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 1000
    RATE_LIMIT_PER_HOUR: int = 10000
    
    # Circuit Breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60
    
    # Alerting
    ALERT_WEBHOOK_URL: Optional[str] = None
    SLACK_WEBHOOK_URL: Optional[str] = None
    ALERT_EMAILS: Optional[str] = None  # Comma-separated
    ALERT_SEVERITY_THRESHOLD: str = "warning"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # Deliverability
    MAX_SENDS_PER_HOUR: int = 30
    MAX_SENDS_PER_DAY: int = 200
    DOMAIN_WARMUP_DAYS: int = 14
    
    # Lead Qualification
    MIN_PRIORITY_SCORE: int = 50
    QUALIFICATION_BATCH_SIZE: int = 100
    
    # Backup
    BACKUP_DIR: str = "./backups"
    BACKUP_RETENTION_DAYS: int = 7
    S3_BUCKET: Optional[str] = None
    
    # Application
    APP_NAME: str = "AI SaaS Outbound"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT == "production"
    
    @property
    def alert_email_list(self) -> list:
        """Get list of alert emails"""
        if self.ALERT_EMAILS:
            return [email.strip() for email in self.ALERT_EMAILS.split(",")]
        return []


settings = Settings()
