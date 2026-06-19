from typing import Any

from .repositories.contact_repository import ContactRepository
from .schemas.contact import ContactRequest
from .serializers import contact_public


class ContactService:
    def __init__(self) -> None:
        self.contacts = ContactRepository()

    def create(self, payload: ContactRequest) -> dict[str, bool]:
        self.contacts.create(payload.name, payload.email, payload.topic, payload.message)
        return {"success": True}

    def list_all(self) -> list[dict[str, Any]]:
        return [contact_public(r) for r in self.contacts.list_all()]
