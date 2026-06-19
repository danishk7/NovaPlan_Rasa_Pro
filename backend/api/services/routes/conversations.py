from fastapi import APIRouter, Depends, HTTPException

from ..auth_dependencies import current_user
from ..schemas.conversation import ConversationRequest
from ..session_service import SessionService

router = APIRouter(tags=["conversations"])
_sessions = SessionService()


@router.post("/conversations")
def create_conversation(payload: ConversationRequest, user=Depends(current_user)):
    if user.get("role") not in {"admin", "support"}:
        session = _sessions.get_session(payload.sesId)
        if not session or session.get("user_id") != user.get("user_id"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        payload.userId = user.get("user_id")
    return _sessions.create_conversation(payload)
