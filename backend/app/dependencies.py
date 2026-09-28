from __future__ import annotations

import threading

from fastapi import Request

from app.config import Settings


def get_model(request: Request):
    return request.app.state.model


def get_model_lock(request: Request) -> threading.Lock:
    return request.app.state.model_lock


def get_settings(request: Request) -> Settings:
    return request.app.state.settings
