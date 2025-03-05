from sqlalchemy.orm import Session

from app.crud.comments import (
    create_comment,
    delete_comment,
    get_comment_by_id,
    get_comments_by_post_id,
    set_comment_verification_token,
    update_comment,
    verify_comment,
)
from app.schemas import CommentCreate, CommentUpdate


def test_create_comment(db_session: Session):
    try:
        comment_data = CommentCreate(
            content="Test comment",
            author_name="Test User",
            author_blog_url="https://example.com",
            post_id=1,
        )
        comment = create_comment(db_session, comment_data)
        assert comment.id is not None
        assert comment.content == "Test comment"
        assert comment.verified is False
    except Exception:
        db_session.rollback()
        raise


def test_get_comments_by_post_id(db_session: Session):
    try:
        comment_data1 = CommentCreate(
            content="Test comment 1",
            author_name="Test User",
            author_blog_url="https://example.com",
            post_id=1,
        )
        comment1 = create_comment(db_session, comment_data1)
        assert comment1.post_id == 1

        comment_data2 = CommentCreate(
            content="Test comment 2",
            author_name="Test User",
            author_blog_url="https://example.com",
            post_id=1,
        )
        comment2 = create_comment(db_session, comment_data2)
        assert comment2.post_id == 1

        verify_comment(db_session, comment1.id)
        verify_comment(db_session, comment2.id)

        comments = get_comments_by_post_id(db_session, post_id=1)
        assert len(comments) == 2
        assert comments[0].content == "Test comment 1"
        assert comments[1].content == "Test comment 2"

        no_comments = get_comments_by_post_id(db_session, post_id=999)
        assert len(no_comments) == 0
    except Exception:
        db_session.rollback()
        raise


def test_get_comment_by_id(db_session: Session):
    try:
        comment_data = CommentCreate(
            content="Test comment",
            author_name="Test User",
            author_blog_url="https://example.com",
            post_id=1,
        )
        created_comment = create_comment(db_session, comment_data)

        comment = get_comment_by_id(db_session, created_comment.id)
        assert comment.id == created_comment.id
        assert comment.content == "Test comment"

        non_existent = get_comment_by_id(db_session, 999)
        assert non_existent is None
    except Exception:
        db_session.rollback()
        raise


def test_update_comment(db_session: Session):
    try:
        comment_data = CommentCreate(
            content="Test comment",
            author_name="Test User",
            author_blog_url="https://example.com",
            post_id=1,
        )
        created_comment = create_comment(db_session, comment_data)

        update_data = CommentUpdate(content="Updated comment")
        updated_comment = update_comment(db_session, created_comment.id, update_data)
        assert updated_comment.content == "Updated comment"

        non_existent = update_comment(db_session, 999, update_data)
        assert non_existent is None
    except Exception:
        db_session.rollback()
        raise


def test_delete_comment(db_session: Session):
    try:
        comment_data = CommentCreate(
            content="Test comment",
            author_name="Test User",
            author_blog_url="https://example.com",
            post_id=1,
        )
        created_comment = create_comment(db_session, comment_data)

        result = delete_comment(db_session, created_comment.id)
        assert result is True
        assert get_comment_by_id(db_session, created_comment.id) is None

        result = delete_comment(db_session, 999)
        assert result is False
    except Exception:
        db_session.rollback()
        raise


def test_set_comment_verification_token(db_session: Session):
    try:
        comment_data = CommentCreate(
            content="Test comment",
            author_name="Test User",
            author_blog_url="https://example.com",
            post_id=1,
        )
        created_comment = create_comment(db_session, comment_data)

        updated_comment = set_comment_verification_token(
            db_session, created_comment.id, "test-token"
        )
        assert updated_comment.verification_token == "test-token"

        non_existent = set_comment_verification_token(db_session, 999, "test-token")
        assert non_existent is None
    except Exception:
        db_session.rollback()
        raise


def test_verify_comment(db_session: Session):
    try:
        comment_data = CommentCreate(
            content="Test comment",
            author_name="Test User",
            author_blog_url="https://example.com",
            post_id=1,
        )
        created_comment = create_comment(db_session, comment_data)

        verified_comment = verify_comment(db_session, created_comment.id)
        assert verified_comment.verified is True

        non_existent = verify_comment(db_session, 999)
        assert non_existent is None
    except Exception:
        db_session.rollback()
        raise
