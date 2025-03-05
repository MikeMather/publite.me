from sqlalchemy.orm import Session

from app.crud.posts import (
    create_post,
    delete_post,
    get_all_slugs,
    get_pages,
    get_post_by_id,
    get_post_by_slug,
    get_posts,
    update_post,
)
from app.schemas import PostCreate, PostUpdate


def test_create_post(db_session: Session):
    post_data = PostCreate(
        title="Test Post",
        slug="test-post-create",
        markdown_content="# Test\nThis is a test post",
        is_published=True,
        is_page=False,
        tags="test,example",
    )

    post = create_post(db_session, post_data)
    assert post.id is not None
    assert post.title == "Test Post"
    assert post.slug == "test-post-create"
    assert post.markdown_content == "# Test\nThis is a test post"
    assert post.content == "<h1>Test</h1>\n<p>This is a test post</p>"
    assert post.is_published is True
    assert post.is_page is False
    assert post.tags == "test,example"


def test_get_posts(db_session: Session):
    post1 = PostCreate(
        title="Published Post",
        slug="published-post-1",
        markdown_content="Published content",
        is_published=True,
        is_page=False,
        tags="test",
    )
    post2 = PostCreate(
        title="Draft Post",
        slug="draft-post-1",
        markdown_content="Draft content",
        is_published=False,
        is_page=False,
    )
    post3 = PostCreate(
        title="Published Page",
        slug="published-page-1",
        markdown_content="Page content",
        is_published=True,
        is_page=True,
    )

    create_post(db_session, post1)
    create_post(db_session, post2)
    create_post(db_session, post3)

    all_posts = get_posts(db_session)
    assert len(all_posts) == 2
    assert all_posts[0].title == "Draft Post"
    assert all_posts[1].title == "Published Post"

    published_posts = get_posts(db_session, published_only=True)
    all_posts = get_posts(db_session)
    assert len(published_posts) == 1
    assert published_posts[0].title == "Published Post"

    all_content = get_posts(db_session, include_pages=True)
    assert len(all_content) == 3

    tagged_posts = get_posts(db_session, tag="test")
    assert len(tagged_posts) == 1
    assert tagged_posts[0].title == "Published Post"


def test_get_pages(db_session: Session):
    try:
        page1 = PostCreate(
            title="Published Page",
            slug="published-page-2",
            markdown_content="Page content",
            is_published=True,
            is_page=True,
        )
        page2 = PostCreate(
            title="Draft Page",
            slug="draft-page-2",
            markdown_content="Draft page content",
            is_published=False,
            is_page=True,
        )
        post = PostCreate(
            title="Regular Post",
            slug="regular-post-2",
            markdown_content="Post content",
            is_published=True,
            is_page=False,
        )

        create_post(db_session, page1)
        create_post(db_session, page2)
        create_post(db_session, post)

        all_pages = get_pages(db_session)
        assert len(all_pages) == 2
        assert all_pages[0].title == "Draft Page"
        assert all_pages[1].title == "Published Page"

        published_pages = get_pages(db_session, published_only=True)
        assert len(published_pages) == 1
        assert published_pages[0].title == "Published Page"
    except Exception:
        db_session.rollback()
        raise


def test_get_post_by_id(db_session: Session):
    try:
        post_data = PostCreate(
            title="Test Post",
            slug="test-post-by-id",
            markdown_content="Test content",
            is_published=True,
            is_page=False,
        )
        created_post = create_post(db_session, post_data)

        post = get_post_by_id(db_session, created_post.id)
        assert post is not None
        assert post.id == created_post.id
        assert post.title == "Test Post"

        non_existent = get_post_by_id(db_session, 999)
        assert non_existent is None
    except Exception:
        db_session.rollback()
        raise


def test_get_post_by_slug(db_session: Session):
    post_data = PostCreate(
        title="Test Post",
        slug="test-post-by-slug",
        markdown_content="Test content",
        is_published=True,
        is_page=False,
    )
    created_post = create_post(db_session, post_data)

    post = get_post_by_slug(db_session, "test-post-by-slug")
    assert post is not None
    assert post.id == created_post.id
    assert post.title == "Test Post"

    non_existent = get_post_by_slug(db_session, "non-existent")
    assert non_existent is None


def test_update_post(db_session: Session):
    post_data = PostCreate(
        title="Original Title",
        slug="original-slug-update",
        markdown_content="Original content",
        is_published=True,
        is_page=False,
        tags="original",
    )
    created_post = create_post(db_session, post_data)

    update_data = PostUpdate(
        title="Updated Title",
        markdown_content="# Updated\nNew content",
        is_published=False,
        tags="updated,test",
    )
    updated_post = update_post(db_session, created_post.id, update_data)

    assert updated_post is not None
    assert updated_post.title == "Updated Title"
    assert updated_post.markdown_content == "# Updated\nNew content"
    assert updated_post.content == "<h1>Updated</h1>\n<p>New content</p>"
    assert updated_post.is_published is False
    assert updated_post.tags == "updated,test"
    assert updated_post.slug == "original-slug-update"
    assert updated_post.updated_at is not None

    non_existent = update_post(db_session, 999, update_data)
    assert non_existent is None


def test_delete_post(db_session: Session):
    post_data = PostCreate(
        title="Test Post",
        slug="test-post-delete",
        markdown_content="Test content",
        is_published=True,
        is_page=False,
    )
    created_post = create_post(db_session, post_data)

    result = delete_post(db_session, created_post.id)
    assert result is True
    assert get_post_by_id(db_session, created_post.id) is None

    result = delete_post(db_session, 999)
    assert result is False


def test_get_all_slugs(db_session: Session):
    post1 = PostCreate(
        title="First Post",
        slug="first-post-slugs",
        markdown_content="First content",
        is_published=True,
        is_page=False,
    )
    post2 = PostCreate(
        title="Second Post",
        slug="second-post-slugs",
        markdown_content="Second content",
        is_published=False,
        is_page=False,
    )
    page = PostCreate(
        title="Test Page",
        slug="test-page-slugs",
        markdown_content="Page content",
        is_published=True,
        is_page=True,
    )

    create_post(db_session, post1)
    create_post(db_session, post2)
    create_post(db_session, page)

    slugs = get_all_slugs(db_session)
    assert len(slugs) == 3
    assert "first-post-slugs" in slugs
    assert "second-post-slugs" in slugs
    assert "test-page-slugs" in slugs
