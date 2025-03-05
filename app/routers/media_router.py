import io
import os
import shutil
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from PIL import Image
from sqlalchemy.orm import Session

from app import schemas
from app.crud import media, settings
from app.database import get_db
from app.models import User
from app.routers.admin_router import get_user_or_redirect

router = APIRouter(prefix="/admin/media", tags=["media"])

MEDIA_ROOT = os.getenv("MEDIA_ROOT", "app/static/media")


@router.get("", response_class=HTMLResponse)
async def media_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    media_items = media.get_media(db)
    blog_settings = settings.get_settings(db)

    return request.state.templates.TemplateResponse(
        "admin/media.html",
        {
            "request": request,
            "media_items": media_items,
            "settings": blog_settings,
            "title": "Media Library",
            "active": "media",
        },
    )


@router.get("/json", response_class=JSONResponse)
async def media_list_json(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    media_items = media.get_media(db)

    # Convert SQLAlchemy objects to dictionaries
    media_list = []
    for med in media_items:
        media_dict = {
            "id": med.id,
            "filename": med.filename,
            "original_filename": med.original_filename,
            "file_path": med.file_path,
            "thumbnail_path": med.thumbnail_path,
            "medium_path": med.medium_path,
            "mime_type": med.mime_type,
            "file_size": med.file_size,
            "width": med.width,
            "height": med.height,
            "created_at": med.created_at.isoformat(),
        }
        media_list.append(media_dict)

    return media_list


@router.post("/upload", response_class=JSONResponse)
async def upload_media(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    file_extension = file.filename.split(".")[-1].lower()
    unique_filename = f"{uuid.uuid4()}.{file_extension}"

    original_path = f"{MEDIA_ROOT}/original/{unique_filename}"
    thumbnail_path = f"{MEDIA_ROOT}/thumbnails/{unique_filename}"
    medium_path = f"{MEDIA_ROOT}/medium/{unique_filename}"

    content = await file.read()
    with open(original_path, "wb") as out_file:
        out_file.write(content)

    file_size = os.path.getsize(original_path)

    width = None
    height = None

    # Process images (resize, optimize)
    mime_type = file.content_type
    if mime_type.startswith("image/"):
        img = Image.open(io.BytesIO(content))
        width, height = img.size

        # thumbnail (150x150)
        thumb = img.copy()
        thumb.thumbnail((150, 150))
        thumb.save(thumbnail_path, optimize=True, quality=90)

        # medium size (800px wide)
        medium = img.copy()
        medium.thumbnail((800, 800))
        medium.save(medium_path, optimize=True, quality=85)

        # Add WebP version for medium size if not already WebP
        if file_extension.lower() != "webp":
            webp_medium_path = (
                f"{MEDIA_ROOT}/medium/{unique_filename.split('.')[0]}.webp"
            )
            medium.save(webp_medium_path, "WEBP", quality=85)
    else:
        # Otherwise just copy the original to the other directories
        shutil.copy(original_path, thumbnail_path)
        shutil.copy(original_path, medium_path)

    media_create = schemas.MediaCreate(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=f"original/{unique_filename}",
        file_size=file_size,
        mime_type=mime_type,
        width=width,
        height=height,
        thumbnail_path=f"thumbnails/{unique_filename}",
        medium_path=f"medium/{unique_filename}",
    )

    db_media = media.create_media(db, media_create)

    return {
        "id": db_media.id,
        "filename": db_media.filename,
        "original_filename": db_media.original_filename,
        "file_path": db_media.file_path,
        "thumbnail_path": db_media.thumbnail_path,
        "medium_path": db_media.medium_path,
        "mime_type": db_media.mime_type,
        "file_size": db_media.file_size,
        "width": db_media.width,
        "height": db_media.height,
    }


@router.get("/{media_id}", response_class=JSONResponse)
async def get_media_item(
    media_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    med = media.get_media_by_id(db, media_id)
    if not med:
        raise HTTPException(status_code=404, detail="Media not found")

    return {
        "id": med.id,
        "filename": med.filename,
        "original_filename": med.original_filename,
        "file_path": med.file_path,
        "thumbnail_path": med.thumbnail_path,
        "medium_path": med.medium_path,
        "mime_type": med.mime_type,
        "file_size": med.file_size,
        "width": med.width,
        "height": med.height,
        "created_at": med.created_at.isoformat(),
    }


@router.delete("/{media_id}", response_class=JSONResponse)
async def delete_media_item(
    media_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_or_redirect),
):
    med = media.get_media_by_id(db, media_id)
    if not med:
        raise HTTPException(status_code=404, detail="Media not found")

    try:
        if os.path.exists(f"{MEDIA_ROOT}/{med.file_path}"):
            os.remove(f"{MEDIA_ROOT}/{med.file_path}")
        if os.path.exists(f"{MEDIA_ROOT}/{med.thumbnail_path}"):
            os.remove(f"{MEDIA_ROOT}/{med.thumbnail_path}")
        if os.path.exists(f"{MEDIA_ROOT}/{med.medium_path}"):
            os.remove(f"{MEDIA_ROOT}/{med.medium_path}")
    except Exception as e:
        print(f"Error deleting files: {e}")

    success = media.delete_media(db, media_id)

    return {"success": success}
