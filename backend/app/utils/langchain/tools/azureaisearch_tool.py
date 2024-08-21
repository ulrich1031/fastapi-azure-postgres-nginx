import uuid
from typing import Optional, Type
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool, tool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from app.utils.vector_retriever.azureaisearch import AzureAISearchVectorRetriever

class SearchInput(BaseModel):
    query: str = Field(description="query to look up internal documents")

class AzureAISearchTool(BaseTool):
    name = "azure_ai_search_tool"
    description = "useful to search through internal documents"
    args_schema: Type[BaseModel] = SearchInput
    retriever: AzureAISearchVectorRetriever
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
        results = await self.retriever.run(query=query, top=self.cfg['top'])
        
        return [
            {
                "uuid": str(uuid.uuid4()),
                "query": query,
                **result.model_dump()
            }
            for result in results
        ]