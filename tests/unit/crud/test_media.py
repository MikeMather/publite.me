from app.crud.media import (
    create_media,
    delete_media,
    get_media,
    get_media_by_filename,
    get_media_by_id,
    update_media,
)
from app.models import Media


def test_create_media(db_session):
    from app.schemas import MediaCreate

    media_data = MediaCreate(
        filename="test.jpg",
        original_filename="test.jpg",
        file_path="/uploads/test.jpg",
        file_size=1024,
        mime_type="image/jpeg",
        width=800,
        height=600,
        thumbnail_path="/uploads/thumbnails/test.jpg",
        medium_path="/uploads/medium/test.jpg",
    )
    media = create_media(db_session, media_data)
    assert media.id is not None
    assert media.filename == "test.jpg"
    assert media.file_size == 1024


def test_get_media(db_session):
    from app.schemas import MediaCreate

    media_data = MediaCreate(
        filename="test1.jpg",
        original_filename="test1.jpg",
        file_path="/uploads/test1.jpg",
        file_size=1024,
        mime_type="image/jpeg",
        width=800,
        height=600,
        thumbnail_path="/uploads/thumbnails/test1.jpg",
        medium_path="/uploads/medium/test1.jpg",
    )
    create_media(db_session, media_data)

    media_data = MediaCreate(
        filename="test2.jpg",
        original_filename="test2.jpg",
        file_path="/uploads/test2.jpg",
        file_size=2048,
        mime_type="image/jpeg",
        width=1024,
        height=768,
        thumbnail_path="/uploads/thumbnails/test2.jpg",
        medium_path="/uploads/medium/test2.jpg",
    )
    create_media(db_session, media_data)

    media_items = get_media(db_session)
    assert len(media_items) == 2
    assert media_items[1].filename == "test1.jpg"
    assert media_items[0].filename == "test2.jpg"

    all_media = db_session.query(Media).all()
    print(f"All media in DB: {[(m.id, m.filename) for m in all_media]}")


def test_get_media_by_id(db_session):
    from app.schemas import MediaCreate

    media_data = MediaCreate(
        filename="test.jpg",
        original_filename="test.jpg",
        file_path="/uploads/test.jpg",
        file_size=1024,
        mime_type="image/jpeg",
        width=800,
        height=600,
        thumbnail_path="/uploads/thumbnails/test.jpg",
        medium_path="/uploads/medium/test.jpg",
    )
    created_media = create_media(db_session, media_data)
    media = get_media_by_id(db_session, created_media.id)
    assert media.id == created_media.id
    assert media.filename == "test.jpg"


def test_get_media_by_filename(db_session):
    from app.schemas import MediaCreate

    media_data = MediaCreate(
        filename="test.jpg",
        original_filename="test.jpg",
        file_path="/uploads/test.jpg",
        file_size=1024,
        mime_type="image/jpeg",
        width=800,
        height=600,
        thumbnail_path="/uploads/thumbnails/test.jpg",
        medium_path="/uploads/medium/test.jpg",
    )
    created_media = create_media(db_session, media_data)
    media = get_media_by_filename(db_session, "test.jpg")
    assert media.id == created_media.id
    assert media.filename == "test.jpg"


def test_update_media(db_session):
    from app.schemas import MediaCreate, MediaUpdate

    media_data = MediaCreate(
        filename="test.jpg",
        original_filename="test.jpg",
        file_path="/uploads/test.jpg",
        file_size=1024,
        mime_type="image/jpeg",
        width=800,
        height=600,
        thumbnail_path="/uploads/thumbnails/test.jpg",
        medium_path="/uploads/medium/test.jpg",
    )
    created_media = create_media(db_session, media_data)

    update_data = MediaUpdate(file_size=2048)
    updated_media = update_media(db_session, created_media.id, update_data)
    assert updated_media.file_size == 2048


def test_delete_media(db_session):
    from app.schemas import MediaCreate

    media_data = MediaCreate(
        filename="test.jpg",
        original_filename="test.jpg",
        file_path="/uploads/test.jpg",
        file_size=1024,
        mime_type="image/jpeg",
        width=800,
        height=600,
        thumbnail_path="/uploads/thumbnails/test.jpg",
        medium_path="/uploads/medium/test.jpg",
    )
    created_media = create_media(db_session, media_data)
    result = delete_media(db_session, created_media.id)
    assert result is True
    assert get_media_by_id(db_session, created_media.id) is None
