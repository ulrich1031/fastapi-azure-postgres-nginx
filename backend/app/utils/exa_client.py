import aiohttp
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.config import get_settings
from app.utils.logging import AppLogger
from app.utils.langfuse_client import StatefulTraceClient

logger = AppLogger().get_logger()

class ExaGetContentResponse(BaseModel):
    url: str
    highlight: str

class ExaClient:
    """
    ** This client didn't use Exa python sdk because it does not support async. **
    """
    def __init__(
        self, 
        langfuse_trace: Optional[StatefulTraceClient] = None
    ):
        self.settings = get_settings()
        self.api_url = "https://api.exa.ai/contents"
        self.api_headers = {  
            "accept": "application/json",  
            "content-type": "application/json",  
            "x-api-key": self.settings.EXA_API_KEY
        }
        self.langfuse_trace = langfuse_trace
    
    async def get_contents(
        self,
        **kwargs
    ) -> List[ExaGetContentResponse]:
        langfuse_span = None
        
        if self.langfuse_trace:
            langfuse_span = self.langfuse_trace.span(
                name="exa-ai-search",
                input={
                    **kwargs
                },
                start_time=datetime.now()
            )
        async with aiohttp.ClientSession() as session:  
            async with session.post(self.api_url, json={'text': False, **kwargs}, headers=self.api_headers) as response:  
                response_data = await response.json()
                if langfuse_span:
                    langfuse_span.update(
                        output=response_data,
                        end_time=datetime.now()
                    )
                results = response_data['results']
                exa_response = []
                for result in results:
                    exa_response.extend(
                        [
                            ExaGetContentResponse(
                                url=result['id'],
                                highlight=highlight
                            )
                            for highlight in result['highlights']
                        ]
                    )
                
                return exa_response