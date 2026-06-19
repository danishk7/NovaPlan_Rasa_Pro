from fastapi import APIRouter

from ..schemas.auth import LoginRequest, RegisterRequest
from ..auth_service import AuthService

router = APIRouter(tags=["auth"])
_auth = AuthService()


@router.post("/register")
def register(payload: RegisterRequest):
    return _auth.register(payload)


@router.post("/login")
def login(payload: LoginRequest):
    return _auth.login(payload)
