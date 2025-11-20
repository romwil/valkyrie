"""Global test configuration and fixtures."""

import os
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set test environment
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["GEMINI_API_KEY"] = "test-api-key"

from src.database import Base, get_db
from src.api.main import app
from src.models import User, Company, Record, Job


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_gemini():
    """Mock Gemini API responses."""
    with patch("google.generativeai.GenerativeModel") as mock_model:
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance

        # Mock generate_content method
        mock_response = MagicMock()
        mock_response.text = """{
    "industry": "Technology",
    "size": "100-500",
    "revenue": "$10M-$50M",
    "description": "A leading technology company specializing in AI solutions.",
    "key_products": ["AI Platform", "Data Analytics"],
    "target_market": "Enterprise",
    "competitors": ["Company A", "Company B"],
    "recent_news": "Raised $20M in Series B funding"
}"""
        mock_instance.generate_content.return_value = mock_response

        yield mock_instance


@pytest.fixture
def sample_user(db_session: Session) -> User:
    """Create a sample user for testing."""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password="$2b$12$test_hashed_password",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_company(db_session: Session) -> Company:
    """Create a sample company for testing."""
    company = Company(
        name="Test Company",
        domain="testcompany.com",
        industry="Technology",
        size="100-500",
        revenue="$10M-$50M",
        description="A test company for unit tests"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def sample_job(db_session: Session, sample_user: User) -> Job:
    """Create a sample job for testing."""
    job = Job(
        name="Test Enrichment Job",
        user_id=sample_user.id,
        status="pending",
        total_records=100,
        processed_records=0,
        successful_records=0,
        failed_records=0
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def auth_headers(sample_user: User) -> dict:
    """Create authentication headers for testing."""
    # In a real app, you would generate a proper JWT token
    # For testing, we'll use a mock token
    return {"Authorization": "Bearer test-token-for-" + sample_user.username}


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Async fixtures
@pytest.fixture
async def async_client(db_session: Session) -> AsyncGenerator:
    """Create an async test client."""
    from httpx import AsyncClient

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
