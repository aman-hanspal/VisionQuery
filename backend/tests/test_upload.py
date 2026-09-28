from pathlib import Path

import pytest


def test_upload_returns_video_id(client, video_bytes):
    response = client.post("/upload", files={"file": ("test.mp4", video_bytes, "video/mp4")})
    assert response.status_code == 200
    assert response.json()["video_id"]


def test_get_video_returns_file_and_supports_seeking(client, video_id, video_bytes):
    response = client.get(f"/video/{video_id}")
    assert response.content == video_bytes
    assert response.headers["content-type"] == "video/mp4"
    response = client.get(f"/video/{video_id}", headers={"Range": "bytes=0-15"})
    assert response.status_code == 206
    assert response.content == video_bytes[:16]


def test_get_video_not_found(client):
    assert client.get("/video/nonexistent-id").status_code == 404


@pytest.mark.parametrize("filename,body", [("test.mp4", b"garbage"), ("empty.mp4", b""), ("test.txt", b"text")])
def test_bad_upload_removed(client, mock_settings, filename, body):
    response = client.post("/upload", files={"file": (filename, body, "video/mp4")})
    assert response.status_code == 400
    assert list(Path(mock_settings.STORAGE_DIR).iterdir()) == []


def test_upload_limit_and_cleanup(client, mock_settings, video_bytes):
    mock_settings.MAX_UPLOAD_BYTES = 4
    response = client.post("/upload", files={"file": ("test.mp4", video_bytes, "video/mp4")})
    assert response.status_code == 413
    assert list(Path(mock_settings.STORAGE_DIR).iterdir()) == []


def test_id_cannot_alias_another_video(client, video_id):
    response = client.post("/query", json={"video_id": f"../{video_id}", "classes": ["person"]})
    assert response.status_code == 400
