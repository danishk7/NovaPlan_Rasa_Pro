from pydantic import BaseModel


class ConversationRequest(BaseModel):
    sesId: str
    userId: str | None = None
    text: str
