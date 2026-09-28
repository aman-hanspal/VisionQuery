from __future__ import annotations

import bisect
import math
import time
from pathlib import Path
from typing import Any

import cv2


def _safe_video_fps(cap: cv2.VideoCapture) -> float:
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0 or not math.isfinite(fps):  # NaN check
        return 30.0
    return fps


def _label_from_names(names: object, cls_i: int) -> str:
    if isinstance(names, dict):
        v = names.get(cls_i)
        return str(v) if v is not None else str(cls_i)
    if isinstance(names, (list, tuple)):
        if 0 <= cls_i < len(names):
            return str(names[cls_i])
        return str(cls_i)
    return str(cls_i)


def _detections_from_results(*, model: Any, results: Any, t: float | None = None) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    if not results:
        return out

    r0 = results[0]
    names = getattr(r0, "names", None) or getattr(model, "names", {})
    boxes = getattr(r0, "boxes", None)
    if boxes is None:
        return out

    for b in boxes:
        xyxy = b.xyxy[0].tolist()
        cls_i = int(b.cls[0])
        label = _label_from_names(names, cls_i)
        score = float(b.conf[0])
        item: dict[str, object] = {
            "label": str(label),
            "conf": float(score),
            "bbox": [float(x) for x in xyxy],
        }
        if t is not None:
            item["t"] = float(t)
        out.append(item)

    return out


def run_yoloworld_live_frame(
    *, frame_bgr: Any, model: Any, conf: float, device: str = "cpu", image_size: int = 640
) -> list[dict[str, object]]:
    results = model.predict(frame_bgr, conf=conf, verbose=False, device=device, imgsz=image_size)
    return _detections_from_results(model=model, results=results, t=None)


class VideoDecodeError(ValueError):
    pass


def _timestamp(cap, index: int, native_fps: float, previous: float) -> tuple[float, bool]:
    """Use decoder PTS when monotonic; explicitly count nominal-FPS fallbacks."""
    raw = float(cap.get(cv2.CAP_PROP_POS_MSEC)) / 1000.0
    if math.isfinite(raw) and raw >= 0 and (index == 0 or raw > previous):
        return raw, False
    return max(index / native_fps, previous + 1 / native_fps), True


def _count(cap, key: int) -> int:
    value = float(cap.get(key))
    return max(0, int(value)) if math.isfinite(value) else 0


