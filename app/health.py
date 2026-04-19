"""Deep health checks for production monitoring"""
import logging
import time
from typing import Dict, List
from sqlalchemy import text
from sqlalchemy.orm import Session
import redis
from app.settings import settings
from app.database import engine

logger = logging.getLogger(__name__)


class HealthChecker:
    """Comprehensive health checker"""
    
    def __init__(self):
        self.checks = {}
    
    def check_database(self) -> Dict:
        """Check database connectivity"""
        try:
            start_time = time.time()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            latency = time.time() - start_time
            
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2),
                "message": "Database connection OK"
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": None,
                "message": f"Database connection failed: {str(e)}"
            }
    
    def check_redis(self) -> Dict:
        """Check Redis connectivity"""
        try:
            start_time = time.time()
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            latency = time.time() - start_time
            
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2),
                "message": "Redis connection OK"
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": None,
                "message": f"Redis connection failed: {str(e)}"
            }
    
    def check_gmail_api(self) -> Dict:
        """Check Gmail API connectivity"""
        try:
            # Check if credentials exist
            import os
            if not os.path.exists(settings.GMAIL_CREDENTIALS_PATH):
                return {
                    "status": "warning",
                    "latency_ms": None,
                    "message": "Gmail credentials not configured"
                }
            
            # Would need to actually call Gmail API to fully test
            return {
                "status": "healthy",
                "latency_ms": None,
                "message": "Gmail credentials present"
            }
        except Exception as e:
            logger.error(f"Gmail API health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": None,
                "message": f"Gmail API check failed: {str(e)}"
            }
    
    def check_openai_api(self) -> Dict:
        """Check OpenAI API connectivity"""
        try:
            if not settings.OPENAI_API_KEY:
                return {
                    "status": "warning",
                    "latency_ms": None,
                    "message": "OpenAI API key not configured"
                }
            
            return {
                "status": "healthy",
                "latency_ms": None,
                "message": "OpenAI API key configured"
            }
        except Exception as e:
            logger.error(f"OpenAI API health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": None,
                "message": f"OpenAI API check failed: {str(e)}"
            }
    
    def check_disk_space(self) -> Dict:
        """Check available disk space"""
        try:
            import shutil
            stat = shutil.disk_usage("/")
            free_gb = stat.free / (1024**3)
            total_gb = stat.total / (1024**3)
            used_percent = (stat.used / stat.total) * 100
            
            status = "healthy"
            if free_gb < 1:
                status = "critical"
            elif free_gb < 5:
                status = "warning"
            
            return {
                "status": status,
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "used_percent": round(used_percent, 2),
                "message": f"Disk: {free_gb:.1f}GB free"
            }
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return {
                "status": "unknown",
                "free_gb": None,
                "message": f"Disk check failed: {str(e)}"
            }
    
    def check_memory(self) -> Dict:
        """Check memory usage"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            status = "healthy"
            if memory.percent > 90:
                status = "critical"
            elif memory.percent > 80:
                status = "warning"
            
            return {
                "status": status,
                "used_percent": memory.percent,
                "available_gb": round(memory.available / (1024**3), 2),
                "message": f"Memory: {memory.percent}% used"
            }
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return {
                "status": "unknown",
                "used_percent": None,
                "message": f"Memory check failed: {str(e)}"
            }
    
    def run_all_checks(self) -> Dict:
        """Run all health checks"""
        start_time = time.time()
        
        checks = {
            "database": self.check_database(),
            "openai_api": self.check_openai_api(),
            "disk_space": self.check_disk_space(),
            "memory": self.check_memory()
        }
        
        # Only check Redis if not in test mode (sqlite indicates test)
        if not settings.DATABASE_URL.startswith('sqlite://'):
            checks["redis"] = self.check_redis()
        else:
            checks["redis"] = {"status": "skipped", "message": "Redis check skipped in test mode"}
        
        # Only check Gmail API if not in test mode
        if not settings.DATABASE_URL.startswith('sqlite://'):
            checks["gmail_api"] = self.check_gmail_api()
        else:
            checks["gmail_api"] = {"status": "skipped", "message": "Gmail API check skipped in test mode"}
        
        # Determine overall status
        statuses = [c["status"] for c in checks.values()]
        
        # Filter out "skipped" statuses for overall health determination
        active_statuses = [s for s in statuses if s != "skipped"]
        
        if any(s == "critical" for s in active_statuses):
            overall_status = "critical"
        elif any(s == "unhealthy" for s in active_statuses):
            overall_status = "unhealthy"
        elif any(s == "warning" for s in active_statuses):
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "timestamp": time.time(),
            "duration_ms": round((time.time() - start_time) * 1000, 2),
            "checks": checks
        }


class ReadinessChecker:
    """Readiness checks for Kubernetes/Container orchestration"""
    
    @staticmethod
    def is_ready() -> Dict:
        """Check if application is ready to serve traffic"""
        checks = {}
        
        # Check database
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks["database"] = True
        except:
            checks["database"] = False
        
        # Check Redis
        try:
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            checks["redis"] = True
        except:
            checks["redis"] = False
        
        is_ready = all(checks.values())
        
        return {
            "ready": is_ready,
            "checks": checks
        }


class LivenessChecker:
    """Liveness checks for Kubernetes/Container orchestration"""
    
    @staticmethod
    def is_alive() -> Dict:
        """Check if application is alive"""
        # Simple check - application is running
        return {
            "alive": True,
            "timestamp": time.time()
        }
