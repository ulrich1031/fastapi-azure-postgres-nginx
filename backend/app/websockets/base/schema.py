from pydantic import BaseModel

class WSErrorResponse(BaseModel):
    content: str