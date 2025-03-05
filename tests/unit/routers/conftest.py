from datetime import datetime
from typing import Generator

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth import get_password_hash
from app.database import get_db
from app.main import app, templates
from app.models import Base, Comment, Media, Post, Settings, User
from app.routers import admin_router, blog_router, media_router


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite:///./data/test.db", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    Creates a fresh SQLite database for each test.
    """
    testing_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    session = testing_session_local()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function", autouse=True)
def clear_database(db_session):
    """
    Clear all tables before each test.
    """
    db_session.query(Comment).delete()
    db_session.query(Media).delete()
    db_session.query(Post).delete()
    db_session.query(User).delete()
    db_session.query(Settings).delete()
    db_session.commit()


@pytest.fixture
def mock_user(db_session):
    """Create a test user."""
    user = User(
        username="testuser",
        hashed_password=get_password_hash("password123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def mock_post(db_session):
    """Create a test post."""
    post = Post(
        title="Test Post",
        markdown_content="# This is a test post content.",
        content="<h1>This is a test post content.</h1>",
        slug="test-post",
        is_published=True,
        is_page=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        meta_description="",
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post


@pytest.fixture
def mock_settings(db_session, mock_post):
    """Create test settings with all required fields."""
    settings = Settings(
        blog_title="Test Blog",
        blog_description="A test blog for unit testing",
        custom_css="",
        theme="default",
        home_page_id=mock_post.id if mock_post else None,
        navigation_markdown="[Home](/)",
        footer_markdown="Test Footer",
        private_key="",
        public_key="",
        comments_enabled=True,
        allow_anonymous_comments=False,
        rss_enabled=True,
    )

    db_session.add(settings)
    db_session.commit()
    db_session.refresh(settings)
    return settings


@pytest.fixture
def test_app():
    """Create a test app without the problematic middleware."""
    test_app = FastAPI()
    test_app.include_router(admin_router.router)
    test_app.include_router(blog_router.router)
    test_app.include_router(media_router.router)

    @test_app.get("/test")
    def test_route():
        return {"status": "ok"}

    return test_app


@pytest.fixture
def client(test_app, db_session, mock_settings):
    """Create a test client with minimal mocking."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    test_app.dependency_overrides[get_db] = override_get_db

    @test_app.middleware("http")
    async def simplified_middleware(request: Request, call_next):
        request.state.templates = templates
        request.state.settings = mock_settings
        request.state.csrf_token = "test_csrf_token"

        class SimpleSession:
            def get(self, key):
                return 1

            async def save(self, response):
                pass

        request.state.session = SimpleSession()

        response = await call_next(request)

        return response

    with TestClient(test_app) as client:
        yield client

    test_app.dependency_overrides.clear()
