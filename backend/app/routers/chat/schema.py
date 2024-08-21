from uuid import UUID
from typing import List, Dict, Optional
from pydantic import BaseModel, field_validator

class QAChatRequestModel(BaseModel):
    content: str
    tenant_id: UUID
    
    @field_validator('content')  
    def content_length(cls, v):  
        if len(v) > 300:  
            raise ValueError('content length cannot exceed 300 characters')  
        return v

class ChatResponseModel(BaseModel):
    content: str