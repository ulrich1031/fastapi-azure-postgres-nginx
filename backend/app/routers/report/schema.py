from uuid import UUID
from typing import List, Dict, Optional
from pydantic import BaseModel, field_validator
from app.utils.string import StringUtil
from app.enums.chunk_enum import ChunkTypeEnum

class ReportResponseModel(BaseModel):
    uuid: UUID
    report_content: Optional[str] = None
    report_citations: Optional[List[str]] = None
    report_target_audience: Optional[str] = None
    report_objective: Optional[str] = None
    report_additional_information: Optional[str] = None
    tenant_id: UUID
    
    @field_validator('report_content', mode="before")
    def update_content_and_citations(cls, v: str, values):
        if not v:
            return v
        extracted = StringUtil.extract_chunks_and_content(v)
        return extracted['content']

class GenerateReportRequestModel(BaseModel):
    auto_select: bool = True
    chunk_ids: Optional[List[UUID]] = []

class InitiateResearchRequestModel(BaseModel):
    tenant_id: UUID
    report_target_audience: str
    report_additional_information: str
    report_objective: str
    
class RunQueryRequestModel(BaseModel):
    query: str
    type: ChunkTypeEnum
    
class ChunkResponseModel(BaseModel):
    uuid: UUID
    type: str
    query: str
    captions_text: str
    llm_similarity_score: float
    source: str
    content: str

class ResearchResponseModel(BaseModel):
    internal: List[ChunkResponseModel] = []
    web: List[ChunkResponseModel] = []
    file: List[ChunkResponseModel] = []
    url: List[ChunkResponseModel] = []
    
    
class InitiateResearchResponseModel(BaseModel):
    report_id: UUID
    research_chunks: ResearchResponseModel
    
class ChatWithReportRequestModel(BaseModel):
    message: str
    
class ChatWithReportResponseModel(BaseModel):
    content: str

class SectionModel(BaseModel):
    title: str

class OutlineModel(BaseModel):
    title: str
    sections: List[SectionModel]