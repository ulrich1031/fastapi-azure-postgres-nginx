from uuid import UUID
from sqlmodel import select
from sqlalchemy import desc
from sqlalchemy.exc import NoResultFound
from .model import ChunkModel
from app.enums import ChunkTypeEnum
from app.database.base.service import BaseService
from app.utils.logging import AppLogger


logger = AppLogger().get_logger()


class ChunkService(BaseService):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def add_chunk(self, chunk: ChunkModel):
        """
        Add chunk to database

        Parameters:

            chunk (ChunkModel): chunk to add

        Returns:

            Optional[ChunkModel]: updated chunk model
        """
        await chunk.save(db_session=self.db_session)
        return chunk
    
    async def find_chunks_by_report_id_and_type(self, report_id: UUID, type: str, skip = 0, limit = 10):
        """
        Retrieve chunk by report id and type.
        """
        statement = (select(ChunkModel)
                     .where(ChunkModel.report_id == report_id, ChunkModel.type == type)
                     .order_by(desc(ChunkModel.llm_similarity_score))
                     .offset(skip)
                     .limit(limit))
        
        try:
            results = await self.db_session.exec(statement)
            return results.all()
        except NoResultFound:
            return []
    
    async def find_chunks_by_report_id(self, report_id: UUID, skip = 0, limit = 10):
        """
        Retrieve chunks by report id.
        """
        statement = (select(ChunkModel)
                     .where(ChunkModel.report_id == report_id)
                     .order_by(desc(ChunkModel.llm_similarity_score))
                     .offset(skip)
                     .limit(limit))
        
        try:
            results = await self.db_session.exec(statement)
            return results.all()
        except NoResultFound:
            return []
    
    async def find_chunk_by_id(self, id: UUID):
        """
        Retrieve chunk by uuid.
        """
        statement = select(ChunkModel).where(ChunkModel.uuid == id)

        try:
            result = await self.db_session.exec(statement)
            return result.one()
        except NoResultFound:
            return None
        
