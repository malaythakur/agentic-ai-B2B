#!/usr/bin/env python
"""Generate a JWT token for testing"""

from app.auth import create_access_token
from app.settings import settings

# Generate token for test user
token = create_access_token(
    data={"sub": "test-user", "role": "admin"},
    expires_delta=None  # Uses default 15 minutes
)

print("JWT Token:")
print(token)
print("\nUse with curl:")
print(f'curl -H "Authorization: Bearer {token}" http://localhost:8000/api/outbound/discover/buyers')