def run_yoloworld_query(
    *,
    video_path: Path,
    model: Any,
    classes: list[str],
    fps: float,
    conf: float,
    device: str = "cpu",
    scan_mode: str = "full",
    frame_budget: int = 900,
    max_sampled_frames: int | None = None,
    max_detections: int = 5000,
    image_size: int = 640,
) -> dict[str, Any]:
    started = time.perf_counter()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        cap.release()
        raise VideoDecodeError("Failed to open video")
    native_fps = _safe_video_fps(cap)
    reported_frames = _count(cap, cv2.CAP_PROP_FRAME_COUNT)
    width, height = _count(cap, cv2.CAP_PROP_FRAME_WIDTH), _count(cap, cv2.CAP_PROP_FRAME_HEIGHT)
    times: list[float] = []
    selected_indices: set[int] | None = None
    prepass_frames = 0
    timestamp_fallbacks = 0
    prepass_incomplete = False
    selection_seconds = 0.0
    detections: list[dict[str, object]] = []
    timestamps: list[float] = []
    indices: list[int] = []
    frames_read = 0
    total_detections = 0
    inference_seconds = 0.0
    previous = -1.0 / native_fps
    next_sample = 0.0
    stop_reason = "end_of_video"
    try:
        if scan_mode == "budget":
            # Decode the timeline first: avoids trusting inaccurate frame counts and
            # distributes the budget over presentation time even for VFR inputs.
            selection_start = time.perf_counter()
            while True:
                ok, _ = cap.read()
                if not ok:
                    break
                t, fallback = _timestamp(cap, len(times), native_fps, previous)
                previous = t
                timestamp_fallbacks += int(fallback)
                times.append(t)
            prepass_frames = len(times)
            if not times:
                raise VideoDecodeError("Video contains no decodable frames")
            prepass_incomplete = reported_frames > prepass_frames
            budget = min(frame_budget, len(times))
            if budget == 1:
                selected_indices = {0}
            else:
                targets = [times[0] + (times[-1] - times[0]) * i / (budget - 1) for i in range(budget)]
                selected_indices = set()
                last_index = -1
                for i, target in enumerate(targets):
                    # Clamp to leave one unique frame for each remaining target.
                    lo = last_index + 1
                    hi = len(times) - (budget - i)
                    last_index = min(hi, max(lo, bisect.bisect_left(times, target)))
                    selected_indices.add(last_index)
            cap.release()
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise VideoDecodeError("Failed to reopen video for budget scan")
            previous = -1.0 / native_fps
            selection_seconds = time.perf_counter() - selection_start

        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                expected = len(times) if times else reported_frames
                if prepass_incomplete or (expected and frames_read < expected):
                    stop_reason = "decode_stopped_early"
                break
            index = frames_read
            frames_read += 1
            if times and index < len(times):
                t = times[index]
            else:
                t, fallback = _timestamp(cap, index, native_fps, previous)
                timestamp_fallbacks += int(fallback)
            previous = t
            if selected_indices is not None:
                should_sample = index in selected_indices
            else:
                should_sample = t + 1e-9 >= next_sample
            if not should_sample:
                continue
            if max_sampled_frames is not None and len(timestamps) >= max_sampled_frames:
                stop_reason = "max_sampled_frames"
                break
            timestamps.append(t)
            indices.append(index)
            if selected_indices is None:
                next_sample = (math.floor((t + 1e-9) * fps) + 1) / fps
            inference_start = time.perf_counter()
            results = model.predict(frame_bgr, conf=conf, verbose=False, device=device, imgsz=image_size)
            frame_dets = _detections_from_results(model=model, results=results, t=t)
            inference_seconds += time.perf_counter() - inference_start
            total_detections += len(frame_dets)
            # Bound returned results, never video coverage; report dropped boxes.
            remaining = max(0, max_detections - len(detections))
            detections.extend(frame_dets[:remaining])
        if frames_read == 0:
            raise VideoDecodeError("Video contains no decodable frames")
    finally:
        cap.release()

    elapsed = time.perf_counter() - started
    complete = stop_reason == "end_of_video"
    duration = (
        (times[-1] + 1 / native_fps)
        if times
        else (previous + 1 / native_fps if complete else reported_frames / native_fps if reported_frames else None)
    )
    span = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
    metadata = {
        "scan_mode": scan_mode,
        "classes": classes,
        "confidence_threshold": conf,
        "device": device,
        "requested_fps": fps,
        "fps_applied": scan_mode == "full",
        "native_fps": native_fps,
        "effective_sample_fps": (len(timestamps) - 1) / span if span > 0 else 0.0,
        "frame_budget": frame_budget if scan_mode == "budget" else None,
        "max_sampled_frames": max_sampled_frames,
        "reported_frame_count": reported_frames,
        "inference_image_size": image_size,
        "frame_width": width,
        "frame_height": height,
        "duration_seconds": duration,
        "duration_is_estimate": True,
        "frames_read": frames_read,
        "prepass_frames_read": prepass_frames,
        "total_frames_decoded": frames_read + prepass_frames,
        "detector_calls": len(timestamps),
        "selected_timestamps": timestamps,
        "selected_frame_indices": indices,
        "timestamp_source": "decoder_pts" if timestamp_fallbacks == 0 else "decoder_pts_with_fps_fallback",
        "timestamp_fallback_frames": timestamp_fallbacks,
        "decoded_until_seconds": previous,
        "processed_until_seconds": timestamps[-1] if timestamps else None,
        "first_sample_seconds": timestamps[0] if timestamps else None,
        "last_sample_seconds": timestamps[-1] if timestamps else None,
        "scan_complete": complete,
        "stop_reason": stop_reason,
        "completion_basis": "decoder_eof_with_reported_count_check" if reported_frames else "decoder_eof_only",
        "all_decoded_frames_sampled": complete and len(timestamps) == frames_read,
        "total_detections": total_detections,
        "returned_detections": len(detections),
        "detections_truncated": total_detections > len(detections),
        "dropped_detections": total_detections - len(detections),
        "elapsed_seconds": elapsed,
        "inference_seconds": inference_seconds,
        "selection_seconds": selection_seconds,
    }
    detections.sort(key=lambda d: (float(d["t"]), -float(d["conf"])))
    return {"detections": detections, "classes": classes, "metadata": metadata}
