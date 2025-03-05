import base64
import json
import secrets
import time
from datetime import datetime
from typing import Optional

import requests
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app import models, schemas, utils
from app.auth import SECRET_KEY
from app.crud import comments, posts, settings
from app.database import get_db
from app.routers.admin_router import get_user, get_user_or_redirect

router = APIRouter(tags=["blog"])


@router.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    blog_settings = request.state.settings

    # If a home page is set and exists, redirect to that page
    if blog_settings.home_page_id:
        home_page = posts.get_post_by_id(db, blog_settings.home_page_id)
        if home_page and home_page.is_published and home_page.is_page:
            return RedirectResponse(url=f"/{home_page.slug}")

    return RedirectResponse(url="/blog")


@router.get("/sitemap.xml", response_class=Response)
async def sitemap(request: Request, db: Session = Depends(get_db)):
    all_posts = posts.get_posts(db, published_only=True, include_pages=False)
    all_pages = posts.get_pages(db, published_only=True)

    return request.state.templates.TemplateResponse(
        "blog/sitemap.xml",
        {"request": request, "posts": all_posts, "pages": all_pages},
        media_type="application/xml",
    )


@router.get("/rss", response_class=Response)
async def rss_feed(request: Request, db: Session = Depends(get_db)):
    if not request.state.settings.rss_enabled:
        raise HTTPException(status_code=404, detail="RSS feed not enabled")

    all_posts = posts.get_posts(db, published_only=True, include_pages=False)
    now = datetime.utcnow()
    return request.state.templates.TemplateResponse(
        "blog/rss.xml",
        {
            "request": request,
            "settings": request.state.settings,
            "posts": all_posts,
            "now": now,
        },
        media_type="application/xml",
    )


@router.get("/blog", response_class=HTMLResponse)
async def blog_home(request: Request, tag: str = None, db: Session = Depends(get_db)):
    all_posts = posts.get_posts(db, published_only=True, include_pages=False, tag=tag)
    blog_settings = settings.get_settings(db)

    navigation_html = utils.markdown_to_html(blog_settings.navigation_markdown)
    footer_html = utils.markdown_to_html(blog_settings.footer_markdown)

    return request.state.templates.TemplateResponse(
        "blog/index.html",
        {
            "request": request,
            "posts": all_posts,
            "settings": blog_settings,
            "navigation_html": navigation_html,
            "footer_html": footer_html,
            "title": (
                blog_settings.blog_title
                if not tag
                else f"Posts tagged '{tag}' - {blog_settings.blog_title}"
            ),
            "current_tag": tag,
        },
    )


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: Optional[models.User] = Depends(get_user),
):
    post = posts.get_post_by_slug(db, slug)
    if not post or not post.is_published or post.is_page:
        raise HTTPException(status_code=404, detail="Post not found")

    blog_settings = settings.get_settings(db)
    navigation_html = utils.markdown_to_html(blog_settings.navigation_markdown)
    footer_html = utils.markdown_to_html(blog_settings.footer_markdown)

    comms = []
    verified_comments_only = not blog_settings.allow_anonymous_comments
    if blog_settings.comments_enabled:
        comms = comments.get_comments_by_post_id(
            db, post.id, verified=verified_comments_only
        )

    is_admin = admin_user is not None

    return request.state.templates.TemplateResponse(
        "blog/post.html",
        {
            "request": request,
            "post": post,
            "settings": blog_settings,
            "navigation_html": navigation_html,
            "footer_html": footer_html,
            "title": f"{post.title} - {blog_settings.blog_title}",
            "comments": comms,
            "is_admin": is_admin,
        },
    )


