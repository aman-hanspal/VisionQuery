from __future__ import annotations

import re
import uuid
from pathlib import Path

import cv2
from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

MEDIA_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
}


def sanitize_video_id(video_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", video_id):
        raise HTTPException(status_code=400, detail="Invalid video_id")
    return video_id


def video_path(video_id: str, *, storage_dir: Path) -> Path:
    return storage_dir / f"{sanitize_video_id(video_id)}.mp4"


def video_exists(video_id: str, *, storage_dir: Path) -> Path:
    safe = sanitize_video_id(video_id)
    for suffix in MEDIA_TYPES:
        path = storage_dir / f"{safe}{suffix}"
        if path.is_file():
            return path
    raise HTTPException(status_code=404, detail="Video not found")


def _validate_video(path: Path) -> bool:
    cap = cv2.VideoCapture(str(path))
    try:
        return cap.isOpened() and cap.read()[0]
    finally:
        cap.release()


async def save_upload(file: UploadFile, *, storage_dir: Path, max_bytes: int = 1024**3) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in MEDIA_TYPES:
        await file.close()
        raise HTTPException(status_code=400, detail="Use an MP4, WebM, MOV, AVI or MKV video")
    storage_dir.mkdir(parents=True, exist_ok=True)
    vid = str(uuid.uuid4())
    out_path = storage_dir / f"{vid}{suffix}"
    total = 0
    try:
        with out_path.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(status_code=413, detail="Video exceeds upload size limit")
                await run_in_threadpool(handle.write, chunk)
        if total == 0 or not await run_in_threadpool(_validate_video, out_path):
            raise HTTPException(status_code=400, detail="Video is empty, corrupt, or uses an unsupported codec")
    except BaseException:
        out_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return vid
