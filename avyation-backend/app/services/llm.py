"""Thin Gemini REST wrapper. Returns None when no key is configured or the call fails,
so every caller has a graceful offline fallback (important for a live demo)."""
import base64
import json
import logging
from typing import Optional

import httpx

from ..config import settings

log = logging.getLogger("avyation.llm")
_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


async def _call(parts: list[dict], json_mode: bool) -> Optional[str]:
    if not settings.gemini_api_key:
        return None
    body: dict = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.1}}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                _URL.format(model=settings.gemini_model),
                headers={"x-goog-api-key": settings.gemini_api_key},
                json=body,
            )
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:  # noqa: BLE001 - demo resilience beats purity
        log.warning("Gemini call failed: %s", exc)
        return None


async def gemini_json(prompt: str, file_bytes: Optional[bytes] = None,
                      mime_type: Optional[str] = None) -> Optional[dict]:
    parts: list[dict] = [{"text": prompt}]
    if file_bytes and mime_type:
        parts.append({"inline_data": {"mime_type": mime_type,
                                      "data": base64.b64encode(file_bytes).decode()}})
    text = await _call(parts, json_mode=True)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.warning("Gemini returned non-JSON: %s", text[:200])
        return None


async def gemini_text(prompt: str) -> Optional[str]:
    return await _call([{"text": prompt}], json_mode=False)
