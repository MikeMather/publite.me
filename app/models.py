import base64
import json
import secrets
from datetime import datetime, timedelta

import cryptography.hazmat.primitives.asymmetric.ed25519 as ed25519
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key,
)
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_setup_complete = Column(Boolean, default=False)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    slug = Column(String, unique=True, index=True)
    content = Column(Text)
    markdown_content = Column(Text)
    tags = Column(String, default="")  # Comma separated
    is_published = Column(Boolean, default=False)
    is_page = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # NEW FIELD: pin_priority (Integer, nullable)
    # NULL means the post is NOT pinned.
    # 0, 1, 2, ... determines the pin order (0 is highest priority/top).
    pin_priority = Column(Integer, nullable=True)

    # SEO fields
    meta_description = Column(String(160), default="")
    meta_keywords = Column(String(255), default="")
    canonical_url = Column(String, default="")
    og_image = Column(String, default="")
    no_index = Column(Boolean, default=False)


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    blog_title = Column(String, default="My Blog")
    blog_description = Column(String, default="A minimalist blog")
    custom_css = Column(Text, default="")
    theme = Column(String, default="default")
    home_page_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    navigation_markdown = Column(Text, default="[Home](/)")
    footer_markdown = Column(Text, default="Powered by publite.me")
    private_key = Column(Text, default="")
    public_key = Column(Text, default="")
    comments_enabled = Column(Boolean, default=True)
    allow_anonymous_comments = Column(Boolean, default=False)
    rss_enabled = Column(Boolean, default=True)

    def sign_data(self, data: str) -> str:
        """Sign data with the blog's private key"""
        if not self.private_key:
            raise ValueError("Private key not set")

        private_key = load_pem_private_key(self.private_key.encode(), password=None)
        signature = private_key.sign(data.encode())
        return base64.b64encode(signature).decode()

    @staticmethod
    def verify_signature(public_key_pem: str, data: str, signature: str) -> bool:
        """Verify a signature using a public key"""
        try:
            public_key = load_pem_public_key(public_key_pem.encode())
            signature_bytes = base64.b64decode(signature)
            public_key.verify(signature_bytes, data.encode())
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    author_name = Column(String)
    author_blog_url = Column(String, nullable=True)
    post_id = Column(Integer, ForeignKey("posts.id"))
    quoted_comment_content = Column(Text, nullable=True)
    quoted_comment_author = Column(String, nullable=True)
    quoted_comment_blog_url = Column(String, nullable=True)
    verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="comments")


Post.comments = relationship(
    "Comment", back_populates="post", cascade="all, delete-orphan"
)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    data = Column(String, nullable=False, default="{}")  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    @classmethod
    def create(cls, expire_hours: int = 24) -> "Session":
        """Create a new session"""
        return cls(
            session_id=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(hours=expire_hours),
        )

    def get_data(self) -> dict:
        """Get session data as dict"""
        return json.loads(self.data)

    def set_data(self, data: dict) -> None:
        """Set session data from dict"""
        self.data = json.dumps(data)

    def refresh(self, expire_hours: int = 24) -> None:
        """Refresh session expiration"""
        self.expires_at = datetime.utcnow() + timedelta(hours=expire_hours)


class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    original_filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)  # Size in bytes
    mime_type = Column(String)
    width = Column(Integer, nullable=True)  # For images
    height = Column(Integer, nullable=True)  # For images
    created_at = Column(DateTime, default=datetime.utcnow)
    thumbnail_path = Column(String, nullable=True)
    medium_path = Column(String, nullable=True)
