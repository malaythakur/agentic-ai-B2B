"""Circuit Breaker pattern for external API resilience"""
import time
import logging
from enum import Enum
from typing import Callable, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for external API calls"""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self.success_count = 0
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerOpenError(f"Circuit {self.name} is OPEN")
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpenError(f"Circuit {self.name} half-open limit reached")
            self.half_open_calls += 1
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try reset"""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _transition_to_half_open(self):
        """Transition from OPEN to HALF_OPEN"""
        logger.info(f"Circuit {self.name} transitioning to HALF_OPEN")
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.success_count = 0
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            # If enough successful calls, close the circuit
            if self.success_count >= self.half_open_max_calls:
                logger.info(f"Circuit {self.name} transitioning to CLOSED")
                self._reset()
        else:
            # In closed state, just reset failure count periodically
            if self.failure_count > 0:
                self.failure_count = max(0, self.failure_count - 1)
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Failed in half-open, go back to open
            logger.warning(f"Circuit {self.name} failed in HALF_OPEN, transitioning to OPEN")
            self._transition_to_open()
        elif self.failure_count >= self.failure_threshold:
            # Too many failures, open the circuit
            logger.warning(f"Circuit {self.name} failure threshold reached, transitioning to OPEN")
            self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition to OPEN state"""
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
    
    def _reset(self):
        """Reset circuit breaker to initial state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self.success_count = 0
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


# Global circuit breakers for external services
gmail_circuit = CircuitBreaker("gmail_api", failure_threshold=3, recovery_timeout=300)
openai_circuit = CircuitBreaker("openai_api", failure_threshold=5, recovery_timeout=120)


def with_circuit_breaker(circuit: CircuitBreaker):
    """Decorator to wrap function with circuit breaker"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return circuit.call(func, *args, **kwargs)
        return wrapper
    return decorator


class RetryWithBackoff:
    """Retry mechanism with exponential backoff"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exceptions: tuple = (Exception,)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exceptions = exceptions
    
    def execute(self, func: Callable, *args, **kwargs):
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.exceptions as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed")
        
        raise last_exception


def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retry with exponential backoff"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry = RetryWithBackoff(max_retries=max_retries, base_delay=base_delay)
            return retry.execute(func, *args, **kwargs)
        return wrapper
    return decorator
