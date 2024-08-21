from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends
from app.database.config import get_agent_db_session
from app.database.agent import MessageService
from app.utils.logging import AppLogger
from app.exceptions.http_exception import NotFoundHTTPException
from .schema import *

logger = AppLogger().get_logger()

router = APIRouter(prefix="/message", tags=["Messages"])

@router.get("/{session_id}", response_model=List[MessageResponseModel])
async def get_messages_by_session_id(
    session_id: str,
    agent_db_session=Depends(get_agent_db_session)
):
    """
    Get chat histories.
    """
    message_service = MessageService(db_session=agent_db_session)
    messages = await message_service.find_by_session_id(session_id=session_id)
    return [MessageResponseModel(**message.model_dump()) for message in messages]
    