from uuid import UUID
from typing import Optional, Union, List, Any, Dict
from pydantic import BaseModel, field_validator
from .enum import QARequestTypeEnum, QAResponseTypeEnum
from ..base import WSErrorResponse

class QAMessageSchema(BaseModel):
    content: str
    files: Optional[List[str]] = None
    tenant_id: UUID
    
    @field_validator('content')  
    def content_length(cls, v):  
        if len(v) > 300:  
            raise ValueError('content length cannot exceed 300 characters')  
        return v
    
class QAMessageStreamResponse(BaseModel):
    content: str

class QAMessageEndResponse(BaseModel):
    content: str

class QAResponseSchema(BaseModel):
    type: str
    data: Optional[Union[QAMessageStreamResponse, QAMessageEndResponse, WSErrorResponse]]

class QARequestSchema(BaseModel):
    type: QARequestTypeEnum
    data: Optional[QAMessageSchema] = None
    config: Optional[Dict] = None