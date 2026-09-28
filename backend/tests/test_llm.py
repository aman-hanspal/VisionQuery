from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.llm import _normalize_classes


def test_deduplicate_before_applying_class_limit():
    assert _normalize_classes(["car", "CAR", "person", "dog"], max_classes=2) == ["car", "person"]


@pytest.mark.parametrize("payload", [{}, {"choices": []}, {"choices": [{"message": {"content": None}}]}])
def test_malformed_provider_response_falls_back(payload, mock_settings, mock_model, monkeypatch):
    mock_settings.OPENROUTER_API_KEY = "test-key"
    response = MagicMock()
    response.json.return_value = payload
    http = AsyncMock()
    http.__aenter__.return_value.post.return_value = response
    monkeypatch.setattr("httpx.AsyncClient", lambda **_: http)
    with TestClient(create_app(mock_settings, lambda _: mock_model)) as client:
        result = client.post("/classes", json={"prompt": "car, person"})
    assert result.status_code == 200
    assert result.json()["classes"] == ["car", "person"]
