import os
import secrets
import shutil
from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import schemas, utils
from app.auth import authenticate_user, get_password_hash
from app.crud import posts, settings, users
from app.database import get_db
from app.models import User
from app.session import get_session

router = APIRouter(prefix="/admin", tags=["admin"])


async def check_setup_needed(db: Session = Depends(get_db)):
    user_count = users.get_user_count(db)
    return user_count == 0


# Authentication middleware for admin routes
async def get_user_or_redirect(request: Request, db: Session = Depends(get_db)):
    setup_needed = await check_setup_needed(db)
    if setup_needed:
        if request.url.path != "/admin/setup":
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": "/admin/setup"},
            )
        return None

    session = await get_session(request)
    user_id = session.get("user_id")

    if not user_id:
        if request.url.path != "/admin/login":
            redirect_url = f"/admin/login?next={request.url}"
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": redirect_url},
            )
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        response = Response()
        await session.clear(response)
        redirect_url = f"/admin/login?next={request.url}"
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": redirect_url},
        )

    return user


async def get_user(request: Request, db: Session = Depends(get_db)):
    setup_needed = await check_setup_needed(db)
    if setup_needed:
        return None

    session = await get_session(request)
    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.query(User).filter(User.id == user_id).first()


# Setup page - only shown if no users exist
@router.get("/setup", response_class=HTMLResponse)
async def setup_page(
    request: Request, setup_needed: bool = Depends(check_setup_needed)
):
    if not setup_needed:
        return RedirectResponse(url="/admin/login")

    return request.state.templates.TemplateResponse(
        "admin/setup.html",
        {"request": request, "title": "Setup Admin Account"},
    )


@router.post("/setup", response_class=HTMLResponse)
async def setup_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    setup_needed: bool = Depends(check_setup_needed),
):
    if not setup_needed:
        return RedirectResponse(url="/admin/login")

    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        hashed_password=hashed_password,
        is_setup_complete=True,
    )
    db.add(db_user)
    db.commit()

    settings.get_settings(db)  # This creates default settings if they don't exist

    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: Optional[str] = None):
    return request.state.templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "title": "Admin Login", "next": next},
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username, password)
    if not user:
        return request.state.templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "title": "Admin Login",
                "error": "Invalid username or password",
                "next": next,
            },
        )

    session = await get_session(request)
    session.set("user_id", user.id)
    session.set("username", user.username)
    session.set("logged_in_at", datetime.utcnow().isoformat())

    redirect_url = next if next else "/admin/dashboard"
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    session.save(response)

    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    all_posts = posts.get_posts(db, include_pages=False)
    print(all_posts)
    _settings = settings.get_settings(db)

    return request.state.templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "posts": all_posts,
            "settings": _settings,
            "title": "Admin Dashboard",
        },
    )


