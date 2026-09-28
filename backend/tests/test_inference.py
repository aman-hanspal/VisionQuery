from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from app.services.inference import VideoDecodeError, run_yoloworld_query


class Capture:
    def __init__(self, times, fps=10, reported=None, opened=True):
        self.times = times
        self.index = -1
        self.fps = fps
        self.reported = len(times) if reported is None else reported
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def get(self, key):
        return {
            cv2.CAP_PROP_FPS: self.fps,
            cv2.CAP_PROP_FRAME_COUNT: self.reported,
            cv2.CAP_PROP_FRAME_WIDTH: 32,
            cv2.CAP_PROP_FRAME_HEIGHT: 24,
            cv2.CAP_PROP_POS_MSEC: self.times[max(0, self.index)] * 1000 if self.times else 0,
        }.get(key, 0)

    def read(self):
        self.index += 1
        return (True, np.zeros((24, 32, 3), dtype=np.uint8)) if self.index < len(self.times) else (False, None)

    def release(self):
        self.released = True


def scan(monkeypatch, capture, model=None, **options):
    monkeypatch.setattr("app.services.inference.cv2.VideoCapture", lambda _: capture)
    model = model or MagicMock(predict=MagicMock(return_value=[]))
    return run_yoloworld_query(
        video_path=Path("fixture.mp4"), model=model, classes=["person"], conf=0.25, **{"fps": 1, **options}
    )


def test_detection_cap_does_not_stop_scan(monkeypatch):
    cap = Capture(list(range(10)), fps=1)
    box = SimpleNamespace(xyxy=np.array([[1, 2, 10, 20]]), cls=[0], conf=[0.9])
    model = MagicMock(predict=MagicMock(return_value=[SimpleNamespace(names={0: "person"}, boxes=[box, box])]))
    result = scan(monkeypatch, cap, model, max_detections=3)
    assert model.predict.call_count == 10
    assert len(result["detections"]) == 3
    assert result["metadata"]["total_detections"] == 20
    assert result["metadata"]["dropped_detections"] == 17
    assert result["metadata"]["scan_complete"]
    assert cap.released


def test_fractional_sampling_avoids_rounded_frame_step(monkeypatch):
    result = scan(monkeypatch, Capture([i / 10 for i in range(100)]), fps=3)
    assert result["metadata"]["detector_calls"] == 30
    assert result["metadata"]["selected_timestamps"][:4] == pytest.approx([0, 0.4, 0.7, 1])


def test_vfr_timestamps_drive_sampling(monkeypatch):
    result = scan(monkeypatch, Capture([0, 0.01, 0.02, 1.1, 1.2, 2.2]), fps=1)
    assert result["metadata"]["selected_timestamps"] == pytest.approx([0, 1.1, 2.2])
    assert result["metadata"]["timestamp_fallback_frames"] == 0


def test_invalid_fps_and_pts_fallback_is_reported(monkeypatch):
    result = scan(monkeypatch, Capture([0, 0, float("nan")], fps=float("inf")), fps=60)
    assert result["metadata"]["selected_timestamps"] == pytest.approx([0, 1 / 30, 2 / 30])
    assert result["metadata"]["timestamp_fallback_frames"] == 2


def test_decode_failure_is_not_reported_complete(monkeypatch):
    result = scan(monkeypatch, Capture([0, 0.1, 0.2], reported=100))
    assert not result["metadata"]["scan_complete"]
    assert result["metadata"]["stop_reason"] == "decode_stopped_early"


def test_exact_frame_limit_at_eof_is_complete(monkeypatch):
    result = scan(monkeypatch, Capture([0, 1], fps=1), max_sampled_frames=2)
    assert result["metadata"]["scan_complete"]


def test_budget_uses_real_timeline_and_unique_indices(monkeypatch):
    captures = [Capture([0, 0.1, 0.2, 5, 9], reported=0), Capture([0, 0.1, 0.2, 5, 9], reported=0)]
    iterator = iter(captures)
    monkeypatch.setattr("app.services.inference.cv2.VideoCapture", lambda _: next(iterator))
    result = run_yoloworld_query(
        video_path=Path("fixture.mp4"),
        model=MagicMock(predict=MagicMock(return_value=[])),
        classes=["person"],
        conf=0.25,
        fps=1,
        scan_mode="budget",
        frame_budget=3,
    )
    assert result["metadata"]["selected_frame_indices"] == [0, 3, 4]
    assert result["metadata"]["selected_timestamps"] == [0, 5, 9]
    assert all(cap.released for cap in captures)


def test_capture_released_when_inference_fails(monkeypatch):
    cap = Capture([0])
    with pytest.raises(RuntimeError, match="inference failed"):
        scan(monkeypatch, cap, MagicMock(predict=MagicMock(side_effect=RuntimeError("inference failed"))))
    assert cap.released


def test_unopenable_capture_released(monkeypatch):
    cap = Capture([], opened=False)
    with pytest.raises(VideoDecodeError):
        scan(monkeypatch, cap)
    assert cap.released
