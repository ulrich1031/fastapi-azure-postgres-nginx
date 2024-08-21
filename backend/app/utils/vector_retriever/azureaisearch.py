import os
import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from app.utils.langfuse_client import StatefulTraceClient

class AzureAISearchResponse(BaseModel):
    score: float
    source: str
    content: str
    highlights: str
    

class AzureAISearchVectorRetriever:
    
    def __init__(
        self,
        service_name,
        index_name,
        langfuse_trace: Optional[StatefulTraceClient] = None,
        **kwargs
    ):
        self.retriever = SearchClient(
            endpoint=f"https://{service_name}.search.windows.net",
            index_name=index_name,
            credential=AzureKeyCredential(os.environ.get('AZURE_AI_SEARCH_API_KEY', "")),
            api_version=os.environ.get('AZURE_AI_SEARCH_API_VERSION', "2024-05-01-preview")
        )
        self.langfuse_trace = langfuse_trace
    
    def __clean_result_content__(self, text):
        """
        removes ansi codes from text
        replaces all whitespace with a single space
        also replaces unicode like \\u00b7 with ascii characters
        """
        # Remove ANSI codes
        text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
        
        # Replace all whitespace with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Decode Unicode escape sequences
        text = text.encode('utf-8').decode('unicode_escape')
        
        # Encode back to ASCII, ignoring non-ASCII characters
        text = text.encode('ascii', 'ignore').decode('ascii')
        
        # Remove all dangling backslashes
        text = text.replace('\\', '')
        
        # replace null bytes
        text = text.replace('\x00', '')

        return text
    
    async def run(self, query: str, top: int = 5, **kwargs) -> List[AzureAISearchResponse]:
        """
        Retrieve the most relevant chunks to the query.
        
        Parameters:
        
            query (str): search query
            
            top (int): number of chunks to fetch. Default is 5.
            
        Returns:
            
            List of chunks in AzureAISearchResponse.

            [{
                'source': 'abc.docx',
                'content': '.....',
                'highlights': '.....',
                'score': 2.34
            }]
        """
        
        langfuse_span = None
        
        if self.langfuse_trace:
            langfuse_span = self.langfuse_trace.span(
                name="azure-ai-search",
                input={
                    'query': query,
                    'top': top,
                    **kwargs
                },
                start_time=datetime.now()
            )
            
        results = self.retriever.search(
            search_text=query,
            top=top,
            query_type="semantic",
            query_caption="extractive",
            semantic_configuration_name="my-semantic-config",
            **kwargs
        )
        
        final_results = [
            AzureAISearchResponse(
                source=result['FilePath'],
                content=self.__clean_result_content__(result['Content']),
                highlights=self.__clean_result_content__(result["@search.captions"][0].text),
                score=result["@search.reranker_score"]
            )
            for i, result in enumerate(results)
        ]
        
        if langfuse_span:
            langfuse_span.update(
                output=final_results,
                end_time=datetime.now()
            )
                
        return final_results
        