from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.dependencies import get_model, get_model_lock, get_settings
from app.schemas.requests import ClassesRequest, QueryRequest
from app.services.inference import VideoDecodeError, run_yoloworld_query
from app.services.llm import _normalize_classes, prompt_to_classes
from app.services.video import video_exists

router = APIRouter()
logger = logging.getLogger(__name__)


async def resolve_request_classes(req, settings: Settings) -> list[str]:
    classes = _normalize_classes(req.classes, max_classes=settings.MAX_CLASSES)
    if not classes and req.prompt and req.prompt.strip():
        classes = await prompt_to_classes(
            req.prompt,
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.OPENROUTER_MODEL,
            max_classes=settings.MAX_CLASSES,
        )
    if not classes:
        raise HTTPException(status_code=400, detail="Provide `classes` or a non-empty `prompt`")
    return classes


@router.post("/query")
async def query(
    req: QueryRequest,
    request: Request,
    model=Depends(get_model),
    lock: threading.Lock = Depends(get_model_lock),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    request_start = time.perf_counter()
    path = video_exists(req.video_id, storage_dir=Path(settings.STORAGE_DIR))
    classes = await resolve_request_classes(req, settings)
    classes_resolved = time.perf_counter()

    def scan():
        wait_started = time.perf_counter()
        with lock:
            lock_acquired = time.perf_counter()
            model.set_classes(classes)
            configured = time.perf_counter()
            result = run_yoloworld_query(
                video_path=path,
                model=model,
                classes=classes,
                fps=req.fps,
                conf=req.conf,
                device=settings.DEVICE,
                scan_mode=req.scan_mode,
                frame_budget=req.frame_budget or max(2, settings.MAX_SAMPLED_FRAMES),
                max_sampled_frames=req.max_sampled_frames,
                max_detections=settings.MAX_DETECTIONS,
                image_size=settings.INFERENCE_IMAGE_SIZE,
            )
            result["metadata"].update(
                {
                    "lock_wait_seconds": lock_acquired - wait_started,
                    "class_encoding_seconds": configured - lock_acquired,
                    "class_resolution_seconds": classes_resolved - request_start,
                    "processing_seconds": time.perf_counter() - request_start,
                }
            )
            return result

    try:
        result = await run_in_threadpool(scan)
    except VideoDecodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    run_id = str(uuid.uuid4())
    result["metadata"].update(
        {
            "run_id": run_id,
            "video_id": req.video_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "environment": request.app.state.environment,
        }
    )
    log_path = Path(settings.RUNS_DIR) / f"{run_id}.json"
    result["metadata"]["run_log_saved"] = True
    try:
        await run_in_threadpool(log_path.write_text, json.dumps(result, indent=2), encoding="utf-8")
    except OSError:
        logger.exception("Could not save run log %s", run_id)
        result["metadata"]["run_log_saved"] = False
    return result


@router.post("/classes")
async def classes_endpoint(req: ClassesRequest, settings: Settings = Depends(get_settings)) -> dict[str, object]:
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt must not be blank")
    result = await prompt_to_classes(
        req.prompt,
        api_key=settings.OPENROUTER_API_KEY,
        model=settings.OPENROUTER_MODEL,
        max_classes=settings.MAX_CLASSES,
    )
    return {"classes": result}
