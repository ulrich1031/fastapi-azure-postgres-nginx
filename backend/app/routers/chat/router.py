from typing import List
from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.database.config import get_agent_db_session, get_main_db_session
from app.services import ChatService
from app.enums.chat_enum import ChatTypeEnum
from app.utils.logging import AppLogger

logger = AppLogger().get_logger()

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/{session_id}/upload-files")
async def upload_files(
    session_id: str,
    files: List[UploadFile] = File(...),
    main_db_session=Depends(get_main_db_session),
    agent_db_session=Depends(get_agent_db_session)
):
    """
    Upload files to the chat session
    
    Parameters:
    
        session_id (str): session id of the chat
        
    Returns:

        bool: return result
    """
    chat_service = ChatService(
        tenant=None,
        session_id=session_id,
        type=ChatTypeEnum.QA.value,
        db_session=agent_db_session
    )
    
    await chat_service.embed_uploaded_files(
        files=files
    )
    
    return True