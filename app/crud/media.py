from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Media


def create_media(db: Session, media) -> Media:
    db_media = Media(
        filename=media.filename,
        original_filename=media.original_filename,
        file_path=media.file_path,
        file_size=media.file_size,
        mime_type=media.mime_type,
        width=media.width,
        height=media.height,
        thumbnail_path=media.thumbnail_path,
        medium_path=media.medium_path,
    )
    db.add(db_media)
    db.commit()
    db.refresh(db_media)
    return db_media


def get_media(db: Session, skip: int = 0, limit: int = 100) -> List[Media]:
    return (
        db.query(Media)
        .order_by(Media.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_media_by_id(db: Session, media_id: int) -> Optional[Media]:
    return db.query(Media).filter(Media.id == media_id).first()


def get_media_by_filename(db: Session, filename: str) -> Optional[Media]:
    return db.query(Media).filter(Media.filename == filename).first()


def update_media(db: Session, media_id: int, media_update) -> Optional[Media]:
    db_media = db.query(Media).filter(Media.id == media_id).first()
    if not db_media:
        return None

    update_data = media_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_media, key, value)

    db.commit()
    db.refresh(db_media)
    return db_media


def delete_media(db: Session, media_id: int) -> bool:
    db_media = db.query(Media).filter(Media.id == media_id).first()
    if db_media:
        db.delete(db_media)
        db.commit()
        return True
    return False
