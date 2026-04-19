from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

from app.settings import settings
from app.database import engine, Base
from app.api.routes import router
from app.logging_config import setup_logging
from app.monitoring import MetricsCollector, get_metrics_response
from app.health import HealthChecker, ReadinessChecker, LivenessChecker
from app.config_validator import validate_config
from app.shutdown import setup_default_shutdown_hooks
from app.auth import check_rate_limit
from app.idempotency import idempotency_store

# Setup logging
logger = setup_logging()

# Validate configuration on startup
if not validate_config():
    logger.error("Configuration validation failed - exiting")
    raise SystemExit(1)

# Setup graceful shutdown hooks
setup_default_shutdown_hooks()

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize metrics
MetricsCollector.set_app_info(settings.APP_VERSION, "production" if not settings.DEBUG else "development")


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract endpoint name for metrics
        endpoint = request.url.path
        method = request.method
        
        # Check rate limiting for API endpoints
        if endpoint.startswith("/api/"):
            client_ip = request.client.host if request.client else "unknown"
            try:
                check_rate_limit(client_ip)
            except Exception as e:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded"}
                )
        
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        status_code = response.status_code
        
        MetricsCollector.record_http_request(method, endpoint, status_code, duration)
        
        return response


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware to handle idempotency keys"""
    
    async def dispatch(self, request: Request, call_next):
        idempotency_key = request.headers.get("Idempotency-Key")
        
        if idempotency_key and request.method in ["POST", "PUT", "PATCH"]:
            # Check if already processed
            if idempotency_store.is_processed(idempotency_key):
                cached = idempotency_store.get_response(idempotency_key)
                if cached:
                    return JSONResponse(
                        content=cached,
                        headers={"X-Idempotency-Status": "cached"}
                    )
            
            request.state.idempotency_key = idempotency_key
        
        response = await call_next(request)
        return response


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Add middleware
app.add_middleware(MetricsMiddleware)
app.add_middleware(IdempotencyMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "environment": "production" if not settings.DEBUG else "development"
    }


@app.get("/health")
async def health_check():
    """Deep health check with all system components"""
    checker = HealthChecker()
    return checker.run_all_checks()


@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    return ReadinessChecker.is_ready()


@app.get("/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return LivenessChecker.is_alive()


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return get_metrics_response()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {'production' if not settings.DEBUG else 'development'}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize default templates if none exist
    try:
        from app.database import SessionLocal
        from app.services.template_service import initialize_default_templates
        
        db = SessionLocal()
        try:
            initialize_default_templates(db)
            logger.info("Template system initialized successfully")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error initializing templates: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info(f"Shutting down {settings.APP_NAME}")
