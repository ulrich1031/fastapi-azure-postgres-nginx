import uuid
from typing import Optional, Type
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool, tool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from app.utils.tavily_client import TavilyClient, TavilySearchContextResponse


class TavilySearchInput(BaseModel):
    query: str = Field(description="query to look up web")

class TavilySearchTool(BaseTool):
    name = "tavily_search_tool"
    description = "useful to search through web"
    args_schema: Type[BaseModel] = TavilySearchInput
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
        tavily_client = TavilyClient()
        results = await tavily_client.get_search_context(query=query, search_depth='advanced', max_results=self.cfg['top'])
        
        return [
            {
                "uuid": str(uuid.uuid4()),
                "query": query,
                **result.model_dump()
            }
            for result in results
        ]