from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DEVICE: str = "auto"
    MODEL_PATH: str = "yolov8m-worldv2.pt"
    STORAGE_DIR: str = "storage/videos"
    RUNS_DIR: str = "storage/runs"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    INFERENCE_IMAGE_SIZE: int = Field(640, ge=32, le=4096, multiple_of=32)
    MAX_CLASSES: int = Field(10, gt=0)
    # Default budget only; full scans are never silently capped by this value.
    MAX_SAMPLED_FRAMES: int = Field(900, gt=0)
    MAX_DETECTIONS: int = Field(5000, gt=0)
    MAX_UPLOAD_BYTES: int = Field(1024 * 1024 * 1024, gt=0)
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
