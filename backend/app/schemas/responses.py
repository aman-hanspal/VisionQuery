from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    ok: bool


class UploadResponse(BaseModel):
    video_id: str


class Detection(BaseModel):
    label: str
    conf: float
    bbox: list[float]
    t: float | None = None


class QueryResponse(BaseModel):
    detections: list[Detection]
    classes: list[str]
    metadata: dict[str, object]


class ClassesResponse(BaseModel):
    classes: list[str]


class LiveDetectResponse(BaseModel):
    detections: list[Detection]
    frame_width: int
    frame_height: int
    classes: list[str]
