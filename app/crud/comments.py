from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Comment


def create_comment(db: Session, comment) -> Comment:
    db_comment = Comment(
        content=comment.content,
        author_name=comment.author_name,
        author_blog_url=comment.author_blog_url,
        post_id=comment.post_id,
        quoted_comment_content=comment.quoted_comment_content,
        quoted_comment_author=comment.quoted_comment_author,
        quoted_comment_blog_url=comment.quoted_comment_blog_url,
        verified=False,
        verification_token=None,
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


def get_comments_by_post_id(
    db: Session, post_id: int, verified=True, skip: int = 0, limit: int = 100
) -> List[Comment]:
    query = db.query(Comment).filter(Comment.post_id == post_id)
    if verified:
        query = query.filter(Comment.verified == verified)
    return query.order_by(Comment.created_at.asc()).offset(skip).limit(limit).all()


def get_comment_by_id(db: Session, comment_id: int) -> Optional[Comment]:
    return db.query(Comment).filter(Comment.id == comment_id).first()


def update_comment(db: Session, comment_id: int, comment_update) -> Optional[Comment]:
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not db_comment:
        return None

    update_data = comment_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_comment, key, value)

    db.commit()
    db.refresh(db_comment)
    return db_comment


def delete_comment(db: Session, comment_id: int) -> bool:
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if db_comment:
        db.delete(db_comment)
        db.commit()
        return True
    return False


def set_comment_verification_token(
    db: Session, comment_id: int, token: str
) -> Optional[Comment]:
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not db_comment:
        return None

    db_comment.verification_token = token
    db.commit()
    db.refresh(db_comment)
    return db_comment


def verify_comment(db: Session, comment_id: int) -> Optional[Comment]:
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not db_comment:
        return None

    db_comment.verified = True
    db.commit()
    db.refresh(db_comment)
    return db_comment
