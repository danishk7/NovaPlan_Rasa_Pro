from fastapi import APIRouter, Depends

from ..auth_dependencies import current_user, require_self_or_roles
from ..schemas.itinerary import ItineraryRequest
from ..itinerary_service import ItineraryService

router = APIRouter(tags=["itineraries"])
_itineraries = ItineraryService()


@router.get("/itineraries/{user_id}")
def get_itineraries(user_id: str, user=Depends(current_user)):
    require_self_or_roles(user_id, user, "admin", "support")
    return _itineraries.list_for_user(user_id)


@router.post("/itineraries")
def create_itinerary(payload: ItineraryRequest, user=Depends(current_user)):
    require_self_or_roles(payload.userId, user, "admin", "support")
    return _itineraries.create(payload)
