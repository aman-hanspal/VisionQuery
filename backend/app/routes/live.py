from __future__ import annotations

import base64
import threading

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.dependencies import get_model, get_model_lock, get_settings
from app.routes.query import resolve_request_classes
from app.schemas.requests import LiveDetectRequest
from app.services.inference import run_yoloworld_live_frame

router = APIRouter()


@router.post("/live/detect")
async def live_detect(
    req: LiveDetectRequest,
    model=Depends(get_model),
    lock: threading.Lock = Depends(get_model_lock),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    classes = await resolve_request_classes(req, settings)

    raw = req.image_b64
    if "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        image_bytes = base64.b64decode(raw, validate=True)
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        frame_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image payload: {e}") from e

    if frame_bgr is None:
        raise HTTPException(status_code=400, detail="Failed to decode image")

    def detect():
        with lock:
            model.set_classes(classes)
            return run_yoloworld_live_frame(
                frame_bgr=frame_bgr,
                model=model,
                conf=req.conf,
                device=settings.DEVICE,
                image_size=settings.INFERENCE_IMAGE_SIZE,
            )

    detections = await run_in_threadpool(detect)

    h, w = frame_bgr.shape[:2]
    return {
        "detections": detections,
        "frame_width": int(w),
        "frame_height": int(h),
        "classes": classes[: settings.MAX_CLASSES],
    }
