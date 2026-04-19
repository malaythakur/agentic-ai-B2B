"""Idempotency key handling for API operations"""
import hashlib
import time
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Event

logger = logging.getLogger(__name__)


class IdempotencyStore:
    """In-memory idempotency key store with TTL"""
    
    def __init__(self, ttl_seconds: int = 86400):  # 24 hours
        self.ttl_seconds = ttl_seconds
        self.store: Dict[str, dict] = {}
    
    def is_processed(self, key: str) -> bool:
        """Check if key has been processed"""
        self._cleanup()
        
        if key not in self.store:
            return False
        
        entry = self.store[key]
        if datetime.utcnow() > entry['expires_at']:
            del self.store[key]
            return False
        
        return True
    
    def get_response(self, key: str) -> Optional[dict]:
        """Get stored response for idempotent key"""
        if key in self.store:
            return self.store[key].get('response')
        return None
    
    def store_response(self, key: str, response: dict):
        """Store response for idempotent key"""
        self.store[key] = {
            'response': response,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
        }
        logger.info(f"Stored idempotent response for key: {key[:16]}...")
    
    def _cleanup(self):
        """Remove expired entries"""
        now = datetime.utcnow()
        expired = [
            key for key, entry in self.store.items()
            if now > entry['expires_at']
        ]
        for key in expired:
            del self.store[key]


# Global idempotency store
idempotency_store = IdempotencyStore()


class IdempotencyChecker:
    """Idempotency checker for API operations"""
    
    @staticmethod
    def generate_key(user_id: str, operation: str, payload: str) -> str:
        """Generate idempotency key from user, operation, and payload"""
        data = f"{user_id}:{operation}:{payload}:{int(time.time() / 300)}"  # 5-minute window
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def check_and_store(key: str, func, *args, **kwargs):
        """Check idempotency and execute function if not processed"""
        if idempotency_store.is_processed(key):
            logger.info(f"Returning cached response for idempotent key: {key[:16]}...")
            return idempotency_store.get_response(key)
        
        # Execute function
        result = func(*args, **kwargs)
        
        # Store response
        idempotency_store.store_response(key, result)
        
        return result


def with_idempotency(operation_name: str):
    """Decorator for idempotent operations"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract user_id and idempotency_key from kwargs
            user_id = kwargs.get('user_id', 'anonymous')
            idempotency_key = kwargs.pop('idempotency_key', None)
            
            if not idempotency_key:
                # No idempotency key, execute normally
                return func(*args, **kwargs)
            
            # Generate or use provided key
            key = idempotency_key or IdempotencyChecker.generate_key(
                user_id, operation_name, str(args) + str(kwargs)
            )
            
            return IdempotencyChecker.check_and_store(key, func, *args, **kwargs)
        return wrapper
    return decorator


class IdempotencyMiddleware:
    """FastAPI middleware for idempotency handling"""
    
    def __init__(self, header_name: str = "Idempotency-Key"):
        self.header_name = header_name
    
    async def __call__(self, request, call_next):
        """Process request with idempotency check"""
        idempotency_key = request.headers.get(self.header_name)
        
        if idempotency_key:
            # Check if already processed
            if idempotency_store.is_processed(idempotency_key):
                cached_response = idempotency_store.get_response(idempotency_key)
                if cached_response:
                    from fastapi import Response
                    import json
                    return Response(
                        content=json.dumps(cached_response),
                        media_type="application/json",
                        headers={"X-Idempotency-Status": "cached"}
                    )
            
            # Store key for later storage
            request.state.idempotency_key = idempotency_key
        
        response = await call_next(request)
        
        # Store response if idempotency key was used
        if hasattr(request.state, 'idempotency_key'):
            # This would need the response body, which is tricky in middleware
            # In practice, handle this in the endpoint itself
            pass
        
        return response