@router.post("/blog/{slug}/comment")
async def create_comment(
    slug: str,
    request: Request,
    content: str = Form(...),
    author_name: str = Form(...),
    author_blog_url: Optional[str] = Form(None),
    quoted_comment_id: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    cookie_token = request.state.csrf_token
    if not cookie_token or not utils.validate_csrf_token(csrf_token, SECRET_KEY):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    if quoted_comment_id == "":
        quoted_comment_id = None
    elif quoted_comment_id is not None:
        try:
            quoted_comment_id = int(quoted_comment_id)
        except ValueError:
            quoted_comment_id = None
    post = posts.get_post_by_slug(db, slug)
    if not post or not post.is_published or post.is_page:
        raise HTTPException(status_code=404, detail="Post not found")

    blog_settings = settings.get_settings(db)
    if not blog_settings.comments_enabled:
        raise HTTPException(status_code=403, detail="Comments are disabled")

    quoted_comment_content = None
    quoted_comment_author = None
    quoted_comment_blog_url = None

    if quoted_comment_id:
        quoted_comment = comments.get_comment_by_id(db, quoted_comment_id)
        if quoted_comment and quoted_comment.post_id == post.id:
            quoted_comment_content = quoted_comment.content
            quoted_comment_author = quoted_comment.author_name
            quoted_comment_blog_url = quoted_comment.author_blog_url

    if author_blog_url:
        author_blog_url = author_blog_url.strip()
        if author_blog_url.startswith(("http://", "https://")):
            author_blog_url = author_blog_url.split("//", 1)[1]

    comment_data = schemas.CommentCreate(
        content=content.strip(),
        author_name=author_name.strip(),
        author_blog_url=author_blog_url,
        post_id=post.id,
        quoted_comment_content=quoted_comment_content,
        quoted_comment_author=quoted_comment_author,
        quoted_comment_blog_url=quoted_comment_blog_url,
    )

    comment = comments.create_comment(db, comment_data)

    if author_blog_url and (
        not blog_settings.allow_anonymous_comments or author_blog_url
    ):
        challenge = {
            "comment_id": comment.id,
            "post_id": post.id,
            "post_slug": slug,
            "author_name": author_name,
            "author_blog_url": author_blog_url,
            "timestamp": int(time.time()),
            "nonce": secrets.token_hex(16),
        }

        challenge_json = json.dumps(challenge)

        challenge_encoded = base64.urlsafe_b64encode(challenge_json.encode()).decode()

        comments.set_comment_verification_token(db, comment.id, challenge_encoded)

        callback_url = request.url_for("verify_comment_callback", slug=slug)
        redirect_url = (
            f"https://{author_blog_url.rstrip('/')}/verify-comment?"
            f"challenge={challenge_encoded}&callback={callback_url}"
        )

        return RedirectResponse(url=redirect_url, status_code=303)

    return RedirectResponse(url=f"/blog/{slug}", status_code=303)


@router.get("/blog/{slug}/verify-callback")
async def verify_comment_callback(
    slug: str,
    request: Request,
    challenge: str,
    signature: str,
    db: Session = Depends(get_db),
):
    try:
        challenge_json = base64.urlsafe_b64decode(challenge.encode()).decode()
        challenge_data = json.loads(challenge_json)

        comment_id = challenge_data.get("comment_id")
        comment = comments.get_comment_by_id(db, comment_id)

        if not comment or comment.verification_token != challenge:
            raise HTTPException(status_code=400, detail="Invalid challenge")

        current_time = int(time.time())
        challenge_time = challenge_data.get("timestamp", 0)
        if current_time - challenge_time > 600:
            raise HTTPException(status_code=400, detail="Challenge expired")

        author_blog_url = challenge_data.get("author_blog_url")
        if not author_blog_url or author_blog_url != comment.author_blog_url:
            raise HTTPException(status_code=400, detail="Blog URL mismatch")

        try:
            public_key_url = f"https://{author_blog_url.rstrip('/')}/public-key"
            response = requests.get(public_key_url, timeout=15)
            response.raise_for_status()
            public_key_data = response.json()
            public_key = public_key_data.get("public_key")

            blog_settings = settings.get_settings(db)
            clean_signature = signature.replace(" ", "+")
            if blog_settings.verify_signature(
                public_key, challenge_json, clean_signature
            ):
                comments.verify_comment(db, comment_id)
                return RedirectResponse(url=f"/blog/{slug}", status_code=303)
            else:
                raise HTTPException(status_code=400, detail="Invalid signature")
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to fetch public key: {str(e)}"
            )

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid challenge format")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Verification failed: {str(e)}")


@router.get("/verify-comment")
async def verify_comment_request(
    request: Request,
    challenge: str,
    callback: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_user_or_redirect),
):
    """
    Handle verification requests from other blogs.
    This endpoint is called when a user comments on another blog using this blog's URL.
    """
    blog_settings = settings.get_settings(db)

    try:
        challenge_json = base64.urlsafe_b64decode(challenge.encode()).decode()
        challenge_data = json.loads(challenge_json)

        signature = blog_settings.sign_data(challenge_json)

        redirect_url = f"{callback}?challenge={challenge}&signature={signature}"

        return request.state.templates.TemplateResponse(
            "blog/verify_comment.html",
            {
                "request": request,
                "settings": blog_settings,
                "challenge_data": challenge_data,
                "redirect_url": redirect_url,
            },
        )

    except Exception as e:
        return request.state.templates.TemplateResponse(
            "blog/verify_comment.html",
            {
                "request": request,
                "settings": settings,
                "error": str(e),
            },
        )


@router.get("/public-key", response_class=JSONResponse)
async def get_public_key(request: Request, db: Session = Depends(get_db)):
    blog_settings = settings.get_settings(db)
    return {"public_key": blog_settings.public_key}


@router.post("/blog/{slug}/comment/{comment_id}/delete")
async def delete_comment(
    slug: str,
    comment_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(get_user),
):
    cookie_token = request.state.csrf_token
    if not cookie_token or not utils.validate_csrf_token(csrf_token, SECRET_KEY):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    post = posts.get_post_by_slug(db, slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    success = comments.delete_comment(db, comment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")

    return RedirectResponse(url=f"/blog/{slug}", status_code=303)


@router.get("/{slug}", response_class=HTMLResponse)
async def root_page(slug: str, request: Request, db: Session = Depends(get_db)):
    page = posts.get_post_by_slug(db, slug)
    if not page or not page.is_published or not page.is_page:
        raise HTTPException(status_code=404, detail="Page not found")

    blog_settings = settings.get_settings(db)
    navigation_html = utils.markdown_to_html(blog_settings.navigation_markdown)
    footer_html = utils.markdown_to_html(blog_settings.footer_markdown)

    return request.state.templates.TemplateResponse(
        "blog/page.html",
        {
            "request": request,
            "page": page,
            "settings": blog_settings,
            "navigation_html": navigation_html,
            "footer_html": footer_html,
            "title": f"{page.title} - {blog_settings.blog_title}",
        },
    )
