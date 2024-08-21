from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends
from app.database.config import get_agent_db_session
from app.database.agent import ChunkService
from app.utils.logging import AppLogger
from app.exceptions.http_exception import NotFoundHTTPException
from .schema import *

logger = AppLogger().get_logger()

router = APIRouter(prefix="/chunk", tags=["Chunk"])

@router.get("/{chunk_id}", response_model=ChunkResponseModel)
async def get_chunk(
    chunk_id: UUID,
    agent_db_session=Depends(get_agent_db_session)
):
    """
    Get chunk
    """
    chunk_service = ChunkService(db_session=agent_db_session)
    result = await chunk_service.find_chunk_by_id(id=chunk_id)
    if not result:
        raise NotFoundHTTPException(msg=f"Chunk {chunk_id} not found")
    
    return result
    