import os
from typing import List

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
    
    # Get CSRF token from request state
    csrf_token = getattr(request.state, 'csrf_token', '')
    
    # Get templates from request state
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
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    imported_posts = []
    errors = []
    
    try:
        for file in files:
            if not file.filename.endswith(('.md', '.markdown')):
                errors.append(f"{file.filename}: Only .md and .markdown files are supported")
                continue
            
            content = await file.read()
            content_str = content.decode('utf-8')
            
            # Import as single post
            try:
                post = imports.import_markdown_post(db, content_str, file.filename)
                imported_posts.append(post)
            except Exception as e:
                errors.append(f"{file.filename}: {str(e)}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    
    # Prepare response message
    success_count = len(imported_posts)
    error_count = len(errors)
    
    message = f"Successfully imported {success_count} post(s)"
    if errors:
        message += f". {error_count} error(s) occurred."
    
    # Redirect to admin with success message
    return RedirectResponse(
        url=f"/admin?message={message}&errors={'|'.join(errors) if errors else ''}",
        status_code=302
    )


@router.post("/text")
async def import_text(
    request: Request,
    content: str = Form(...),
    filename: str = Form("imported_post.md"),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db)
):
    """Import post from text content"""
    await get_user_or_redirect(request, db)
    
    try:
        post = imports.import_markdown_post(db, content, filename)
        return RedirectResponse(
            url=f"/admin/posts/{post.id}/edit?message=Post imported successfully",
            status_code=302
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
