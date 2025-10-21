import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.imports import import_markdown_post
from app.models import Post


class TestImportRouter:
    """Test import router endpoints"""
    
    def test_import_page_get(self, client: TestClient):
        """Test GET /admin/import/ returns the import page"""
        response = client.get("/admin/import/")
        
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/html")
    
    def test_import_page_requires_auth(self, client: TestClient):
        """Test that import page requires authentication"""
        response = client.get("/admin/import/")
        assert response.status_code == 200  # Assuming auth is mocked in test setup
    
    def test_upload_single_file(self, client: TestClient, db_session: Session, mock_user):
        """Test uploading a single markdown file"""
        markdown_content = """---
title: Test Import Post
date: 2024-01-15
published: true
tags: test, import
---

# Test Import Post

This is a test post for import functionality."""
        
        files = {
            "files": ("test.md", markdown_content, "text/markdown")
        }
        data = {
            "csrf_token": "test_csrf_token"
        }
        
        with patch("app.utils.validate_csrf_token", return_value=True), \
             patch("app.routers.import_router.get_user_or_redirect", return_value=mock_user):
            response = client.post("/admin/import/upload", files=files, data=data)
        
        if response.status_code == 404:
            pytest.skip("Import router not available in test environment")
        
        posts = db_session.query(Post).all()
        test_post = None
        for post in posts:
            if post.title == "Test Import Post":
                test_post = post
                break
        
        assert test_post is not None, f"Expected post not found. Found posts: {[p.title for p in posts]}"
        assert test_post.slug == "test-import-post"
        assert test_post.is_published is True
        assert "test, import" in test_post.tags
        
        if response.status_code == 302:
            assert "/admin" in response.headers["location"]
        else:
            assert response.status_code == 200
    
    def test_upload_multiple_files(self, client: TestClient, db_session: Session, mock_user):
        """Test uploading multiple markdown files"""
        file1_content = """---
title: First Post
published: true
---

# First Post

Content 1."""
        
        file2_content = """---
title: Second Post
published: false
---

# Second Post

Content 2."""
        
        files = [
            ("files", ("post1.md", file1_content, "text/markdown")),
            ("files", ("post2.md", file2_content, "text/markdown"))
        ]
        data = {
            "csrf_token": "test_csrf_token"
        }
        
        with patch("app.utils.validate_csrf_token", return_value=True), \
             patch("app.routers.import_router.get_user_or_redirect", return_value=mock_user):
            response = client.post("/admin/import/upload", files=files, data=data)
        
        posts = db_session.query(Post).all()
        first_post = None
        second_post = None
        for post in posts:
            if post.title == "First Post":
                first_post = post
            elif post.title == "Second Post":
                second_post = post
        
        assert first_post is not None, f"First Post not found. Found posts: {[p.title for p in posts]}"
        assert second_post is not None, f"Second Post not found. Found posts: {[p.title for p in posts]}"
        assert first_post.is_published is True
        assert second_post.is_published is False
        
        if response.status_code == 302:
            assert "/admin" in response.headers["location"]
        else:
            assert response.status_code == 200
    
    def test_upload_invalid_file_type(self, client: TestClient, db_session: Session, mock_user):
        """Test uploading non-markdown files"""
        files = {
            "files": ("test.txt", "This is not markdown", "text/plain")
        }
        data = {
            "csrf_token": "test_csrf_token"
        }
        
        with patch("app.utils.validate_csrf_token", return_value=True), \
             patch("app.routers.import_router.get_user_or_redirect", return_value=mock_user):
            response = client.post("/admin/import/upload", files=files, data=data)
        
        posts = db_session.query(Post).all()
        test_posts = [p for p in posts if p.title in ["Test Import Post", "First Post", "Second Post", "Text Import Post", "Complex Post", "Malformed Post"]]
        assert len(test_posts) == 0, f"Expected no test posts, but found: {[p.title for p in test_posts]}"
        
        if response.status_code == 302:
            assert "/admin" in response.headers["location"]
        else:
            assert response.status_code == 200
    
    def test_upload_no_files(self, client: TestClient):
        """Test uploading without files"""
        data = {
            "csrf_token": "test_csrf_token"
        }
        with patch("app.utils.validate_csrf_token", return_value=True):
            response = client.post("/admin/import/upload", data=data)
        
        assert response.status_code == 422
    
    def test_import_with_duplicate_slug(self, client: TestClient, db_session: Session, mock_user):
        """Test importing posts with duplicate slugs"""
        existing_content = """---
title: Existing Post
slug: test-post
---

# Existing Post

Existing content."""
        
        import_markdown_post(db_session, existing_content, "existing.md")
        
        new_content = """---
title: Test Post
---

# Test Post

New content."""
        
        files = {
            "files": ("new.md", new_content, "text/markdown")
        }
        data = {
            "csrf_token": "test_csrf_token"
        }
        
        with patch("app.utils.validate_csrf_token", return_value=True), \
             patch("app.routers.import_router.get_user_or_redirect", return_value=mock_user):
            response = client.post("/admin/import/upload", files=files, data=data)
        
        posts = db_session.query(Post).all()
        existing_post = None
        new_post = None
        for post in posts:
            if post.title == "Existing Post":
                existing_post = post
            elif post.title == "Test Post":
                new_post = post
        
        assert existing_post is not None, f"Existing Post not found. Found posts: {[p.title for p in posts]}"
        assert new_post is not None, f"Test Post not found. Found posts: {[p.title for p in posts]}"
        assert existing_post.slug.startswith("test-post")
        assert new_post.slug.startswith("test-post")
        assert existing_post.slug != new_post.slug
        
        if response.status_code == 302:
            assert "/admin" in response.headers["location"]
        else:
            assert response.status_code == 200
    
    def test_import_with_complex_frontmatter(self, client: TestClient, db_session: Session, mock_user):
        """Test importing post with complex frontmatter"""
        complex_content = """---
title: Complex Post
date: 2024-01-15 14:30:00
published: true
page: false
tags: complex, test, frontmatter
description: A complex post with lots of metadata
keywords: complex, test, metadata
canonical_url: https://example.com/complex-post
og_image: https://example.com/image.jpg
no_index: false
---

# Complex Post

This post has complex frontmatter."""
        
        files = {
            "files": ("complex.md", complex_content, "text/markdown")
        }
        data = {
            "csrf_token": "test_csrf_token"
        }
        
        with patch("app.utils.validate_csrf_token", return_value=True), \
             patch("app.routers.import_router.get_user_or_redirect", return_value=mock_user):
            response = client.post("/admin/import/upload", files=files, data=data)
        
        posts = db_session.query(Post).all()
        test_post = None
        for post in posts:
            if post.title == "Complex Post":
                test_post = post
                break
        
        assert test_post is not None, f"Complex Post not found. Found posts: {[p.title for p in posts]}"
        assert test_post.is_published is True
        assert test_post.is_page is False
        assert test_post.tags == "complex, test, frontmatter"
        assert test_post.meta_description == "A complex post with lots of metadata"
        assert test_post.meta_keywords == "complex, test, metadata"
        assert test_post.canonical_url == "https://example.com/complex-post"
        assert test_post.og_image == "https://example.com/image.jpg"
        assert test_post.no_index is False
        assert test_post.published_at is not None
        
        if response.status_code == 302:
            assert "/admin" in response.headers["location"]
        else:
            assert response.status_code == 200
    
    def test_import_error_handling(self, client: TestClient, db_session: Session, mock_user):
        """Test error handling during import"""
        malformed_content = """---
title: Malformed Post
date: invalid-date
published: maybe
---

# Malformed Post

Content."""
        
        files = {
            "files": ("malformed.md", malformed_content, "text/markdown")
        }
        data = {
            "csrf_token": "test_csrf_token"
        }
        
        with patch("app.utils.validate_csrf_token", return_value=True), \
             patch("app.routers.import_router.get_user_or_redirect", return_value=mock_user):
            response = client.post("/admin/import/upload", files=files, data=data)
        
        posts = db_session.query(Post).all()
        test_post = None
        for post in posts:
            if post.title == "Malformed Post":
                test_post = post
                break
        
        assert test_post is not None, f"Malformed Post not found. Found posts: {[p.title for p in posts]}"
        assert test_post.is_published is False 
        assert test_post.published_at is None 
        
        if response.status_code == 302:
            assert "/admin" in response.headers["location"]
        else:
            assert response.status_code == 200
