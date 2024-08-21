import json
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from tavily.async_tavily import AsyncTavilyClient
from app.config import get_settings
from app.utils.langfuse_client import StatefulTraceClient

class TavilySearchContextResponse(BaseModel):
    url: str
    content: str

class TavilyClient:
    
    def __init__(
        self,
        langfuse_trace: Optional[StatefulTraceClient] = None
    ):
        self.settings = get_settings()
        self.client = AsyncTavilyClient(api_key=self.settings.TAVILY_API_KEY)
        self.langfuse_trace = langfuse_trace
        
    async def get_search_context(self, **kwargs) -> List[TavilySearchContextResponse]:
        langfuse_span = None
        
        if self.langfuse_trace:
            langfuse_span = self.langfuse_trace.span(
                name="tavily-search-context",
                input=kwargs,
                start_time=datetime.now()
            )
            
        results = await self.client.get_search_context(**kwargs)
        results = json.loads(json.loads(results))
        
        if langfuse_span:
            langfuse_span.update(
                output=results,
                end_time=datetime.now()
            )
        
        return [
            TavilySearchContextResponse(
                url=json.loads(result)['url'] if json.loads(result)['url'] else "",
                content=json.loads(result)['content']
            )
            for result in results
        ]