from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def mock_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        DEVICE="cpu",
        MODEL_PATH="fake_model.pt",
        STORAGE_DIR=str(tmp_path / "videos"),
        RUNS_DIR=str(tmp_path / "runs"),
        OPENROUTER_API_KEY="",
        MAX_CLASSES=10,
        MAX_SAMPLED_FRAMES=5,
        MAX_DETECTIONS=100,
    )


@pytest.fixture()
def mock_model() -> MagicMock:
    model = MagicMock()
    model.ckpt_path = None
    model.names = {0: "person", 1: "car"}
    model.predict.return_value = []
    return model


@pytest.fixture()
def client(mock_settings: Settings, mock_model: MagicMock):
    application = create_app(mock_settings, model_factory=lambda _: mock_model)
    with TestClient(application) as client:
        yield client


@pytest.fixture()
def video_bytes(tmp_path: Path) -> bytes:
    path = tmp_path / "fixture.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (32, 24))
    assert writer.isOpened(), "OpenCV MP4 fixture encoder unavailable"
    for i in range(100):
        writer.write(np.full((24, 32, 3), i * 2, dtype=np.uint8))
    writer.release()
    return path.read_bytes()


@pytest.fixture()
def video_id(client, video_bytes) -> str:
    response = client.post("/upload", files={"file": ("fixture.mp4", video_bytes, "video/mp4")})
    assert response.status_code == 200, response.text
    return response.json()["video_id"]
