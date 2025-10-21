import os
from typing import List
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.crud import imports, settings
from app.database import get_db
from app.session import get_session
from app.routers.admin_router import get_user_or_redirect

router = APIRouter(prefix="/admin/import", tags=["import"])


@router.get("/", response_class=HTMLResponse)
async def import_page(request: Request, db: Session = Depends(get_db)):
    """Display the import page"""
    await get_user_or_redirect(request, db)
    
    csrf_token = getattr(request.state, 'csrf_token', '')
    
    templates = getattr(request.state, 'templates', None)
    if not templates:
        raise HTTPException(status_code=500, detail="Templates not available")
    
    return templates.TemplateResponse(
        "admin/import.html",
        {
            "request": request,
            "settings": settings.get_settings(db),
            "csrf_token": csrf_token,
            "title": "Import Posts",
            "active": "posts"
        }
    )


@router.post("/upload")
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle file uploads and import posts"""
    await get_user_or_redirect(request, db)

    expected_token = getattr(request.state, 'csrf_token', '')
    if not csrf_token or csrf_token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    imported_posts = []
    errors = []
    
    for file in files:
        if not file.filename.lower().endswith(('.md', '.markdown')):
            errors.append(f"{file.filename}: Only .md and .markdown files are supported")
            continue
        
        try:
            content = await file.read()
            content_str = content.decode('utf-8')
            post = imports.import_markdown_post(db, content_str, file.filename)
            imported_posts.append(post)
        except UnicodeDecodeError as e:
            errors.append(f"{file.filename}: Invalid UTF-8 encoding")
        except ValueError as e:
            errors.append(f"{file.filename}: {e!s}")
        except Exception as e:
            errors.append(f"{file.filename}: Unexpected error - {e!s}")
    
    success_count = len(imported_posts)
    error_count = len(errors)
    
    message = f"Successfully imported {success_count} post(s)"
    if errors:
        message += f". {error_count} error(s) occurred."
    
    encoded_message = quote(message)
    encoded_errors = quote('|'.join(errors)) if errors else ''
    return RedirectResponse(
        url=f"/admin?message={encoded_message}&errors={encoded_errors}",
        status_code=302
    )
