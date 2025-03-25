from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_setup_complete: bool

    class Config:
        from_attributes = True


class PostBase(BaseModel):
    title: str
    slug: str
    markdown_content: str
    tags: Optional[str] = ""
    is_published: bool = False
    published_at: Optional[datetime] = None
    is_page: bool = False
    meta_description: Optional[str] = ""
    meta_keywords: Optional[str] = ""
    canonical_url: Optional[str] = ""
    og_image: Optional[str] = ""
    no_index: bool = False


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    markdown_content: Optional[str] = None
    tags: Optional[str] = None
    is_published: Optional[bool] = None
    published_at: Optional[datetime] = None
    is_page: Optional[bool] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    canonical_url: Optional[str] = None
    og_image: Optional[str] = None
    no_index: Optional[bool] = None


class Post(PostBase):
    id: int
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingsBase(BaseModel):
    blog_title: str
    blog_description: str
    custom_css: str
    theme: str
    navigation_markdown: str = "[Home](/)"
    footer_markdown: str = "Powered by publite.me"
    home_page_id: Optional[int] = None
    private_key: str = ""
    public_key: str = ""
    comments_enabled: bool = True
    allow_anonymous_comments: bool = False
    rss_enabled: bool = True


class SettingsUpdate(BaseModel):
    blog_title: Optional[str] = None
    blog_description: Optional[str] = None
    custom_css: Optional[str] = None
    theme: Optional[str] = None
    navigation_markdown: Optional[str] = None
    footer_markdown: Optional[str] = None
    home_page_id: Optional[int] = None
    private_key: Optional[str] = None
    public_key: Optional[str] = None
    comments_enabled: Optional[bool] = None
    allow_anonymous_comments: Optional[bool] = None
    rss_enabled: Optional[bool] = None


class Settings(SettingsBase):
    id: int

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class MediaBase(BaseModel):
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_path: Optional[str] = None
    medium_path: Optional[str] = None


class MediaCreate(MediaBase):
    pass


class MediaUpdate(BaseModel):
    filename: Optional[str] = None
    original_filename: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_path: Optional[str] = None
    medium_path: Optional[str] = None


class Media(MediaBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CommentBase(BaseModel):
    content: str
    author_name: str
    author_blog_url: Optional[str] = None
    quoted_comment_content: Optional[str] = None
    quoted_comment_author: Optional[str] = None
    quoted_comment_blog_url: Optional[str] = None


class CommentCreate(CommentBase):
    post_id: int


class CommentUpdate(BaseModel):
    content: Optional[str] = None
    author_name: Optional[str] = None
    author_blog_url: Optional[str] = None
    quoted_comment_content: Optional[str] = None
    quoted_comment_author: Optional[str] = None
    quoted_comment_blog_url: Optional[str] = None
    verified: Optional[bool] = None
    verification_token: Optional[str] = None


class Comment(CommentBase):
    id: int
    post_id: int
    verified: bool
    verification_token: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
