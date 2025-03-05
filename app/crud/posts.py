from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app import utils
from app.models import Post


def create_post(db: Session, post) -> Post:
    html_content = utils.markdown_to_html(post.markdown_content)

    db_post = Post(
        title=post.title,
        slug=post.slug,
        markdown_content=post.markdown_content,
        content=html_content,
        is_published=post.is_published,
        is_page=post.is_page,
        tags=post.tags if hasattr(post, "tags") else "",
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


def get_posts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    published_only: bool = False,
    include_pages: bool = False,
    tag: str = None,
) -> List[Post]:
    query = db.query(Post)
    if published_only:
        query = query.filter(Post.is_published)
    if not include_pages:
        query = query.filter(~Post.is_page)
    if tag:
        query = query.filter(
            (Post.tags.ilike(f"%,{tag},%"))
            | (Post.tags.ilike(f"{tag},%"))
            | (Post.tags.ilike(f"%, {tag}"))
            | (Post.tags.ilike(f"%,{tag}"))
            | (Post.tags == tag)
        )
    return query.order_by(Post.created_at.desc()).offset(skip).limit(limit).all()


def get_pages(
    db: Session, skip: int = 0, limit: int = 100, published_only: bool = False
) -> List[Post]:
    query = db.query(Post).filter(Post.is_page)
    if published_only:
        query = query.filter(Post.is_published)
    return query.order_by(Post.title).offset(skip).limit(limit).all()


def get_post_by_id(db: Session, post_id: int) -> Optional[Post]:
    return db.query(Post).filter(Post.id == post_id).first()


def get_post_by_slug(db: Session, slug: str) -> Optional[Post]:
    return db.query(Post).filter(Post.slug == slug).first()


def update_post(db: Session, post_id: int, post_update) -> Optional[Post]:
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        return None

    update_data = post_update.model_dump(exclude_unset=True)

    # If markdown content is updated, regenerate HTML content
    if "markdown_content" in update_data:
        update_data["content"] = utils.markdown_to_html(update_data["markdown_content"])
        update_data["updated_at"] = datetime.utcnow()

    for key, value in update_data.items():
        setattr(db_post, key, value)

    db.commit()
    db.refresh(db_post)
    return db_post


def delete_post(db: Session, post_id: int) -> bool:
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if db_post:
        db.delete(db_post)
        db.commit()
        return True
    return False


def get_all_slugs(db: Session) -> List[str]:
    return [post.slug for post in db.query(Post.slug).all()]
