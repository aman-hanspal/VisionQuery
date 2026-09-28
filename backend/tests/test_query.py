import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest


def test_query_missing_video_returns_404(client):
    assert client.post("/query", json={"video_id": "missing", "classes": ["person"]}).status_code == 404


def test_query_no_prompt_or_classes_returns_400(client, video_id):
    assert client.post("/query", json={"video_id": video_id}).status_code == 400


def test_query_full_scan_is_not_limited_by_default_budget(client, video_id, mock_model, mock_settings):
    response = client.post("/query", json={"video_id": video_id, "classes": ["person"], "fps": 1})
    assert response.status_code == 200, response.text
    result = response.json()
    meta = result["metadata"]
    assert meta["scan_complete"]
    assert meta["stop_reason"] == "end_of_video"
    assert meta["detector_calls"] == mock_model.predict.call_count == 10
    assert meta["frames_read"] == 100
    assert meta["selected_timestamps"] == pytest.approx(list(range(10)))
    assert meta["frame_width"] == 32 and meta["frame_height"] == 24
    assert meta["elapsed_seconds"] >= meta["inference_seconds"] >= 0
    assert meta["run_log_saved"]
    saved = json.loads((Path(mock_settings.RUNS_DIR) / f"{meta['run_id']}.json").read_text())
    assert saved["classes"] == ["person"]
    assert saved["metadata"]["environment"]["device"] == "cpu"


def test_query_budget_spans_start_to_end(client, video_id):
    response = client.post(
        "/query", json={"video_id": video_id, "classes": ["car"], "scan_mode": "budget", "frame_budget": 3}
    )
    assert response.status_code == 200
    meta = response.json()["metadata"]
    assert meta["detector_calls"] == 3
    assert meta["selected_frame_indices"] == [0, 50, 99]
    assert meta["selected_timestamps"] == pytest.approx([0, 5, 9.9])
    assert meta["total_frames_decoded"] == 200
    assert meta["scan_complete"] and not meta["all_decoded_frames_sampled"]


def test_query_explicit_limit_is_reported(client, video_id):
    response = client.post("/query", json={"video_id": video_id, "classes": ["car"], "max_sampled_frames": 2})
    meta = response.json()["metadata"]
    assert not meta["scan_complete"]
    assert meta["stop_reason"] == "max_sampled_frames"
    assert meta["detector_calls"] == 2


def test_corrupt_existing_video_returns_400(client, mock_settings):
    (Path(mock_settings.STORAGE_DIR) / "broken.mp4").write_bytes(b"corrupt")
    response = client.post("/query", json={"video_id": "broken", "classes": ["car"]})
    assert response.status_code == 400


def test_explicit_classes_frozen_and_deduplicated(client, video_id, mock_model, monkeypatch):
    resolver = AsyncMock(return_value=["WRONG"])
    monkeypatch.setattr("app.routes.query.prompt_to_classes", resolver)
    response = client.post(
        "/query", json={"video_id": video_id, "classes": [" car ", "CAR", "person"], "prompt": "unrelated"}
    )
    assert response.json()["classes"] == ["car", "person"]
    mock_model.set_classes.assert_called_once_with(["car", "person"])
    resolver.assert_not_called()


def test_prompt_only_uses_same_resolver_as_classes_endpoint(client, video_id, monkeypatch):
    resolver = AsyncMock(return_value=["dog"])
    monkeypatch.setattr("app.routes.query.prompt_to_classes", resolver)
    response = client.post("/query", json={"video_id": video_id, "prompt": "find a dog"})
    assert response.json()["classes"] == ["dog"]
    resolver.assert_awaited_once()


@pytest.mark.parametrize(
    "options",
    [
        {"fps": 0},
        {"fps": 241},
        {"conf": -0.1},
        {"scan_mode": "bad"},
        {"frame_budget": 3},
        {"scan_mode": "budget", "frame_budget": 1},
        {"scan_mode": "budget", "max_sampled_frames": 3},
    ],
)
def test_invalid_scan_options(client, video_id, options):
    response = client.post("/query", json={"video_id": video_id, "classes": ["person"], **options})
    assert response.status_code == 422
