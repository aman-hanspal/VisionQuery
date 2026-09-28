from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DetectionRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    prompt: str | None = Field(None, max_length=2000)
    classes: list[str] | None = Field(None, max_length=100)
    conf: float = Field(0.25, ge=0, le=1)


class QueryRequest(DetectionRequest):
    video_id: str = Field(..., min_length=1, max_length=128)
    fps: float = Field(1.0, gt=0, le=240)
    scan_mode: Literal["full", "budget"] = "full"
    frame_budget: int | None = Field(None, ge=2, le=100000)
    max_sampled_frames: int | None = Field(None, gt=0)

    @model_validator(mode="after")
    def check_scan_options(self):
        if self.scan_mode == "full" and self.frame_budget is not None:
            raise ValueError("frame_budget is only used in budget mode")
        if self.scan_mode == "budget" and self.max_sampled_frames is not None:
            raise ValueError("Use frame_budget, not max_sampled_frames, in budget mode")
        return self


class ClassesRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)


class LiveDetectRequest(DetectionRequest):
    image_b64: str = Field(..., min_length=1, max_length=16 * 1024 * 1024)
