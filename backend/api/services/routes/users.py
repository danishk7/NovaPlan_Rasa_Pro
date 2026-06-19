from fastapi import APIRouter, Depends, Request

from ..auth_dependencies import current_user, require_roles, require_self_or_roles
from ..user_service import UserService

router = APIRouter(tags=["users"])
_users = UserService()


@router.get("/users")
def get_users(_user=Depends(require_roles("admin"))):
    return _users.list_users()


@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: str, request: Request, _user=Depends(require_roles("admin"))):
    payload = await request.json()
    return _users.update_role(user_id, payload.get("role"))


@router.delete("/users/{user_id}")
def delete_user(user_id: str, _user=Depends(require_roles("admin"))):
    return _users.delete_user(user_id)


@router.get("/profile/{user_id}")
def get_profile(user_id: str, user=Depends(current_user)):
    require_self_or_roles(user_id, user, "admin", "support")
    return _users.get_profile(user_id)


@router.patch("/profile/{user_id}")
async def update_profile(user_id: str, request: Request, user=Depends(current_user)):
    require_self_or_roles(user_id, user, "admin")
    updates = await request.json()
    if user.get("role") != "admin":
        updates.pop("role", None)
    return _users.update_profile(user_id, updates)
