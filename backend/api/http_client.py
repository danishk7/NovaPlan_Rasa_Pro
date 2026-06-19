from __future__ import annotations

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

RETRYABLE = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.NetworkError,
)


def _retry_decorator():
    return retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(RETRYABLE),
    )


@_retry_decorator()
async def get_json(
    url: str,
    *,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    follow_redirects: bool = True,
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=follow_redirects) as client:
        response = await client.get(url, headers=headers, params=params)
    return response


@_retry_decorator()
async def post_json(
    url: str,
    *,
    json: dict[str, Any] | list[Any],
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    merged = {"Content-Type": "application/json", **(headers or {})}
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=json, headers=merged)
    return response
