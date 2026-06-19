from typing import Any

from .repositories.itinerary_repository import ItineraryRepository
from .schemas.itinerary import ItineraryRequest
from .serializers import itinerary_public


class ItineraryService:
    def __init__(self) -> None:
        self.itineraries = ItineraryRepository()

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        return [itinerary_public(r) for r in self.itineraries.list_for_user(user_id)]

    def create(self, payload: ItineraryRequest) -> dict[str, bool]:
        itn_id = self.itineraries.create(
            payload.userId,
            payload.time,
            payload.title,
            payload.summary,
            payload.status or "confirmed",
            payload.itnId,
        )
        return {"success": True, "itnId": itn_id}

    @staticmethod
    def _metadata_user(payload: dict[str, Any]) -> dict[str, str]:
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            user_id = metadata.get("userId") or metadata.get("user_id")
            if user_id:
                return {"userId": str(user_id), "name": str(metadata.get("userName") or metadata.get("user_name") or "Traveler")}

        sender = payload.get("sender")
        if sender and str(sender) != "guest":
            return {"userId": str(sender), "name": "Traveler"}
        return {}

    def remove_guest_notice(self, payload: dict[str, Any], responses: Any) -> Any:
        if not self._metadata_user(payload) or not isinstance(responses, list):
            return responses
        for message in responses:
            if not isinstance(message, dict):
                continue
            text = str(message.get("text") or "")
            if "Guest chat" in text.lower() and "kept the itinerary in this session" in text.lower():
                message["text"] = ""
        return responses
