"""
RFP Sniper - Test Configuration
================================
Pytest fixtures and configuration for testing.
"""

import asyncio
import os
import tempfile
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app import models  # noqa: F401
from app.database import get_session
from app.main import app
from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password
from app.services.cache_service import cache_clear

# Test database URL - use isolated SQLite file for deterministic test runs.
_test_db_path = os.getenv("TEST_DB_PATH")
if not _test_db_path:
    _test_db_path = str(
        Path(tempfile.gettempdir()) / f"govtech_sniper_test_{os.getpid()}_{uuid.uuid4().hex}.db"
    )
TEST_DB_PATH = Path(_test_db_path).resolve()
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

# Create test session maker
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db_file() -> Generator[None, None, None]:
    """Remove isolated sqlite db artifacts after the test session."""
    yield
    for suffix in ("", "-journal", "-wal", "-shm"):
        target = Path(f"{TEST_DB_PATH}{suffix}")
        if target.exists():
            target.unlink()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def reset_cache() -> AsyncGenerator[None, None]:
    """Ensure cache is cleared between tests to avoid cross-test pollution."""
    await cache_clear()
    yield
    await cache_clear()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database session override."""

    async def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("TestPassword123!"),
        full_name="Test User",
        company_name="Test Company",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """Get auth headers for test user."""
    tokens = create_token_pair(test_user.id, test_user.email, test_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def test_rfp(db_session: AsyncSession, test_user: User) -> RFP:
    """Create a test RFP."""
    rfp = RFP(
        user_id=test_user.id,
        title="Test Cybersecurity Services RFP",
        solicitation_number="W912HV-24-R-0001",
        notice_id="test-notice-123",
        agency="Department of Defense",
        sub_agency="U.S. Army Corps of Engineers",
        naics_code="541512",
        set_aside="Small Business",
        rfp_type="solicitation",
        status="new",
        posted_date=datetime.utcnow(),
        response_deadline=datetime(2025, 3, 15, 17, 0, 0),
        estimated_value=2500000,
    )
    db_session.add(rfp)
    await db_session.commit()
    await db_session.refresh(rfp)
    return rfp


@pytest_asyncio.fixture
async def test_proposal(db_session: AsyncSession, test_user: User, test_rfp: RFP) -> Proposal:
    """Create a test proposal."""
    proposal = Proposal(
        user_id=test_user.id,
        rfp_id=test_rfp.id,
        title=f"Proposal for {test_rfp.title}",
        status="draft",
        total_sections=5,
        completed_sections=0,
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)
    return proposal


@pytest_asyncio.fixture
async def test_document(db_session: AsyncSession, test_user: User) -> KnowledgeBaseDocument:
    """Create a test knowledge base document."""
    doc = KnowledgeBaseDocument(
        user_id=test_user.id,
        title="Test Capability Statement",
        document_type="capability_statement",
        original_filename="capability_statement.pdf",
        file_path="/uploads/test/capability_statement.pdf",
        file_size_bytes=1024000,
        mime_type="application/pdf",
        processing_status="ready",
        is_ready=True,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc
