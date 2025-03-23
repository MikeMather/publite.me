from unittest.mock import MagicMock, patch

import pytest
from fastapi import status


def test_get_post_endpoint(client, mock_post, mock_settings):
    """Test getting a published post with proper settings configuration."""
    response = client.get(f"/blog/{mock_post.slug}")
    assert response.status_code == status.HTTP_200_OK
    assert mock_post.title in response.text


def mock_post_not_found(client, mock_settings):
    """Test requesting a non-existent post."""
    response = client.get("/blog/non-existent-post")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_root_endpoint_with_home_page(client, mock_post, mock_settings):
    """Test root endpoint redirects to home page when set."""
    mock_post.is_page = True
    mock_settings.home_page_id = mock_post.id

    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.url == f"http://testserver/{mock_post.slug}"


def test_root_endpoint_without_home_page(client, mock_settings):
    """Test root endpoint redirects to blog when no home page is set."""
    mock_settings.home_page_id = None

    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.url == "http://testserver/blog"


def test_sitemap_endpoint(client, mock_post, mock_settings):
    """Test sitemap.xml endpoint returns XML with posts."""
    response = client.get("/sitemap.xml")
    assert response.status_code == status.HTTP_200_OK
    assert "application/xml" in response.headers["content-type"]
    assert mock_post.slug in response.text


def test_rss_feed_enabled(client, mock_post, mock_settings):
    """Test RSS feed endpoint returns XML when enabled."""
    mock_settings.rss_enabled = True

    response = client.get("/rss")
    assert response.status_code == status.HTTP_200_OK
    assert "application/xml" in response.headers["content-type"]
    assert mock_post.title in response.text
    assert mock_settings.blog_title in response.text
    assert mock_settings.blog_description in response.text
    assert mock_post.title in response.text
    assert mock_post.meta_description in response.text
    assert f"<link>http://testserver/blog/{mock_post.slug}</link>" in response.text


def test_rss_feed_disabled(client, mock_settings):
    """Test RSS feed endpoint returns 404 when disabled."""
    mock_settings.rss_enabled = False

    response = client.get("/rss")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_blog_home_no_tag(client, mock_post, mock_settings):
    """Test blog home endpoint returns posts without tag filter."""
    response = client.get("/blog")
    assert response.status_code == status.HTTP_200_OK
    assert mock_post.title in response.text
    assert mock_settings.blog_title in response.text


def test_blog_home_with_tag(client, mock_post, mock_settings, db_session):
    """Test blog home endpoint returns posts filtered by tag."""
    # Add a tag to the test post
    mock_post.tags = "test-tag"
    db_session.commit()
    response = client.get("/blog?tag=test-tag")
    assert response.status_code == status.HTTP_200_OK
    assert mock_post.title in response.text
    assert "test-tag" in response.text


