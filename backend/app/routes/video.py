from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from app.config import Settings
from app.dependencies import get_settings
from app.services.video import MEDIA_TYPES, save_upload, video_exists

router = APIRouter()


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    from pathlib import Path

    storage = Path(settings.STORAGE_DIR)
    video_id = await save_upload(file, storage_dir=storage, max_bytes=settings.MAX_UPLOAD_BYTES)
    return {"video_id": video_id}


@router.get("/video/{video_id}")
def get_video(
    video_id: str,
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    from pathlib import Path

    storage = Path(settings.STORAGE_DIR)
    path = video_exists(video_id, storage_dir=storage)
    return FileResponse(path, media_type=MEDIA_TYPES[path.suffix], content_disposition_type="inline")
