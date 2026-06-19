from typing import Any

from fastapi import HTTPException
from .repositories.user_repository import UserRepository
from .serializers import user_public


class UserService:
    def __init__(self) -> None:
        self.users = UserRepository()

    def list_users(self) -> list[dict[str, Any]]:
        return self.users.list_public()

    def update_role(self, user_id: str, role: str) -> dict[str, Any]:
        if role not in {"user", "admin", "support"}:
            raise HTTPException(status_code=400, detail="Invalid role")
        row = self.users.update_role(user_id, role)
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return row

    def delete_user(self, user_id: str) -> dict[str, bool]:
        row = self.users.delete(user_id)
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return {"success": True}

    def get_profile(self, user_id: str) -> dict[str, Any]:
        row = self.users.find_by_id(user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        return user_public(row)

    def update_profile(self, user_id: str, updates: dict[str, Any]) -> dict[str, bool]:
        allowed = {
            "name": "name",
            "bio": "bio",
            "location": "location",
            "loyaltyTier": "loyalty_tier",
            "role": "role",
        }
        fields: list[tuple[str, str, Any]] = []
        for key in updates:
            if key in allowed:
                fields.append((key, allowed[key], updates[key]))
        if not fields:
            raise HTTPException(status_code=400, detail="No valid fields")
        self.users.update_profile(user_id, fields)
        return {"success": True}
