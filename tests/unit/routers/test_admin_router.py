from unittest.mock import patch

import pytest
from fastapi import status

from app.models import Post, Settings, User


def test_setup_page_when_needed(client, db_session):
    """Test setup page is shown when no users exist."""
    response = client.get("/admin/setup")
    assert response.status_code == status.HTTP_200_OK
    assert "Setup Admin Account" in response.text


def test_setup_page_when_not_needed(client, mock_user):
    """Test setup page redirects when users exist."""
    response = client.get("/admin/setup")
    assert response.url == "http://testserver/admin/login"


def test_setup_submit_success(client, db_session):
    """Test successful admin account creation."""
    response = client.post(
        "/admin/setup",
        data={
            "username": "admin",
            "password": "password123",
        },
    )
    assert response.url == "http://testserver/admin/login"

    user = db_session.query(User).first()
    assert user is not None
    assert user.username == "admin"
    assert user.is_setup_complete is True

    settings = db_session.query(Settings).first()
    assert settings is not None


def test_setup_submit_when_not_needed(client, mock_user):
    """Test setup submit redirects when users exist."""
    response = client.post(
        "/admin/setup",
        data={
            "username": "admin2",
            "password": "password123",
        },
    )
    assert response.url == "http://testserver/admin/login"


def test_login_page(client):
    """Test login page is shown."""
    response = client.get("/admin/login")
    assert response.status_code == status.HTTP_200_OK
    assert "Admin Login" in response.text


def test_login_submit_failure(client, mock_user):
    """Test failed login."""
    response = client.post(
        "/admin/login",
        data={
            "username": "testuser",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert "Invalid username or password" in response.text


def test_dashboard(client, mock_user, mock_post):
    """Test dashboard page shows posts."""
    response = client.get("/admin/dashboard")
    assert response.status_code == status.HTTP_200_OK
    assert "Admin Dashboard" in response.text
    assert mock_post.title in response.text


def test_new_post_page(client, mock_user):
    """Test new post page is shown."""
    response = client.get("/admin/posts/new")
    assert response.status_code == status.HTTP_200_OK
    assert "New Post" in response.text


def test_create_post(client, mock_user, db_session):
    """Test creating a new post."""
    response = client.post(
        "/admin/posts/new",
        data={
            "title": "Test Post",
            "markdown_content": "# Test Content",
            "is_published": "true",
        },
    )
    assert response.url == "http://testserver/admin/dashboard"

    # Verify post was created
    post = db_session.query(Post).first()
    assert post is not None
    assert post.title == "Test Post"
    assert post.is_published is True
    assert post.is_page is False


def test_edit_post_page(client, mock_user, mock_post):
    """Test edit post page shows post content."""
    with patch("app.routers.admin_router.get_user_or_redirect", return_value=mock_user):
        response = client.get(f"/admin/posts/{mock_post.id}/edit")
        assert response.status_code == status.HTTP_200_OK
        assert mock_post.title in response.text


def test_update_post(client, mock_user, mock_post):
    """Test updating a post."""
    with patch("app.routers.admin_router.get_user_or_redirect", return_value=mock_user):
        response = client.post(
            f"/admin/posts/{mock_post.id}/edit",
            data={
                "title": "Updated Title",
                "slug": mock_post.slug,
                "markdown_content": "# Updated Content",
                "is_published": "true",
            },
        )
        assert (
            response.url
            == f"http://testserver/admin/posts/{mock_post.id}/edit?success=true"
        )


def test_delete_post(client, mock_user, mock_post):
    """Test deleting a post."""
    with patch("app.routers.admin_router.get_user_or_redirect", return_value=mock_user):
        response = client.post(f"/admin/posts/{mock_post.id}/delete")
        assert response.url == "http://testserver/admin/dashboard"


def test_settings_page(client, mock_user, mock_settings):
    """Test settings page shows current settings."""
    with patch("app.routers.admin_router.get_user_or_redirect", return_value=mock_user):
        response = client.get("/admin/settings")
        assert response.status_code == status.HTTP_200_OK
        assert "Blog Settings" in response.text
        assert mock_settings.blog_title in response.text


def test_update_settings(client, mock_user, mock_settings, tmp_path):
    """Test updating blog settings."""
    with patch("app.routers.admin_router.get_user_or_redirect", return_value=mock_user):
        response = client.post(
            "/admin/settings",
            data={
                "blog_title": "Updated Blog Title",
                "blog_description": "Updated description",
                "theme": "default",
                "navigation_markdown": "[Home](/)",
                "footer_markdown": "Updated footer",
                "comments_enabled": "true",
                "allow_anonymous_comments": "false",
                "rss_enabled": "true",
            },
        )
        assert response.url == "http://testserver/admin/settings"


def test_new_page_page(client, mock_user):
    """Test new page page is shown."""
    with patch("app.routers.admin_router.get_user_or_redirect", return_value=mock_user):
        response = client.get("/admin/pages/new")
        assert response.status_code == status.HTTP_200_OK
        assert "New Page" in response.text


def test_create_page(client, mock_user, db_session):
    """Test creating a new page."""
    response = client.post(
        "/admin/pages/new",
        data={
            "title": "Test Page",
            "markdown_content": "# Test Content",
            "is_published": "true",
        },
    )
    assert response.url == "http://testserver/admin/pages"

    # Verify page was created
    page = db_session.query(Post).filter(Post.is_page).first()
    assert page is not None
    assert page.title == "Test Page"
    assert page.is_published is True
    assert page.is_page is True


def test_edit_page_page(client, mock_user, mock_post):
    """Test edit page page shows page content."""
    mock_post.is_page = True
    with patch("app.routers.admin_router.get_user_or_redirect", return_value=mock_user):
        response = client.get(f"/admin/pages/{mock_post.id}/edit")
        assert response.status_code == status.HTTP_200_OK
        assert mock_post.title in response.text


def test_update_page(client, mock_user, mock_post):
    """Test updating a page."""
    mock_post.is_page = True
    response = client.post(
        f"/admin/pages/{mock_post.id}/edit",
        data={
            "csrf_token": "test_csrf_token",
            "title": "Updated Title",
            "slug": mock_post.slug,
            "markdown_content": "# Updated Content",
            "is_published": "true",
        },
    )
    assert (
        response.url
        == f"http://testserver/admin/pages/{mock_post.id}/edit?success=true"
    )


def test_delete_page(client, mock_user, mock_post):
    """Test deleting a page."""
    mock_post.is_page = True
    response = client.post(f"/admin/pages/{mock_post.id}/delete")
    assert response.url == "http://testserver/admin/pages"


def test_admin_home_not_logged_in(client):
    """Test admin home redirects to login when not logged in."""
    response = client.get("/admin/dashboard")
    assert response.status_code == status.HTTP_200_OK
    assert "Setup" in response.text
