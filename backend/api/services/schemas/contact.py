from pydantic import BaseModel


class ContactRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    topic: str | None = None
    message: str | None = None
