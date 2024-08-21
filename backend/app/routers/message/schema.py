from uuid import UUID
from pydantic import BaseModel

class MessageResponseModel(BaseModel):
    uuid: UUID
    role: str
    content: str
    