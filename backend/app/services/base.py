from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from app.utils.openai.azureopenai_client import AzureOpenAIClient
from app.utils.langfuse_client import LangFuseClient

class BaseService:
    """
    Base Service

    Attributes:

        db_session (AsyncSession): database session
    """
    azure_openai_client: Optional[AzureOpenAIClient]
    db_session: Optional[AsyncSession]

    def __init__(
        self,
        db_session: AsyncSession,
        langfuse_trace_args: Optional[dict] = None,
    ):
        self.db_session = db_session
        
        if langfuse_trace_args:
            if "metadata" not in langfuse_trace_args:
                langfuse_trace_args["metadata"] = {}
        
        self.langfuse_client = LangFuseClient()        
        self.langfuse_trace_args = langfuse_trace_args
        self.langfuse_trace = self.langfuse_client.get_trace_from_args(args=self.langfuse_trace_args)
        
        self.azure_openai_client = AzureOpenAIClient(langfuse_trace=self.langfuse_trace)