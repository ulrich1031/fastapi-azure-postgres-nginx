import uuid
from typing import Optional, Type, List
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool, tool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from app.utils.exa_client import ExaClient

class ExaSearchInput(BaseModel):
    urls: List[str] = Field(description="urls to search through")
    query: str = Field(description="query to search through urls")

class ExaSearchTool(BaseTool):
    name = "exa_search_tool"
    description = "useful to search through user specified urls"
    args_schema: Type[BaseModel] = ExaSearchInput
    exa_client: ExaClient
    cfg: dict = {
        'top': 1
    }
    
    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        raise NotImplemented

    async def _arun(
        self, urls: List[str], query: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        results = await self.exa_client.get_contents(
                ids=urls,
                highlights={
                    "query": query,
                    "highlightsPerUrl": 3, 
                    "numSentences": 3
                }
            )
        
        return [
            {
                "uuid": str(uuid.uuid4()),
                "query": query,
                **result.model_dump()
            }
            for result in results
        ]