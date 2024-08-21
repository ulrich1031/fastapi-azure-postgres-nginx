from uuid import UUID
from typing import Optional, List, Dict
from sqlmodel import Field, Column, Relationship
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from app.database.base.model import BaseModel, TimeStampMixin


class ReportModel(BaseModel, TimeStampMixin, table=True):
    """
    Represents a report in the agent database.

    Attributes:

        report_objective (Optional[str]): report objective. Default is None.
        
        report_target_audience (Optional[str]): report target audience. Default is None.
        
        report_additional_information (Optional[str]): report additional information. Default is None.
        
        report_content (Optional[str]): text content of the report. Default is None.
        
        tenant_id (Optional[UUID]): tenant id that this report is belongs to. Default is None.

        report_citations (List[UUID]): uuid of chunks that were used in the report.

        chunk_ids (List[UUID]): list of uuid of chunk in a database used for report generation. Default is [].
    """

    __tablename__ = "reports"
    report_objective: Optional[str] = Field(default=None)
    report_target_audience: Optional[str] = Field(default=None)
    report_additional_information: Optional[str] = Field(default=None)
    report_content: Optional[str] = Field(default=None)
    report_citations: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    chunk_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    tenant_id: Optional[UUID] = Field(default=None)
    
    chunks = Relationship(
        sa_relationship=relationship(
            "ChunkModel", cascade="all, delete-orphan"
        )
    )
