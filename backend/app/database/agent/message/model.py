from typing import Optional, List
from sqlmodel import Field, JSON
from sqlalchemy import Column
from app.database.base.model import BaseModel, TimeStampMixin
from app.enums import MessageRoleEnum


class MessageModel(BaseModel, TimeStampMixin, table=True):
    """
    Represents a tenant in the database.

    Attributes:

        session_id (str): chat session id
        
        role (str): "system", "assistant" or "user"
        
        content (str): message content
        
        files (List[str]): files attached to this message.
    """
    
    __tablename__ = "messages"
    
    session_id: str = Field(
        index=True, nullable=False
    )
    role: str = Field(default=MessageRoleEnum.USER.value, nullable=False)
    content: Optional[str] = Field(default=None)
    files: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    type: str = Field(nullable=False)