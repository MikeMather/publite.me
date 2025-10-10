import re
from datetime import datetime
from typing import List, Optional, Tuple
from urllib.parse import quote

from sqlalchemy.orm import Session

from app import utils
from app.models import Post


def parse_markdown_frontmatter(content: str) -> Tuple[dict, str]:
    """
    Parse frontmatter from markdown content.
    Returns (frontmatter_dict, content_without_frontmatter)
    """
    if not content.startswith('---'):
        return {}, content
    
    # Find the end of frontmatter
    end_marker = content.find('---', 3)
    if end_marker == -1:
        return {}, content
    
    frontmatter_text = content[3:end_marker]
    content_without_frontmatter = content[end_marker + 3:].lstrip('\n')
    
    frontmatter = {}
    for line in frontmatter_text.split('\n'):
        line = line.strip()
        if ':' in line and line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"\'')
            frontmatter[key] = value
    
    return frontmatter, content_without_frontmatter


def extract_title_from_content(content: str) -> str:
    """
    Extract title from markdown content (first # heading)
    """
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()
    return "Untitled Post"


def generate_slug(title: str, existing_slugs: List[str]) -> str:
    """
    Generate a unique slug from title
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    slug = slug.strip('-')
    
    # Ensure uniqueness
    original_slug = slug
    counter = 1
    while slug in existing_slugs:
        slug = f"{original_slug}-{counter}"
        counter += 1
    
    return slug


def import_markdown_post(
    db: Session, 
    markdown_content: str, 
    filename: Optional[str] = None
) -> Post:
    """
    Import a single markdown post from content.
    """
    # Check if content has basic structure
    if not markdown_content.strip():
        raise ValueError("Empty content")
    
    # Parse frontmatter
    frontmatter, content = parse_markdown_frontmatter(markdown_content)
    
    # Extract title
    title = frontmatter.get('title', extract_title_from_content(content))
    if not title:
        title = filename.replace('.md', '') if filename else "Untitled Post"
    
    # Check if content has meaningful structure (either frontmatter or markdown)
    if not frontmatter and not content.strip():
        raise ValueError("Content has no meaningful structure")
    
    # Check if content has at least some markdown structure
    if not frontmatter and not any(line.strip().startswith('#') for line in content.split('\n')):
        # If no frontmatter and no headings, require at least some content
        if len(content.strip()) < 50:
            raise ValueError("Content too short or lacks structure")
    
    # Generate slug
    existing_slugs = [post.slug for post in db.query(Post.slug).all()]
    slug = frontmatter.get('slug', generate_slug(title, existing_slugs))
    
    # Ensure slug is unique
    original_slug = slug
    counter = 1
    while db.query(Post).filter(Post.slug == slug).first():
        slug = f"{original_slug}-{counter}"
        counter += 1
    
    # Parse other frontmatter fields
    is_published = frontmatter.get('published', 'false').lower() in ('true', '1', 'yes')
    is_page = frontmatter.get('page', 'false').lower() in ('true', '1', 'yes')
    tags = frontmatter.get('tags', '')
    if isinstance(tags, list):
        tags = ', '.join(tags)
    
    # Parse published date
    published_at = None
    if frontmatter.get('date'):
        try:
            # Try different date formats
            date_str = frontmatter['date']
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                try:
                    published_at = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
        except (ValueError, TypeError, KeyError):
            # Date parsing failed, leave published_at as None
            pass
    
    # Convert markdown to HTML
    html_content = utils.markdown_to_html(content)
    
    # Create post
    db_post = Post(
        title=title,
        slug=slug,
        markdown_content=content,
        content=html_content,
        is_published=is_published,
        published_at=published_at,
        is_page=is_page,
        tags=tags,
        meta_description=frontmatter.get('description', ''),
        meta_keywords=frontmatter.get('keywords', ''),
        canonical_url=frontmatter.get('canonical_url', ''),
        og_image=frontmatter.get('og_image', ''),
        no_index=frontmatter.get('no_index', 'false').lower() in ('true', '1', 'yes')
    )
    
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


def import_multiple_markdown_posts(
    db: Session, 
    markdown_files: List[Tuple[str, str]]  # List of (filename, content) tuples
) -> List[Post]:
    """
    Import multiple markdown posts.
    Returns list of created posts.
    """
    created_posts = []
    
    for filename, content in markdown_files:
        try:
            # Check if content has basic structure
            if not content.strip():
                print(f"Skipping {filename}: empty content")
                continue
                
            post = import_markdown_post(db, content, filename)
            created_posts.append(post)
        except Exception as e:
            # Log error but continue with other files
            print(f"Error importing {filename}: {e}")
            continue
    
    return created_posts


