from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException
from psycopg import errors

from config.settings import JWT_SECRET
from .repositories.user_repository import UserRepository
from .schemas.auth import LoginRequest, RegisterRequest
from .serializers import user_public


class AuthService:
    JWT_ALGORITHM = "HS256"

    def __init__(self) -> None:
        self.users = UserRepository()

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def _check_password(password: str, password_hash: str | None) -> bool:
        if not password_hash or password_hash == "SOCIAL_AUTH_PROVIDER":
            return False
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    def _token(self, user: dict[str, Any]) -> str:
        payload = {
            "id": user["user_id"],
            "email": user["email"],
            "role": user["role"],
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=self.JWT_ALGORITHM)

    def register(self, payload: RegisterRequest) -> dict[str, Any]:
        if not payload.name or not payload.email or not payload.password:
            raise HTTPException(status_code=400, detail="All fields are required")
        try:
            row = self.users.create(
                self.users.new_id(),
                payload.name,
                payload.email,
                self._hash_password(payload.password),
            )
        except errors.UniqueViolation as exc:
            raise HTTPException(status_code=400, detail="Email already exists") from exc
        return {"token": self._token(row), "user": user_public(row)}

    def login(self, payload: LoginRequest) -> dict[str, Any]:
        row = self.users.find_by_login(payload.email)
        if not row or not self._check_password(payload.password, row.get("password_hash")):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"token": self._token(row), "user": user_public(row)}
