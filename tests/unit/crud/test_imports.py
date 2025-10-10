import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.crud.imports import (
    parse_markdown_frontmatter,
    extract_title_from_content,
    generate_slug,
    import_markdown_post,
    import_multiple_markdown_posts,
)


class TestParseMarkdownFrontmatter:
    """Test frontmatter parsing functionality"""
    
    def test_parse_frontmatter_basic(self):
        """Test basic frontmatter parsing"""
        content = """---
title: Test Post
date: 2024-01-15
published: true
tags: test, example
---

# Test Post 

This is the content."""
        
        frontmatter, content_without = parse_markdown_frontmatter(content)
        
        assert frontmatter['title'] == 'Test Post'
        assert frontmatter['date'] == '2024-01-15'
        assert frontmatter['published'] == 'true'
        assert frontmatter['tags'] == 'test, example'
        assert '# Test Post' in content_without
        assert 'This is the content.' in content_without
    
    def test_parse_frontmatter_no_frontmatter(self):
        """Test content without frontmatter"""
        content = """# Test Post

This is the content."""
        
        frontmatter, content_without = parse_markdown_frontmatter(content)
        
        assert frontmatter == {}
        assert content_without == content
    
    def test_parse_frontmatter_incomplete(self):
        """Test content with incomplete frontmatter"""
        content = """---
title: Test Post
date: 2024-01-15

# Test Post

This is the content."""
        
        frontmatter, content_without = parse_markdown_frontmatter(content)
        
        assert frontmatter == {}
        assert content_without == content
    
    def test_parse_frontmatter_quoted_values(self):
        """Test frontmatter with quoted values"""
        content = """---
title: "Test Post"
description: 'A test post'
tags: "test, example"
---

# Test Post"""
        
        frontmatter, content_without = parse_markdown_frontmatter(content)
        
        assert frontmatter['title'] == 'Test Post'
        assert frontmatter['description'] == 'A test post'
        assert frontmatter['tags'] == 'test, example'


class TestExtractTitleFromContent:
    """Test title extraction from content"""
    
    def test_extract_title_from_heading(self):
        """Test extracting title from first heading"""
        content = """# My Awesome Post

This is the content."""
        
        title = extract_title_from_content(content)
        assert title == "My Awesome Post"
    
    def test_extract_title_no_heading(self):
        """Test content without heading"""
        content = """This is just content without a heading."""
        
        title = extract_title_from_content(content)
        assert title == "Untitled Post"
    
    def test_extract_title_multiple_headings(self):
        """Test extracting title from first heading when multiple exist"""
        content = """# First Heading

Some content.

## Second Heading

More content."""
        
        title = extract_title_from_content(content)
        assert title == "First Heading"


class TestGenerateSlug:
    """Test slug generation functionality"""
    
    def test_generate_slug_basic(self):
        """Test basic slug generation"""
        existing_slugs = []
        slug = generate_slug("My Awesome Post", existing_slugs)
        assert slug == "my-awesome-post"
    
    def test_generate_slug_with_special_chars(self):
        """Test slug generation with special characters"""
        existing_slugs = []
        slug = generate_slug("My Awesome Post!", existing_slugs)
        assert slug == "my-awesome-post"
    
    def test_generate_slug_unique(self):
        """Test slug generation with existing slugs"""
        existing_slugs = ["my-awesome-post", "my-awesome-post-1"]
        slug = generate_slug("My Awesome Post", existing_slugs)
        assert slug == "my-awesome-post-2"
    
    def test_generate_slug_empty_title(self):
        """Test slug generation with empty title"""
        existing_slugs = []
        slug = generate_slug("", existing_slugs)
        assert slug == ""