def test_blog_post_unpublished(client, mock_post, mock_settings):
    """Test blog post endpoint returns 404 for unpublished posts."""
    mock_post.is_published = False
    response = client.get(f"/blog/{mock_post.slug}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_blog_post_is_page(client, mock_post, mock_settings):
    """Test blog post endpoint returns 404 for pages."""
    mock_post.is_page = True

    response = client.get(f"/blog/{mock_post.slug}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_comment_comments_disabled(client, mock_post, mock_settings):
    """Test create comment endpoint returns 422 when comments are disabled."""
    mock_settings.comments_enabled = False

    with patch("app.utils.validate_csrf_token", return_value=True):
        response = client.post(
            f"/blog/{mock_post.slug}/comment",
            data={
                "content": "Test comment",
                "csrf_token": "valid_token",
            },
        )
        assert response.status_code == 422


def test_create_comment_invalid_csrf(client, mock_post, mock_settings):
    """Test create comment endpoint returns 403 with invalid CSRF token."""
    with patch("app.utils.validate_csrf_token", return_value=False):
        response = client.post(
            f"/blog/{mock_post.slug}/comment",
            data={
                "content": "Test comment",
                "author_name": "Test Author",
                "csrf_token": "invalid_token",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_comment_post_not_found(client, mock_settings):
    """Test create comment endpoint returns 404 for non-existent post."""
    with patch("app.utils.validate_csrf_token", return_value=True):
        response = client.post(
            "/blog/non-existent-post/comment",
            data={
                "content": "Test comment",
                "author_name": "Test Author",
                "csrf_token": "valid_token",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_comment_success_anonymous(client, mock_post, mock_settings, db_session):
    """Test create comment endpoint creates comment successfully for anonymous user."""
    mock_settings.comments_enabled = True
    mock_settings.allow_anonymous_comments = True

    with patch("app.utils.validate_csrf_token", return_value=True):
        response = client.post(
            f"/blog/{mock_post.slug}/comment",
            data={
                "content": "Test comment",
                "author_name": "Test Author",
                "csrf_token": "valid_token",
            },
        )
        assert response.url == f"http://testserver/blog/{mock_post.slug}"


# def test_create_comment_with_blog_url(client, mock_post, mock_settings, db_session):
#     """Test create comment endpoint with blog URL redirects to verification."""
#     mock_settings.comments_enabled = True
#     mock_post.is_page = False
#     mock_post.is_published = True
#     db_session.commit()

#     with patch("app.utils.validate_csrf_token", return_value=True):
#         with patch("secrets.token_hex", return_value="mock_nonce"):
#             with patch("time.time", return_value=1000000):
#                 response = client.post(
#                     f"/blog/{mock_post.slug}/comment",
#                     data={
#                         "content": "Test comment",
#                         "author_name": "Test Author",
#                         "author_blog_url": "example.com",
#                         "csrf_token": "valid_token",
#                     },
#                 )
#                 print(response.text)
#                 assert "example.com/verify-comment" in response.headers["location"]


# def test_create_comment_with_quoted_comment(
#     client, mock_post, mock_settings, db_session
# ):
#     """Test create comment endpoint with quoted comment."""
#     mock_settings.comments_enabled = True
#     mock_settings.allow_anonymous_comments = True

#     # First create a comment to quote
#     with patch("app.utils.validate_csrf_token", return_value=True):
#         client.post(
#             f"/blog/{mock_post.slug}/comment",
#             data={
#                 "content": "Original comment",
#                 "author_name": "Original Author",
#                 "csrf_token": "valid_token",
#             },
#         )

#     # Get the comment ID (should be 1)
#     quoted_comment_id = 1

#     # Now create a comment quoting the first one
#     with patch("app.utils.validate_csrf_token", return_value=True):
#         response = client.post(
#             f"/blog/{mock_post.slug}/comment",
#             data={
#                 "content": "Reply comment",
#                 "author_name": "Reply Author",
#                 "quoted_comment_id": str(quoted_comment_id),
#                 "csrf_token": "valid_token",
#             },
#         )
#         assert response.status_code == status.HTTP_303_SEE_OTHER
#         assert response.headers["location"] == f"/blog/{mock_post.slug}"


def test_verify_comment_callback_invalid_challenge(client, mock_post):
    """Test verify comment callback with invalid challenge."""
    response = client.get(
        f"/blog/{mock_post.slug}/verify-callback?challenge=invalid&signature=invalid"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@patch("base64.urlsafe_b64decode")
def test_verify_comment_callback_expired_challenge(mock_decode, client, mock_post):
    """Test verify comment callback with expired challenge."""
    mock_decode.return_value.decode.return_value = '{"comment_id": 1, "timestamp": 0}'

    response = client.get(
        f"/blog/{mock_post.slug}/verify-callback?challenge=valid&signature=valid"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@patch("requests.get")
@patch("json.loads")
@patch("base64.urlsafe_b64decode")
def test_verify_comment_callback_success(
    mock_decode, mock_loads, mock_get, client, mock_post, mock_settings, db_session
):
    """Test verify comment callback with valid challenge and signature."""
    from app.models import Comment

    comment = Comment(
        content="Test comment",
        author_name="Test Author",
        author_blog_url="example.com",
        post_id=mock_post.id,
        verification_token="valid_challenge",
    )
    db_session.add(comment)
    db_session.commit()

    # Mock the decoded challenge
    challenge_data = {
        "comment_id": comment.id,
        "timestamp": int(pytest.importorskip("time").time()) - 60,  # 1 minute ago
        "author_blog_url": "example.com",
    }
    mock_decode.return_value.decode.return_value = (
        '{"comment_id": 1, "timestamp": 1000000, "author_blog_url": "example.com"}'
    )
    mock_loads.return_value = challenge_data

    # Mock the public key request
    mock_response = MagicMock()
    mock_response.json.return_value = {"public_key": "mock_public_key"}
    mock_get.return_value = mock_response

    # Mock the signature verification
    with patch.object(mock_settings, "verify_signature", return_value=True):
        response = client.get(
            f"/blog/{mock_post.slug}/verify-callback?challenge=valid_challenge&signature=valid"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.url == f"http://testserver/blog/{mock_post.slug}"


def test_get_public_key(client, mock_settings):
    """Test get public key endpoint."""
    mock_settings.public_key = "test_public_key"

    response = client.get("/public-key")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"public_key": "test_public_key"}


def test_delete_comment_invalid_csrf(client, mock_post, mock_settings, mock_user):
    """Test delete comment endpoint with invalid CSRF token."""
    with patch("app.utils.validate_csrf_token", return_value=False):
        response = client.post(
            f"/blog/{mock_post.slug}/comment/1/delete",
            data={"csrf_token": "invalid_token"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_comment_not_found(client, mock_post, mock_settings, mock_user):
    """Test delete comment endpoint with non-existent comment."""
    with patch("app.utils.validate_csrf_token", return_value=True):
        response = client.post(
            f"/blog/{mock_post.slug}/comment/999/delete",
            data={"csrf_token": "valid_token"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_comment_success(
    client, mock_post, mock_settings, mock_user, db_session
):
    """Test delete comment endpoint successfully deletes comment."""
    # Create a comment to delete
    from app.models import Comment

    comment = Comment(
        content="Test comment", author_name="Test Author", post_id=mock_post.id
    )
    db_session.add(comment)
    db_session.commit()

    with patch("app.utils.validate_csrf_token", return_value=True):
        response = client.post(
            f"/blog/{mock_post.slug}/comment/{comment.id}/delete",
            data={"csrf_token": "valid_token"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.url == f"http://testserver/blog/{mock_post.slug}"


def test_root_page_not_found(client, mock_settings):
    """Test root page endpoint returns 404 for non-existent page."""
    response = client.get("/non-existent-page")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_root_page_not_published(client, mock_post, mock_settings):
    """Test root page endpoint returns 404 for unpublished page."""
    mock_post.is_page = True
    mock_post.is_published = False

    response = client.get(f"/{mock_post.slug}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_root_page_not_a_page(client, mock_post, mock_settings):
    """Test root page endpoint returns 404 for non-page post."""
    mock_post.is_page = False
    mock_post.is_published = True

    response = client.get(f"/{mock_post.slug}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_root_page_success(client, mock_post, mock_settings):
    """Test root page endpoint returns page successfully."""
    mock_post.is_page = True
    mock_post.is_published = True

    response = client.get(f"/{mock_post.slug}")
    assert response.status_code == status.HTTP_200_OK
    assert mock_post.title in response.text
