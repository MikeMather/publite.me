from typing import Optional

from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.models import User


def create_user(db: Session, user) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username, hashed_password=hashed_password, is_setup_complete=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

    return db.query(User).count()


def update_user(db: Session, user_id: int, is_setup_complete: bool) -> User:
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.is_setup_complete = is_setup_complete
        db.commit()
        db.refresh(db_user)
    return db_user


def get_user_count(db: Session) -> int:
    return db.query(User).count()
