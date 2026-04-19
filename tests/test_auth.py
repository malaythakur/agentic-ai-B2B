"""Tests for authentication module"""
import pytest
from datetime import timedelta
from app.auth import (
    create_access_token,
    decode_token,
    verify_password,
    get_password_hash,
    RateLimiter
)


def test_password_hashing():
    """Test password hashing and verification"""
    password = "test_password123"
    hashed = get_password_hash(password)
    
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_jwt_token_creation():
    """Test JWT token creation and decoding"""
    data = {"sub": "user123", "role": "admin"}
    token = create_access_token(data)
    
    assert token is not None
    assert isinstance(token, str)


def test_jwt_token_decoding():
    """Test JWT token decoding"""
    data = {"sub": "user123", "role": "admin"}
    token = create_access_token(data, expires_delta=timedelta(minutes=5))
    
    decoded = decode_token(token)
    
    assert decoded is not None
    assert decoded["sub"] == "user123"
    assert decoded["role"] == "admin"


def test_expired_token():
    """Test expired token handling"""
    data = {"sub": "user123"}
    # Create expired token (negative expiration)
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))
    
    decoded = decode_token(token)
    
    assert decoded is None


def test_rate_limiter():
    """Test rate limiter functionality"""
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    
    # Should allow first 3 requests
    assert limiter.is_allowed("key1")
    assert limiter.is_allowed("key1")
    assert limiter.is_allowed("key1")
    
    # Should block 4th request
    assert not limiter.is_allowed("key1")
    
    # Different key should still be allowed
    assert limiter.is_allowed("key2")


def test_rate_limiter_cleanup():
    """Test rate limiter cleanup of old entries"""
    limiter = RateLimiter(max_requests=1, window_seconds=1)
    
    # Add request
    assert limiter.is_allowed("key1")
    
    # Wait for window to expire
    import time
    time.sleep(1.1)
    
    # Next request should be allowed after window expires
    assert limiter.is_allowed("key1")


@pytest.mark.asyncio
async def test_get_current_user(client, auth_headers):
    """Test authentication endpoint"""
    response = client.get("/health", headers=auth_headers)
    assert response.status_code == 200
