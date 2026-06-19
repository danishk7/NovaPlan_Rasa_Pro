from typing import Any

from pydantic import BaseModel, Field


class ItineraryRequest(BaseModel):
    itnId: str | None = None
    userId: str
    time: str | None = None
    title: str
    summary: dict[str, Any] = Field(default_factory=dict)
    status: str | None = "pending"
