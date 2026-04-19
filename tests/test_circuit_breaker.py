"""Tests for circuit breaker"""
import pytest
import time
from app.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenError,
    RetryWithBackoff
)


def test_circuit_breaker_initial_state():
    """Test circuit breaker starts closed"""
    cb = CircuitBreaker("test")
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_successful_calls():
    """Test circuit breaker with successful calls"""
    cb = CircuitBreaker("test", failure_threshold=3)
    
    def success_func():
        return "success"
    
    # Multiple successful calls should keep circuit closed
    for _ in range(5):
        result = cb.call(success_func)
        assert result == "success"
    
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_failure_threshold():
    """Test circuit breaker opens after failures"""
    cb = CircuitBreaker("test", failure_threshold=3)
    
    def fail_func():
        raise ValueError("Test error")
    
    # Fail up to threshold
    for _ in range(3):
        with pytest.raises(ValueError):
            cb.call(fail_func)
    
    # Circuit should be open now
    assert cb.state == CircuitState.OPEN
    
    # Next call should raise CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        cb.call(lambda: "should not execute")


def test_circuit_breaker_recovery():
    """Test circuit breaker recovery"""
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0)
    
    def fail_func():
        raise ValueError("Test error")
    
    # Open the circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(fail_func)
    
    assert cb.state == CircuitState.OPEN
    
    # Wait for recovery timeout
    time.sleep(0.1)
    
    # Circuit should attempt reset (half-open)
    # But will fail because we still call fail_func
    with pytest.raises(ValueError):
        cb.call(fail_func)
    
    # Should be open again after failure in half-open
    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_successful_recovery():
    """Test successful circuit breaker recovery"""
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0, half_open_max_calls=2)
    
    # Open the circuit
    def fail_func():
        raise ValueError("Test error")
    
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(fail_func)
    
    assert cb.state == CircuitState.OPEN
    
    # Wait for recovery
    time.sleep(0.1)
    
    # Successful calls in half-open should close circuit
    def success_func():
        return "success"
    
    for _ in range(2):
        result = cb.call(success_func)
        assert result == "success"
    
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_get_state():
    """Test getting circuit breaker state"""
    cb = CircuitBreaker("test_service", failure_threshold=5)
    
    state = cb.get_state()
    
    assert state["name"] == "test_service"
    assert state["state"] == "closed"
    assert state["failure_count"] == 0
    assert state["failure_threshold"] == 5


def test_retry_with_backoff_success():
    """Test retry with successful execution"""
    retry = RetryWithBackoff(max_retries=3, base_delay=0.01)
    
    def success_func():
        return "success"
    
    result = retry.execute(success_func)
    assert result == "success"


def test_retry_with_backoff_eventual_success():
    """Test retry with eventual success"""
    retry = RetryWithBackoff(max_retries=3, base_delay=0.01)
    
    call_count = 0
    
    def fail_then_succeed():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Not yet")
        return "success"
    
    result = retry.execute(fail_then_succeed)
    assert result == "success"
    assert call_count == 3


def test_retry_with_backoff_exhausted():
    """Test retry when all attempts exhausted"""
    retry = RetryWithBackoff(max_retries=2, base_delay=0.01)
    
    def always_fail():
        raise ValueError("Always fails")
    
    with pytest.raises(ValueError):
        retry.execute(always_fail)
