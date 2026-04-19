"""Pytest configuration and fixtures"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment variables before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/0"
os.environ["SECRET_KEY"] = "test_secret_key_for_testing_purposes_only"
os.environ["OPENAI_API_KEY"] = "sk-test_openai_key_for_testing"
os.environ["GMAIL_CREDENTIALS_PATH"] = "data/credentials.json"
os.environ["GMAIL_TOKEN_PATH"] = "data/token.json"

from app.database import Base, get_db
from app.main import app
from app.settings import Settings

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine"""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create fresh database session for each test"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with dependency override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    del app.dependency_overrides[get_db]


@pytest.fixture
def sample_lead():
    """Sample lead data"""
    return {
        "lead_id": "lead-001",
        "company": "Test Corp",
        "website": "https://testcorp.com",
        "signal": "Hiring sales development reps. Just raised Series A funding.",
        "decision_maker": "John Smith",
        "fit_score": 9,
        "status": "new"
    }


@pytest.fixture
def auth_headers():
    """Authentication headers for protected endpoints"""
    from app.auth import create_access_token
    
    token = create_access_token(
        data={"sub": "test-user", "role": "admin"},
        expires_delta=None
    )
    
    return {"Authorization": f"Bearer {token}"}