class TestImportMarkdownPost:
    """Test importing a single markdown post"""
    
    def test_import_post_basic(self, db_session: Session):
        """Test basic post import"""
        content = """---
title: Test Post
date: 2024-01-15
published: true
tags: test, example
---

# Test Post

This is the content."""
        
        post = import_markdown_post(db_session, content, "test.md")
        
        assert post.title == "Test Post"
        assert post.slug == "test-post"
        assert post.is_published is True
        assert post.tags == "test, example"
        assert "Test Post" in post.markdown_content
        assert "This is the content." in post.markdown_content
        assert post.content is not None  # HTML content should be generated
    
    def test_import_post_no_frontmatter(self, db_session: Session):
        """Test importing post without frontmatter"""
        content = """# My Post

This is the content."""
        
        post = import_markdown_post(db_session, content, "test.md")
        
        assert post.title == "My Post"
        assert post.slug == "my-post"
        assert post.is_published is False  # Default value
        assert post.tags == ""
    
    def test_import_post_with_custom_slug(self, db_session: Session):
        """Test importing post with custom slug"""
        content = """---
title: Test Post
slug: custom-slug
---

# Test Post

Content."""
        
        post = import_markdown_post(db_session, content, "test.md")
        
        assert post.slug == "custom-slug"
    
    def test_import_post_unique_slug(self, db_session: Session):
        """Test importing post with duplicate slug"""
        # Create existing post
        existing_content = """---
title: Existing Post
slug: test-post
---

# Existing Post

Content."""
        
        import_markdown_post(db_session, existing_content, "existing.md")
        
        # Import new post with same title
        new_content = """---
title: Test Post
---

# Test Post

New content."""
        
        post = import_markdown_post(db_session, new_content, "new.md")
        
        assert post.slug == "test-post-1"  # Should be unique
    
    def test_import_post_date_parsing(self, db_session: Session):
        """Test date parsing in frontmatter"""
        content = """---
title: Test Post
date: 2024-01-15
---

# Test Post

Content."""
        
        post = import_markdown_post(db_session, content, "test.md")
        
        assert post.published_at is not None
        assert post.published_at.year == 2024
        assert post.published_at.month == 1
        assert post.published_at.day == 15
    
    def test_import_post_boolean_fields(self, db_session: Session):
        """Test boolean field parsing"""
        content = """---
title: Test Post
published: true
page: true
no_index: true
---

# Test Post

Content."""
        
        post = import_markdown_post(db_session, content, "test.md")
        
        assert post.is_published is True
        assert post.is_page is True
        assert post.no_index is True
    
    def test_import_post_meta_fields(self, db_session: Session):
        """Test meta fields parsing"""
        content = """---
title: Test Post
description: Test description
keywords: test, keywords
canonical_url: https://example.com
og_image: https://example.com/image.jpg
---

# Test Post

Content."""
        
        post = import_markdown_post(db_session, content, "test.md")
        
        assert post.meta_description == "Test description"
        assert post.meta_keywords == "test, keywords"
        assert post.canonical_url == "https://example.com"
        assert post.og_image == "https://example.com/image.jpg"


class TestImportMultipleMarkdownPosts:
    """Test importing multiple markdown posts"""
    
    def test_import_multiple_posts(self, db_session: Session):
        """Test importing multiple posts"""
        files = [
            ("post1.md", """---
title: First Post
---

# First Post

Content 1."""),
            ("post2.md", """---
title: Second Post
---

# Second Post

Content 2.""")
        ]
        
        posts = import_multiple_markdown_posts(db_session, files)
        
        assert len(posts) == 2
        assert posts[0].title == "First Post"
        assert posts[1].title == "Second Post"
    
    def test_import_multiple_posts_with_error(self, db_session: Session):
        """Test importing multiple posts with one error"""
        files = [
            ("post1.md", """---
title: First Post
---

# First Post

Content 1."""),
            ("invalid.md", "Invalid content without proper structure"),
            ("post2.md", """---
title: Second Post
---

# Second Post

Content 2.""")
        ]
        
        posts = import_multiple_markdown_posts(db_session, files)
        
        # Should import 2 posts successfully, skip the invalid one
        assert len(posts) == 2
        assert posts[0].title == "First Post"
        assert posts[1].title == "Second Post"

