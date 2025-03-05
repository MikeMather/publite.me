import io
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from PIL import Image

from app.models import Media


@pytest.fixture
def mock_media(db_session):
    """Create a test media item."""
    media = Media(
        filename="test.jpg",
        original_filename="original_test.jpg",
        file_path="original/test.jpg",
        thumbnail_path="thumbnails/test.jpg",
        medium_path="medium/test.jpg",
        mime_type="image/jpeg",
        file_size=1000,
        width=800,
        height=600,
    )
    db_session.add(media)
    db_session.commit()
    db_session.refresh(media)
    return media


def test_media_list_json(client, mock_user, mock_media):
    """Test media list JSON endpoint returns successfully."""
    response = client.get("/admin/media/json")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["filename"] == mock_media.filename


def test_media_list(client, mock_user, mock_media):
    """Test media list endpoint returns successfully."""
    with patch("app.routers.media_router.get_user_or_redirect", return_value=mock_user):
        response = client.get("/admin/media")
        assert response.status_code == status.HTTP_200_OK
        assert "Media Library" in response.text
        assert mock_media.filename in response.text


def test_upload_media_image(client, mock_user, tmp_path):
    """Test uploading an image file."""
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    test_media_root = str(tmp_path)
    for subdir in ["original", "thumbnails", "medium"]:
        os.makedirs(os.path.join(test_media_root, subdir))

    with patch("app.routers.media_router.MEDIA_ROOT", test_media_root):
        response = client.post(
            "/admin/media/upload", files={"file": ("test.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["original_filename"] == "test.jpg"
        assert data["mime_type"] == "image/jpeg"
        assert data["width"] == 100
        assert data["height"] == 100
        assert os.path.exists(os.path.join(test_media_root, data["file_path"]))
        assert os.path.exists(os.path.join(test_media_root, data["thumbnail_path"]))
        assert os.path.exists(os.path.join(test_media_root, data["medium_path"]))


def test_upload_media_non_image(client, mock_user, tmp_path):
    """Test uploading a non-image file."""
    file_content = b"Test file content"
    file_bytes = io.BytesIO(file_content)

    test_media_root = str(tmp_path)
    for subdir in ["original", "thumbnails", "medium"]:
        os.makedirs(os.path.join(test_media_root, subdir))

    with patch("app.routers.media_router.MEDIA_ROOT", test_media_root):
        response = client.post(
            "/admin/media/upload",
            files={"file": ("test.txt", file_bytes, "text/plain")},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["original_filename"] == "test.txt"
        assert data["mime_type"] == "text/plain"
        assert data["width"] is None
        assert data["height"] is None
        assert os.path.exists(os.path.join(test_media_root, data["file_path"]))
        assert os.path.exists(os.path.join(test_media_root, data["thumbnail_path"]))
        assert os.path.exists(os.path.join(test_media_root, data["medium_path"]))


def test_get_media_item_not_found(client, mock_user):
    """Test get media item endpoint returns 404 for non-existent media."""
    response = client.get("/admin/media/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_media_item_success(client, mock_user, mock_media):
    """Test get media item endpoint returns successfully."""
    response = client.get(f"/admin/media/{mock_media.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["filename"] == mock_media.filename
    assert data["file_path"] == mock_media.file_path


def test_delete_media_item_not_found(client, mock_user):
    """Test delete media item endpoint returns 404 for non-existent media."""
    response = client.delete("/admin/media/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_media_item_success(client, mock_user, mock_media, tmp_path):
    """Test delete media item endpoint successfully deletes media."""
    test_media_root = str(tmp_path)
    for subdir in ["original", "thumbnails", "medium"]:
        os.makedirs(os.path.join(test_media_root, subdir))
        with open(os.path.join(test_media_root, subdir, mock_media.filename), "w") as f:
            f.write("test")

    with patch("app.routers.media_router.MEDIA_ROOT", test_media_root):
        response = client.delete(f"/admin/media/{mock_media.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

        assert not os.path.exists(os.path.join(test_media_root, mock_media.file_path))
        assert not os.path.exists(
            os.path.join(test_media_root, mock_media.thumbnail_path)
        )
        assert not os.path.exists(os.path.join(test_media_root, mock_media.medium_path))
