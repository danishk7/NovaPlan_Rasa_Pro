from fastapi import APIRouter, Depends

from ..auth_dependencies import require_roles
from ..schemas.contact import ContactRequest
from ..contact_service import ContactService

router = APIRouter(tags=["contacts"])
_contacts = ContactService()


@router.post("/contact")
def create_contact(payload: ContactRequest):
    return _contacts.create(payload)


@router.get("/contacts")
def get_contacts(_user=Depends(require_roles("admin", "support"))):
    return _contacts.list_all()
