import os
from typing import Optional, Any, List
from datetime import datetime
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import get_settings
from app.utils.logging import AppLogger
from app.utils.langfuse_client import StatefulTraceClient

logger = AppLogger().get_logger()

class FaissVectorRetriever:
    
    def __init__(
        self,
        langfuse_trace: Optional[StatefulTraceClient] = None,
        file_path: Optional[str] = "",
        embeddings: Optional[Any] = None,
        splitters: Optional[Any] = None,
        file_path_prefix: Optional[str] = "./static/faiss-indexes/"
    ):
        self.settings = get_settings()
        if embeddings == None:
            self.embeddings = AzureOpenAIEmbeddings(
                azure_deployment=self.settings.AZURE_EMBEDDING_MODEL,
                openai_api_version=self.settings.AZURE_OPENAI_API_VERSION
            )
        else:
            self.embeddings = embeddings
        
        if splitters == None:
            self.splitters = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=0  
            )
        else:
            self.splitters = splitters
        
        self.file_path = file_path_prefix + file_path
        if self.file_path and os.path.exists(self.file_path):
            self.db = FAISS.load_local(
                self.file_path,
                allow_dangerous_deserialization=True,
                embeddings=self.embeddings
            )
        else:
            self.db: FAISS = None
        
        self.langfuse_trace = langfuse_trace
    
    async def asimilarity_search(self, **kwargs) -> List[Document]:
        
        langfuse_span = None
        
        if self.langfuse_trace:
            langfuse_span = self.langfuse_trace.span(
                name="local-file-search",
                input={
                    **kwargs
                },
                start_time=datetime.now()
            )
        
        result = await self.db.asimilarity_search(**kwargs)
        
        if langfuse_span:
            langfuse_span.update(
                output=result,
                end_time=datetime.now()
            )
        
        return result
    
    async def add_documents(self, documents: List[Document], save_local: bool = True, split: bool = True, **kwargs) -> List[str]:
        """
        Add documents to FAISS vector store.
        
        Parameters:
            documents (List[Document]): documents to add
            save_local (bool): Whether to save result to local. Default to True.
            split (bool): Whether to split document with splitters. Default to True.
        """
        if split == True:
            docs = self.splitters.split_documents(documents)
        else:
            docs = documents
        
        if len(docs) == 0:
            return
        
        if not self.db:
            self.db = await FAISS.afrom_documents(docs, embedding=self.embeddings)
        else:
            ids = await self.db.aadd_documents(docs)
        
        if save_local == True and self.file_path:
            self.db.save_local(self.file_path)
        
        # return ids