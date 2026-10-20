"""TinyFish Web Agent client (https://docs.tinyfish.ai/agent-api).

Auth is the `X-API-Key` header. `POST /v1/automation/run` blocks until the goal is done and
returns {status, result, ...}. Docs say to validate the *content* of `result`, not just
`status`, so `run()` raises TinyFishError for COMPLETED-but-failed runs too.

Request body is {"url": <start page>, "goal": <natural-language instructions>} - double-check
against https://docs.tinyfish.ai/agent-api/reference if you tweak optional fields.
"""
from typing import Any, Optional

import httpx

from ..config import settings


class TinyFishError(RuntimeError):
    pass


class TinyFishClient:
    @property
    def enabled(self) -> bool:
        return bool(settings.tinyfish_api_key)

    def _headers(self) -> dict:
        return {"X-API-Key": settings.tinyfish_api_key, "Content-Type": "application/json"}

    async def run(self, url: str, goal: str, timeout: float = 240.0) -> Any:
        """Synchronous run. Returns the `result` payload of a successful automation."""
        if not self.enabled:
            raise TinyFishError("TINYFISH_API_KEY is not set")
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                f"{settings.tinyfish_base_url}/v1/automation/run",
                headers=self._headers(),
                json={"url": url, "goal": goal},
            )
        if r.status_code >= 400:
            raise TinyFishError(f"HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        result = data.get("result")
        if data.get("status") != "COMPLETED" or not result:
            msg = (data.get("error") or {}).get("message") if isinstance(data.get("error"), dict) else data.get("error")
            raise TinyFishError(f"Run did not complete: status={data.get('status')} error={msg}")
        if isinstance(result, dict) and (result.get("status") == "failure" or result.get("error")):
            raise TinyFishError(f"Goal not achieved: {result.get('reason') or result.get('error')}")
        return result

    # Optional: long filings can use the async pattern instead of holding an HTTP request open.
    async def run_async(self, url: str, goal: str) -> Optional[str]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{settings.tinyfish_base_url}/v1/automation/run-async",
                headers=self._headers(),
                json={"url": url, "goal": goal},
            )
        if r.status_code >= 400:
            raise TinyFishError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json().get("run_id")

    async def get_run(self, run_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{settings.tinyfish_base_url}/v1/runs/{run_id}",
                                 headers={"X-API-Key": settings.tinyfish_api_key})
        if r.status_code >= 400:
            raise TinyFishError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()


tinyfish = TinyFishClient()
