"""Configuration validation for startup"""
import os
import logging
from typing import List, Tuple
from app.settings import settings

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validate configuration on startup"""
    
    REQUIRED_ENV_VARS = [
        'DATABASE_URL',
        'REDIS_URL',
        'CELERY_BROKER_URL',
        'SECRET_KEY',
        'OPENAI_API_KEY'
    ]
    
    OPTIONAL_BUT_RECOMMENDED = [
        'GMAIL_CREDENTIALS_PATH',
        'ALERT_WEBHOOK_URL',
        'SENTRY_DSN'
    ]
    
    @classmethod
    def validate(cls) -> Tuple[bool, List[str]]:
        """Validate all configuration
        
        Returns:
            (is_valid, list of errors)
        """
        errors = []
        warnings = []
        
        # Check required environment variables
        for var in cls.REQUIRED_ENV_VARS:
            if not os.getenv(var):
                errors.append(f"Required environment variable {var} is not set")
        
        # Check optional but recommended
        for var in cls.OPTIONAL_BUT_RECOMMENDED:
            if not os.getenv(var):
                warnings.append(f"Optional environment variable {var} is not set (recommended)")
        
        # Validate database URL format
        if settings.DATABASE_URL:
            if not (settings.DATABASE_URL.startswith('postgresql://') or 
                    settings.DATABASE_URL.startswith('postgresql+psycopg://') or 
                    settings.DATABASE_URL.startswith('sqlite://')):
                errors.append("DATABASE_URL must start with 'postgresql://', 'postgresql+psycopg://', or 'sqlite://'")
        
        # Validate Redis URL
        if settings.REDIS_URL:
            if not settings.REDIS_URL.startswith('redis://'):
                errors.append("REDIS_URL must start with 'redis://'")
        
        # Validate secret key
        if settings.SECRET_KEY:
            if len(settings.SECRET_KEY) < 32:
                warnings.append("SECRET_KEY should be at least 32 characters for security")
        
        # Validate Gmail credentials path
        if settings.GMAIL_CREDENTIALS_PATH:
            if not os.path.exists(settings.GMAIL_CREDENTIALS_PATH):
                warnings.append(f"Gmail credentials file not found at {settings.GMAIL_CREDENTIALS_PATH}")
        
        # Validate OpenAI API key format
        if settings.OPENAI_API_KEY:
            if not settings.OPENAI_API_KEY.startswith('sk-'):
                warnings.append("OPENAI_API_KEY doesn't have expected format")
        
        # Validate file paths
        data_dir = 'data'
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir)
                logger.info(f"Created data directory: {data_dir}")
            except Exception as e:
                errors.append(f"Failed to create data directory: {e}")
        
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            try:
                os.makedirs(logs_dir)
                logger.info(f"Created logs directory: {logs_dir}")
            except Exception as e:
                errors.append(f"Failed to create logs directory: {e}")
        
        # Log results
        if warnings:
            for warning in warnings:
                logger.warning(f"Config Warning: {warning}")
        
        if errors:
            for error in errors:
                logger.error(f"Config Error: {error}")
            return False, errors
        
        if warnings:
            logger.info("Configuration validation passed with warnings")
        else:
            logger.info("Configuration validation passed")
        
        return True, []
    
    @classmethod
    def validate_database_connection(cls) -> Tuple[bool, str]:
        """Test database connection"""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "Database connection OK"
        except Exception as e:
            return False, f"Database connection failed: {str(e)}"
    
    @classmethod
    def validate_redis_connection(cls) -> Tuple[bool, str]:
        """Test Redis connection"""
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            return True, "Redis connection OK"
        except Exception as e:
            return False, f"Redis connection failed: {str(e)}"
    
    @classmethod
    def validate_gmail_setup(cls) -> Tuple[bool, str]:
        """Validate Gmail API setup"""
        if not settings.GMAIL_CREDENTIALS_PATH:
            return True, "Gmail not configured (optional)"
        
        if not os.path.exists(settings.GMAIL_CREDENTIALS_PATH):
            return False, f"Gmail credentials file not found at {settings.GMAIL_CREDENTIALS_PATH}"
        
        # Check if it's valid JSON
        try:
            import json
            with open(settings.GMAIL_CREDENTIALS_PATH, 'r') as f:
                creds = json.load(f)
                if 'installed' not in creds and 'web' not in creds:
                    return False, "Invalid Gmail credentials format"
            return True, "Gmail credentials OK"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON in Gmail credentials: {e}"
        except Exception as e:
            return False, f"Error reading Gmail credentials: {e}"
    
    @classmethod
    def run_all_validations(cls) -> bool:
        """Run all validations and return if startup should proceed"""
        logger.info("Running startup configuration validation...")
        
        # Basic config validation
        is_valid, errors = cls.validate()
        if not is_valid:
            logger.error("Configuration validation failed - startup aborted")
            return False
        
        # Test connections (skip Redis for tests)
        checks = [
            ("Database", cls.validate_database_connection),
        ]
        
        # Only check Redis if not in test mode (sqlite indicates test)
        if not settings.DATABASE_URL.startswith('sqlite://'):
            checks.append(("Redis", cls.validate_redis_connection))
        
        checks.append(("Gmail", cls.validate_gmail_setup))
        
        for name, check_func in checks:
            success, message = check_func()
            if success:
                logger.info(f"{name}: {message}")
            else:
                if name == "Gmail":
                    logger.warning(f"{name}: {message} (optional)")
                else:
                    logger.error(f"{name}: {message}")
                    is_valid = False
        
        if is_valid:
            logger.info("All startup validations passed - proceeding with startup")
        else:
            logger.error("Some validations failed - startup aborted")
        
        return is_valid


def validate_config():
    """Convenience function for startup validation"""
    return ConfigValidator.run_all_validations()
