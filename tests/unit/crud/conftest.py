import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Comment, Media, Post, User


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def clear_database(db_session):
    # Clear all tables before each test
    db_session.query(Media).delete()
    db_session.query(Comment).delete()
    db_session.query(Post).delete()
    db_session.query(User).delete()
    db_session.commit()