@router.get("/pages", response_class=HTMLResponse)
async def pages(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    return request.state.templates.TemplateResponse(
        "admin/pages.html",
        {
            "request": request,
            "pages": posts.get_pages(db),
            "settings": settings.get_settings(db),
            "title": "Pages",
        },
    )


@router.get("/posts/new", response_class=HTMLResponse)
async def new_post(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    return request.state.templates.TemplateResponse(
        "admin/post_edit.html",
        {
            "request": request,
            "settings": settings.get_settings(db),
            "title": "New Post",
            "is_new": True,
        },
    )


@router.post("/posts/new", response_class=HTMLResponse)
async def create_post(
    request: Request,
    title: str = Form(...),
    slug: Optional[str] = Form(None),
    tags: str = Form(""),
    markdown_content: str = Form(...),
    is_published: bool = Form(False),
    meta_description: str = Form(""),
    meta_keywords: str = Form(""),
    canonical_url: str = Form(""),
    og_image: str = Form(""),
    no_index: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    if not slug:
        existing_slugs = posts.get_all_slugs(db)
        slug = utils.generate_unique_slug(title, existing_slugs)

    post = schemas.PostCreate(
        title=title,
        slug=slug,
        tags=tags,
        markdown_content=markdown_content,
        is_published=is_published,
        is_page=False,
        meta_description=meta_description,
        meta_keywords=meta_keywords,
        canonical_url=canonical_url,
        og_image=og_image,
        no_index=no_index,
    )
    posts.create_post(db, post)

    return RedirectResponse(
        url="/admin/dashboard",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/posts/{post_id}/edit", response_class=HTMLResponse)
async def edit_post(
    post_id: int,
    request: Request,
    success: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    post = posts.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return request.state.templates.TemplateResponse(
        "admin/post_edit.html",
        {
            "request": request,
            "post": post,
            "settings": settings.get_settings(db),
            "title": f"Edit Post: {post.title}",
            "is_new": False,
            "success": success,
        },
    )


@router.post("/posts/{post_id}/edit", response_class=HTMLResponse)
async def update_post(
    post_id: int,
    request: Request,
    title: str = Form(...),
    slug: str = Form(...),
    tags: str = Form(""),
    markdown_content: str = Form(...),
    is_published: bool = Form(False),
    meta_description: str = Form(""),
    meta_keywords: str = Form(""),
    canonical_url: str = Form(""),
    og_image: str = Form(""),
    no_index: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    post = posts.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post_update = schemas.PostUpdate(
        title=title,
        slug=slug,
        tags=tags,
        markdown_content=markdown_content,
        is_published=is_published,
        is_page=post.is_page,
        meta_description=meta_description,
        meta_keywords=meta_keywords,
        canonical_url=canonical_url,
        og_image=og_image,
        no_index=no_index,
    )
    posts.update_post(db, post_id, post_update)

    if post.is_page:
        redirect_url = f"/admin/pages/{post_id}/edit?success=true"
    else:
        redirect_url = f"/admin/posts/{post_id}/edit?success=true"

    return RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/posts/{post_id}/delete", response_class=HTMLResponse)
async def delete_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    success = posts.delete_post(db, post_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found")

    return RedirectResponse(
        url="/admin/dashboard",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/settings", response_class=HTMLResponse)
async def edit_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    return request.state.templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "settings": settings.get_settings(db),
            "pages": posts.get_pages(db),
            "title": "Blog Settings",
        },
    )


@router.post("/settings", response_class=HTMLResponse)
async def update_settings(
    request: Request,
    blog_title: str = Form(...),
    blog_description: str = Form(...),
    custom_css: str = Form(""),
    theme: str = Form("default"),
    navigation_markdown: str = Form("[Home](/)"),
    footer_markdown: str = Form("Powered by publite.me"),
    home_page_id: Optional[str] = Form(None),
    comments_enabled: bool = Form(False),
    allow_anonymous_comments: bool = Form(False),
    rss_enabled: bool = Form(False),
    favicon: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    home_page_id_value = None if not home_page_id else int(home_page_id)

    settings_update = schemas.SettingsUpdate(
        blog_title=blog_title,
        blog_description=blog_description,
        custom_css=custom_css,
        theme=theme,
        navigation_markdown=navigation_markdown,
        footer_markdown=footer_markdown,
        home_page_id=home_page_id_value,
        comments_enabled=comments_enabled,
        allow_anonymous_comments=allow_anonymous_comments,
        rss_enabled=rss_enabled,
    )
    settings.update_settings(db, settings_update)

    if favicon and favicon.filename:
        media_root = os.getenv("MEDIA_ROOT", "app/static/media")
        favicon_path = f"{media_root}/favicon.ico"
        with open(favicon_path, "wb") as buffer:
            shutil.copyfileobj(favicon.file, buffer)

    return RedirectResponse(
        url="/admin/settings",
        status_code=status.HTTP_303_SEE_OTHER,
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/pages/new", response_class=HTMLResponse)
async def new_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    return request.state.templates.TemplateResponse(
        "admin/page_edit.html",
        {
            "request": request,
            "settings": settings.get_settings(db),
            "title": "New Page",
            "is_new": True,
        },
    )


@router.post("/pages/new", response_class=HTMLResponse)
async def create_page(
    request: Request,
    title: str = Form(...),
    slug: Optional[str] = Form(None),
    markdown_content: str = Form(...),
    is_published: bool = Form(False),
    meta_description: str = Form(""),
    meta_keywords: str = Form(""),
    canonical_url: str = Form(""),
    og_image: str = Form(""),
    no_index: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    if not slug:
        existing_slugs = posts.get_all_slugs(db)
        slug = utils.generate_unique_slug(title, existing_slugs)

    post = schemas.PostCreate(
        title=title,
        slug=slug,
        tags="",
        markdown_content=markdown_content,
        is_published=is_published,
        is_page=True,
        meta_description=meta_description,
        meta_keywords=meta_keywords,
        canonical_url=canonical_url,
        og_image=og_image,
        no_index=no_index,
    )
    posts.create_post(db, post)

    return RedirectResponse(
        url="/admin/pages",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/pages/{page_id}/edit", response_class=HTMLResponse)
async def edit_page(
    page_id: int,
    request: Request,
    success: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    page = posts.get_post_by_id(db, page_id)
    if not page or not page.is_page:
        raise HTTPException(status_code=404, detail="Page not found")
    return request.state.templates.TemplateResponse(
        "admin/page_edit.html",
        {
            "request": request,
            "page": page,
            "settings": settings.get_settings(db),
            "title": f"Edit Page: {page.title}",
            "is_new": False,
            "success": success,
        },
    )


@router.post("/pages/{page_id}/edit", response_class=HTMLResponse)
async def update_page(
    page_id: int,
    request: Request,
    csrf_token: str = Form(...),
    title: str = Form(...),
    slug: str = Form(...),
    markdown_content: str = Form(...),
    is_published: bool = Form(False),
    meta_description: str = Form(""),
    meta_keywords: str = Form(""),
    canonical_url: str = Form(""),
    og_image: str = Form(""),
    no_index: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    page_update = schemas.PostUpdate(
        title=title,
        slug=slug,
        tags="",
        markdown_content=markdown_content,
        is_published=is_published,
        is_page=True,
        meta_description=meta_description,
        meta_keywords=meta_keywords,
        canonical_url=canonical_url,
        og_image=og_image,
        no_index=no_index,
    )
    db_page = posts.update_post(db, page_id, page_update)

    if not db_page:
        raise HTTPException(status_code=404, detail="Page not found")

    return RedirectResponse(
        url=f"/admin/pages/{page_id}/edit?success=true",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/pages/{page_id}/delete", response_class=HTMLResponse)
async def delete_page(
    page_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    success = posts.delete_post(db, page_id)
    if not success:
        raise HTTPException(status_code=404, detail="Page not found")

    return RedirectResponse(
        url="/admin/pages",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    session = await get_session(request)
    response = RedirectResponse(url="/admin/login")
    await session.clear(response)
    return response


@router.get("/", response_class=HTMLResponse)
async def admin_home(
    request: Request,
    current_user: User = Depends(get_user),
):
    if current_user:
        return RedirectResponse(url="/admin/dashboard")
    return RedirectResponse(url="/admin/login")
