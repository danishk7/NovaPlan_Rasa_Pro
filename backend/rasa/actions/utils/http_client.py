from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

RETRYABLE = (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)


def _retry():
    return retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(RETRYABLE),
    )


@_retry()
async def get(
    url: str,
    *,
    timeout: float = 12.0,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        return await client.get(url, params=params, headers=headers)


@_retry()
async def post(
    url: str,
    *,
    json: dict[str, Any],
    timeout: float = 8.0,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    merged = {"Content-Type": "application/json", **(headers or {})}
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.post(url, json=json, headers=merged)
