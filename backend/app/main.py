from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
import threading
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.routes import health, live, query, video


def load_model(settings: Settings):
    # Lazy imports let API tests inject a model without installing/loading YOLO.
    import torch
    from ultralytics import YOLOWorld

    device = settings.DEVICE
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    settings.DEVICE = device
    model = YOLOWorld(settings.MODEL_PATH)
    model.to(device)
    return model


def environment_manifest(settings: Settings, model) -> dict:
    packages = {}
    for name in ("ultralytics", "torch", "opencv-python", "opencv-python-headless", "numpy", "fastapi"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            pass
    checkpoint = Path(getattr(model, "ckpt_path", None) or settings.MODEL_PATH)
    checksum = None
    if checkpoint.is_file():
        with checkpoint.open("rb") as handle:
            checksum = hashlib.file_digest(handle, "sha256").hexdigest()
    source = {"commit": None, "dirty": None}
    try:
        root = Path(__file__).resolve().parents[2]
        source["commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=5).strip()
        source["dirty"] = bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True, timeout=5).strip()
        )
    except (OSError, subprocess.SubprocessError):
        pass
    torch = sys.modules.get("torch")
    gpu = None
    if torch is not None and settings.DEVICE.startswith("cuda") and torch.cuda.is_available():
        gpu = torch.cuda.get_device_name(settings.DEVICE)
    return {
        "source": source,
        "gpu_name": gpu,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "packages": packages,
        "device": settings.DEVICE,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": checksum,
    }


def create_app(settings: Settings | None = None, model_factory=load_model) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.RUNS_DIR).mkdir(parents=True, exist_ok=True)
        app.state.settings = settings
        app.state.model = model_factory(settings)
        app.state.model_lock = threading.Lock()
        app.state.environment = environment_manifest(settings, app.state.model)
        yield

    application = FastAPI(title="Vision Query", version="0.2.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in (health.router, video.router, query.router, live.router):
        application.include_router(router)
    return application


app = create_app()
