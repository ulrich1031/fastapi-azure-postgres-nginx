import uuid
from typing import Optional, Type
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool, tool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from app.utils.vector_retriever import FaissVectorRetriever

class SearchInput(BaseModel):
    query: str = Field(description="query to look up user uploaded files")

class FaissVectorSearchTool(BaseTool):
    name = "faiss_search_tool"
    description = "useful to search through user uploaded files in the specific chat session"
    args_schema: Type[BaseModel] = SearchInput
    retriever: FaissVectorRetriever
    cfg: dict = {
        'top': 1
    }
    
    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        raise NotImplemented

    async def _arun(
        self, query: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        results = await self.retriever.asimilarity_search(query=query, k=self.cfg['top'])
        
        return [
            {
                "uuid": str(uuid.uuid4()),
                "query": query,
                **result.dict()
            }
            for result in results
        ]