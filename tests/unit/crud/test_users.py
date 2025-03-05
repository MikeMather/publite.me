from sqlalchemy.orm import Session

from app.crud.users import (
    create_user,
    get_user_by_username,
    get_user_count,
    update_user,
)
from app.models import User
from app.schemas import UserCreate


def test_create_user(db_session: Session):
    try:
        user_data = UserCreate(
            username="testuser",
            password="testpassword123",
        )

        user = create_user(db_session, user_data)
        assert user.id is not None
        assert user.username == "testuser"
        assert user.hashed_password != "testpassword123"
        assert user.is_setup_complete is True

        db_user = db_session.query(User).filter_by(username="testuser").first()
        assert db_user is not None
        assert db_user.username == user.username
        assert db_user.hashed_password == user.hashed_password
    except Exception:
        db_session.rollback()
        raise


def test_get_user_by_username(db_session: Session):
    try:
        user_data = UserCreate(
            username="findme",
            password="password123",
        )
        created_user = create_user(db_session, user_data)

        user = get_user_by_username(db_session, "findme")
        assert user is not None
        assert user.id == created_user.id
        assert user.username == "findme"

        non_existent = get_user_by_username(db_session, "nonexistent")
        assert non_existent is None
    except Exception:
        db_session.rollback()
        raise


def test_update_user(db_session: Session):
    try:
        user_data = UserCreate(
            username="updateme",
            password="password123",
        )
        created_user = create_user(db_session, user_data)

        updated_user = update_user(db_session, created_user.id, is_setup_complete=False)
        assert updated_user is not None
        assert updated_user.is_setup_complete is False

        db_user = db_session.query(User).filter_by(id=created_user.id).first()
        assert db_user.is_setup_complete is False

        non_existent = update_user(db_session, 999, is_setup_complete=True)
        assert non_existent is None
    except Exception:
        db_session.rollback()
        raise


def test_get_user_count(db_session: Session):
    try:
        initial_count = get_user_count(db_session)
        assert initial_count == 0

        users = [
            UserCreate(username=f"user{i}", password="password123") for i in range(3)
        ]
        for user_data in users:
            create_user(db_session, user_data)

        updated_count = get_user_count(db_session)
        assert updated_count == 3
    except Exception:
        db_session.rollback()
        raise
