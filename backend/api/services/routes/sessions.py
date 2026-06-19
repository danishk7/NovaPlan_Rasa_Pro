from fastapi import APIRouter, Depends, HTTPException

from ..auth_dependencies import current_user, require_roles, require_self_or_roles
from ..session_service import SessionService

router = APIRouter(tags=["sessions"])
_sessions = SessionService()


def _require_session_access(ses_id: str, user: dict) -> None:
    if user.get("role") in {"admin", "support"}:
        return
    session = _sessions.get_session(ses_id)
    if session and session.get("user_id") == user.get("user_id"):
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")


@router.get("/sessions/user/{user_id}")
def get_or_create_session(user_id: str, user=Depends(current_user)):
    require_self_or_roles(user_id, user, "admin", "support")
    return _sessions.get_or_create_user_session(user_id)


@router.get("/sessions")
def get_sessions(_user=Depends(require_roles("admin", "support"))):
    return _sessions.list_sessions()


@router.get("/sessions/{ses_id}/conversations")
def get_conversations(ses_id: str, user=Depends(current_user)):
    _require_session_access(ses_id, user)
    return _sessions.list_conversations(ses_id)


@router.post("/sessions/{ses_id}/request-human")
def request_human(ses_id: str, user=Depends(current_user)):
    _require_session_access(ses_id, user)
    return _sessions.request_human(ses_id)
