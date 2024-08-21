from uuid import UUID
from pydantic import BaseModel

class ChunkResponseModel(BaseModel):
    uuid: UUID
    type: str
    query: str
    captions_text: str
    llm_similarity_score: float
    source: str
    content: str