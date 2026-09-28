from __future__ import annotations

import json
import re
from typing import Any


def _heuristic_classes(prompt: str, *, max_classes: int = 10) -> list[str]:
    # Offline mode is deliberately comma-separated object phrases, not an NLP parser.
    return _normalize_classes((prompt or "").split(","), max_classes=max_classes)


def _normalize_classes(items: Any, *, max_classes: int = 10) -> list[str]:
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for it in items:
        if not isinstance(it, str):
            continue
        s = " ".join(it.strip().split())
        if not s:
            continue
        out.append(s)
    seen: set[str] = set()
    deduped: list[str] = []
    for s in out:
        k = s.lower()
        if k in seen:
            continue
        seen.add(k)
        deduped.append(s)
    return deduped[:max_classes]


async def prompt_to_classes(
    prompt: str,
    *,
    api_key: str = "",
    model: str = "openai/gpt-4o-mini",
    max_classes: int = 10,
) -> list[str]:
    if not api_key:
        return _heuristic_classes(prompt, max_classes=max_classes)

    url = "https://openrouter.ai/api/v1/chat/completions"

    system = (
        "You convert a user's free-form search prompt into a short list of object classes "
        "for open-vocabulary object detection. Output ONLY valid JSON: an array of 1-10 short strings. "
        "Each string should be a concrete visual object or attributeable object phrase (e.g., 'person', 'knife', "
        "'forklift', 'red helmet'). No explanations, no extra keys."
    )
    user_msg = f"Prompt: {prompt}\n\nReturn JSON array of object classes only."

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.2,
        "max_tokens": 120,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        import httpx

        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return _heuristic_classes(prompt, max_classes=max_classes)

    try:
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("Non-text class response")
        content = content.strip()
    except (KeyError, IndexError, TypeError, ValueError):
        return _heuristic_classes(prompt, max_classes=max_classes)

    if not content:
        return _heuristic_classes(prompt, max_classes=max_classes)

    try:
        parsed = json.loads(content)
        classes = _normalize_classes(parsed, max_classes=max_classes)
        return classes if classes else _heuristic_classes(prompt, max_classes=max_classes)
    except Exception:
        m = re.search(r"(\[[\s\S]*\])", content)
        if m:
            try:
                parsed = json.loads(m.group(1))
                classes = _normalize_classes(parsed, max_classes=max_classes)
                return classes if classes else _heuristic_classes(prompt, max_classes=max_classes)
            except Exception:
                return _heuristic_classes(prompt, max_classes=max_classes)
        return _heuristic_classes(prompt, max_classes=max_classes)
