import json
from typing import Any

from .repositories.conversation_repository import ConversationRepository
from .repositories.session_repository import SessionRepository
from .repositories.user_repository import UserRepository
from .schemas.conversation import ConversationRequest
from .serializers import conversation_public, session_public


class SessionService:
    def __init__(self) -> None:
        self.sessions = SessionRepository()
        self.conversations = ConversationRepository()
        self.users = UserRepository()

    def get_or_create_user_session(self, user_id: str) -> dict[str, Any]:
        session = self.sessions.find_active_for_user(user_id)
        if not session:
            created = self.sessions.create(
                self.sessions.new_session_id(),
                user_id,
            )
            session = self.sessions.find_by_id(created["ses_id"])
        return session_public(session)

    def list_sessions(self) -> list[dict[str, Any]]:
        return [session_public(r) for r in self.sessions.list_all()]

    def get_session(self, ses_id: str) -> dict[str, Any] | None:
        return self.sessions.find_by_id(ses_id)

    def list_conversations(self, ses_id: str) -> list[dict[str, Any]]:
        return [conversation_public(r) for r in self.conversations.list_for_session(ses_id)]

    def create_conversation(self, payload: ConversationRequest) -> dict[str, bool]:
        self.conversations.create(
            payload.sesId,
            payload.userId,
            payload.text,
        )
        self.sessions.touch(payload.sesId)
        return {"success": True}

    def request_human(self, ses_id: str) -> dict[str, bool]:
        self.sessions.mark_needs_human(ses_id)
        return {"success": True}

    def persist_handoff(self, ses_id: str, summary: dict[str, Any], ticket_id: str) -> None:
        text = json.dumps({"ticket_id": ticket_id, "handover_summary": summary}, ensure_ascii=False)
        self.sessions.upsert_handoff(ses_id)
        self.conversations.create(ses_id, None, text)
