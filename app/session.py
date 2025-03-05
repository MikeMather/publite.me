from typing import Any

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session as SQLAlchemySession

from app.database import get_db
from app.models import Session

SESSION_COOKIE_NAME = "session_id"


class SessionManager:
    def __init__(self, request: Request, db: SQLAlchemySession):
        self.request = request
        self.db = db
        self.session_id = request.cookies.get(SESSION_COOKIE_NAME)
        self._session = None
        self._data = None

    async def load(self) -> None:
        """Load session data from database"""
        if not self.session_id:
            self._create_session()
            return

        session = (
            self.db.query(Session).filter(Session.session_id == self.session_id).first()
        )

        if session and not session.is_expired:
            self._session = session
            self._data = session.get_data()
            session.refresh()
            self.db.commit()
        else:
            self._create_session()

    def _create_session(self) -> None:
        """Create a new session"""
        self._session = Session.create()
        self._data = {}
        self.session_id = self._session.session_id
        self.db.add(self._session)
        self.db.commit()

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from session"""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value in session"""
        self._data[key] = value
        self._session.set_data(self._data)
        self.db.commit()

    def delete(self, key: str) -> None:
        """Delete key from session"""
        if key in self._data:
            del self._data[key]
            self._session.set_data(self._data)
            self.db.commit()

    def save(self, response: Response) -> None:
        """Save session and set cookie"""
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=self.session_id,
            httponly=True,
            secure=self.request.url.scheme == "https",
            samesite="lax",
            max_age=86400,  # 24 hours
        )

    async def clear(self, response: Response) -> None:
        """Clear session data and remove cookie"""
        if self._session:
            self.db.delete(self._session)
            self.db.commit()
        response.delete_cookie(SESSION_COOKIE_NAME)
        self._data = {}
        self._session = None
        self.session_id = None


async def get_session(
    request: Request, db: SQLAlchemySession = Depends(get_db)
) -> SessionManager:
    """Get or create session manager"""
    if not hasattr(request.state, "session"):
        session = SessionManager(request, db)
        await session.load()
        request.state.session = session
    return request.state.session
