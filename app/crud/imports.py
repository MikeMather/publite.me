import re
from datetime import datetime
from typing import List, Optional, Tuple
from urllib.parse import quote

import frontmatter
from sqlalchemy.orm import Session

from app import utils
from app.models import Post
    
import logging

logger = logging.getLogger(__name__)


def parse_markdown_frontmatter(content: str) -> Tuple[dict, str]:
    """
    Parse frontmatter from markdown content using python-frontmatter.
    Returns (frontmatter_dict, content_without_frontmatter)
    """
    try:
        post = frontmatter.loads(content)
        return post.metadata, post.content
    except Exception:
        return {}, content


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
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    slug = slug.strip('-')
    
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
    if not markdown_content.strip():
        raise ValueError("Empty content")
    
    frontmatter, content = parse_markdown_frontmatter(markdown_content)
    
    content = remove_one_line_comments(content)
    
    title = frontmatter.get('title', extract_title_from_content(content))
    if not title:
        title = filename.replace('.md', '') if filename else "Untitled Post"
    if not frontmatter and not content.strip():
        raise ValueError("Content has no meaningful structure")
    
    if not frontmatter and not any(line.strip().startswith('#') for line in content.split('\n')):
        if len(content.strip()) < 50:
            raise ValueError("Content too short or lacks structure")
    
    existing_slugs = [post.slug for post in db.query(Post.slug).all()]
    slug = frontmatter.get('slug', generate_slug(title, existing_slugs))
    
    original_slug = slug
    counter = 1
    while db.query(Post).filter(Post.slug == slug).first():
        slug = f"{original_slug}-{counter}"
        counter += 1
    
    published_value = frontmatter.get('published', False)
    if isinstance(published_value, bool):
        is_published = published_value
    else:
        is_published = str(published_value).lower() in ('true', '1', 'yes')
    
    page_value = frontmatter.get('page', False)
    if isinstance(page_value, bool):
        is_page = page_value
    else:
        is_page = str(page_value).lower() in ('true', '1', 'yes')
    
    tags = frontmatter.get('tags', '')
    if isinstance(tags, list):
        tags = ', '.join(tags)

    published_at = None
    if frontmatter.get('date'):
        date_value = frontmatter['date']
        if isinstance(date_value, datetime):
            published_at = date_value
        elif hasattr(date_value, 'date'):
            published_at = datetime.combine(date_value, datetime.min.time())
        else:
            try:
                date_str = str(date_value)
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        published_at = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
            except (ValueError, TypeError, KeyError):
                pass
    
    html_content = utils.markdown_to_html(content)
    
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
        no_index=frontmatter.get('no_index', False) if isinstance(frontmatter.get('no_index', False), bool) else str(frontmatter.get('no_index', 'false')).lower() in ('true', '1', 'yes')
    )
    
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

def import_multiple_markdown_posts(
    db: Session, 
    markdown_files: List[Tuple[str, str]]
) -> List[Post]:
    """
    Import multiple markdown posts.
    Returns list of created posts.
    """
    created_posts = []
    
    for filename, content in markdown_files:
        try:
            if not content.strip():
                logger.warning("Skipping %s: empty content", filename)
                continue
                
            post = import_markdown_post(db, content, filename)
            created_posts.append(post)
        except Exception as e:
            logger.error("Error importing %s: %s", filename, e, exc_info=True)
            continue
    
    return created_posts


