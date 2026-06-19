from fastapi import APIRouter

from .auth import router as auth_router
from .sessions import router as sessions_router
from .contacts import router as contacts_router
from .conversations import router as conversations_router
from .health import router as health_router
from .itineraries import router as itineraries_router
from .test_results import router as test_results_router
from .users import router as users_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(contacts_router)
api_router.include_router(sessions_router)
api_router.include_router(conversations_router)
api_router.include_router(itineraries_router)
api_router.include_router(test_results_router)
