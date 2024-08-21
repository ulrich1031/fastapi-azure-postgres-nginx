from uuid import UUID
from typing import Optional, List, Dict
from sqlmodel import Field
from sqlalchemy.orm import relationship
from app.database.base.model import BaseModel, TimeStampMixin
from app.enums import ChunkTypeEnum


class ChunkModel(BaseModel, TimeStampMixin, table=True):
    """
    Represents a chunk of reaserch in the agent database.

    Attributes:

        report_id (str): The uuid of the report that this chunk is asscoiated with. When associated report is deleted, chunk will be removed automatically. 
        
        session_id (str): Session id in case this chunk was used in chat. Otherwise, it will be None.

        type (str): The type of chunk. It can be "INTERNAL" or "WEB". Defaults to "INTERNAL".

        query (str): The query used for generating this chunk. This is a  required field.

        llm_similarity_score (Optional[float]): The similarity score of the chunk compared with report information, calculated by LLM. Defaults to 0.0.

        vector_similarity_score (Optional[float]): The vector similarity score compared with search query, associated with the chunk.  Defaults to 0.0.

        source (Optional[str]): Source of the chunk: filename or url. Defaults to None.

        content (Optional[str]): The content of the chunk. This can be None if the content is not provided.

        captions_text (Optional[str]): The text extracted from captions within this chunk, if available. Defaults to None.

        captions_highlights (Optional[str]): Highlights extracted from captions within this chunk, if available. Defaults to None.

    """

    __tablename__ = "chunks"
    type: str = Field(default=ChunkTypeEnum.INTERNAL.value, nullable=False)
    query: str = Field(nullable=False)
    llm_similarity_score: Optional[float] = Field(default=0.0)
    vector_similarity_score: Optional[float] = Field(default=0.0)
    source: Optional[str] = Field(default=None)
    content: Optional[str] = Field(default=None)
    captions_text: Optional[str] = Field(default=None)
    captions_highlights: Optional[str] = Field(default=None)

    report_id: Optional[UUID] = Field(default=None, foreign_key="reports.uuid")
    session_id: Optional[str] = Field(default=None)