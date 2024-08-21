from typing import Optional
from datetime import datetime
from openai import AsyncAzureOpenAI
from app.config import Settings, get_settings
from app.utils.logging import AppLogger, ElapsedTimeLogger
from app.utils.langfuse_client import StatefulTraceClient


logger = AppLogger().get_logger()


class AzureOpenAIClient:
    """
    AzureOpenAI Async Client
    
    Arguments:
    
        settings (Settings): configuration variables. By default, it loads configuration variables from environment variables.
        
        langfuse_trace (Optional[StatefulTraceClient]): LangFuse trace.
    """
    def __init__(
        self,
        langfuse_trace: Optional[StatefulTraceClient] = None,
        settings: Settings = get_settings()
    ):
        self.settings = settings
        self.client = AsyncAzureOpenAI(
            azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
            api_key=self.settings.AZURE_OPENAI_API_KEY,
            api_version=self.settings.AZURE_OPENAI_API_VERSION,
        )
        
        self.langfuse_trace = langfuse_trace

    async def ainvoke(self, name: Optional[str] = None, **kwargs):
        """
        name (str): used for logging and langfuse trace.
        """
        with ElapsedTimeLogger("Azure openai invoking" + f": {name}" if name else ""):
            if "model" not in kwargs:
                kwargs["model"] = self.settings.SMART_LLM_MODEL

            start_time = datetime.now()
            
            if self.langfuse_trace:
                generation = self.langfuse_trace.generation(
                    name=name,
                    model=kwargs["model"],
                    input=kwargs['messages'],
                    start_time=start_time
                )
                
            response = await self.client.chat.completions.create(**kwargs)
            end_time = datetime.now()
            
            if self.langfuse_trace:
                generation.update(
                    usage=response.usage,
                    output=response.choices[0].message.content,
                    end_time=end_time,
                )
            
            return response.choices[0].message.content

    async def astream(self, **kwargs):
        if "model" not in kwargs:
            kwargs["model"] = self.settings.SMART_LLM_MODEL

        stream = await self.client.chat.completions.create(**kwargs, stream=True)

        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
