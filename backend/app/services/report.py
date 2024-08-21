import json
import asyncio
import logging
from typing import Optional, List, Dict
from fastapi import UploadFile
from app.database.main import TenantModel
from app.database.agent import ChunkService, ChunkModel, ReportModel, MessageModel, ReportService, MessageService
from app.utils.vector_retriever.azureaisearch import AzureAISearchVectorRetriever, AzureAISearchResponse
from app.utils.logging import AppLogger, ElapsedTimeLogger
from app.utils.string import StringUtil
from app.utils.file import FileUtil
from app.utils.tavily_client import TavilyClient, TavilySearchContextResponse
from app.utils.vector_retriever import FaissVectorRetriever, Document
from app.utils.exa_client import ExaClient, ExaGetContentResponse
from app.routers.report.schema import ChunkResponseModel, OutlineModel, ResearchResponseModel, InitiateResearchResponseModel 
from app.enums.chunk_enum import ChunkTypeEnum
from app.enums.message_enum import MessageRoleEnum, MessageTypeEnum
from app.ai.prompts import ReportPrompts
from app.config import get_settings
from .base import BaseService

logger = AppLogger().get_logger()

class ReportFlowService(BaseService):
    """
    Service for report generation flow logics.
    """
    def __init__(self, tenant: TenantModel, report: Optional[ReportModel] = None, **kwargs):
        """
        Initiate Report Flow Service.
        
        Parameters:
        
            tenant (TenantModel): tenant model that will be used for report flow.
            
            report_id (UUID): report id.
            
        """
        super().__init__(**kwargs)
        
        self.settings = get_settings()
        self.chunk_service = ChunkService(**kwargs)
        self.report_service = ReportService(**kwargs)
        self.message_service = MessageService(**kwargs)
        self.report = report
        self.tenant = tenant
        self.tavily_client = TavilyClient(langfuse_trace=self.langfuse_trace)
        self.exa_client = ExaClient(langfuse_trace=self.langfuse_trace)
        self.faiss_vector_retriever = None
        self.chunks = []
        if report:
            self.faiss_vector_retriever = FaissVectorRetriever(
                file_path=str(self.report.uuid),
                langfuse_trace=self.langfuse_trace
            )
    
    async def __get_web_search_queries__(self, count: int = 5, **kwargs):
        """
        Get internal search queries from user report generation params.
        
        Parameters:
            count (int): 5
        """
        result = await self.azure_openai_client.ainvoke(
            model=self.settings.FAST_LLM_MODEL,
            name="generate-web-search-queries",
            timeout=45,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content":  ReportPrompts.get_web_search_queries(count=count, **kwargs)
                }
            ]
        )
        result = json.loads(result)
        logger.info(f"Get web search queries: {json.dumps(result['queries'])}")
        return result["queries"]
    
    async def __get_web_search_queries_for_section__(self, count: int = 5, section: dict = {}, **kwargs):
        """
        Get internal search queries from user report generation params.
        
        Parameters:
            count (int): 5
        """
        result = await self.azure_openai_client.ainvoke(
            model=self.settings.FAST_LLM_MODEL,
            name="generate-web-search-queries",
            timeout=45,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content":  ReportPrompts.get_web_search_queries_for_section(count=count, section_title=section["title"], section_description=section["description"], **kwargs)
                }
            ]
        )
        result = json.loads(result)
        logger.info(f"Get web search queries for section: {json.dumps(result['queries'])}")
        return result["queries"]

    async def __get_rag_search_queries__(self, count: int = 5, **kwargs):
        """
        Get raq search queries from user report generation params.
        
        Parameters:
            count (int): 5
        """
        result = await self.azure_openai_client.ainvoke(
            model=self.settings.FAST_LLM_MODEL,
            name="generate-rag-search-queries",
            timeout=45,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content":  ReportPrompts.get_rag_queries(count=count, **kwargs)
                }
            ]
        )
        result = json.loads(result)
        logger.info(f"Get rag search queries: {json.dumps(result['queries'])}")
        return result["queries"]

    async def __get_section_rag_search_queries__(self, count: int = 3, **kwargs):
        """
        Get section raq search queries from user report generation params.
        
        Parameters:
            count (int): 3
        """
        result = await self.azure_openai_client.ainvoke(
            model=self.settings.FAST_LLM_MODEL,
            name="generate-section-rag-search-queries",
            timeout=45,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content":  ReportPrompts.get_section_rag_queries(count=count, **kwargs)
                }
            ]
        )
        result = json.loads(result)
        return result["queries"]

    async def __run_web_search_query__(self, query: str, top: int = 5) -> List[TavilySearchContextResponse]:
        with ElapsedTimeLogger(f"Running web search query: {query}"):
            results = await self.tavily_client.get_search_context(query=query, search_depth='advanced', max_results=top)
            return results
    
    async def __run_rag_query__(self, query: str, service_name: str, index_name: str, top: int = 5) -> List[AzureAISearchResponse]:
        """
        Get the relevant results
        """
        with ElapsedTimeLogger(f"Running rag query: {query}"):
            try:
                retreiver = AzureAISearchVectorRetriever(
                    service_name=service_name,
                    index_name=index_name,
                    langfuse_trace=self.langfuse_trace                    
                )
                results = await retreiver.run(query=query, top=top)
                return results
            except Exception as e:
                logger.error(f"error in run_rag_query: {e}")
                return []
    
    async def __run_url_search_query__(self, query: str, urls: List[str], top: int = 5) -> List[ExaGetContentResponse]:
        
        with ElapsedTimeLogger(f"Url search query: {query} on {urls}"):
            results = await self.exa_client.get_contents(
                ids=urls,
                highlights={
                    "query": query,
                    "highlightsPerUrl": top, 
                    "numSentences": 3
                }
            )
            return results
    
    async def __run_custom_file_query__(self, query: str, top: int = 5) -> List[Document]:
        """
        Get the relevant results from custom files
        """
        with ElapsedTimeLogger(f"Running custom file query: {query}"):
            try:
                # if self.faiss_vector_retriever.db:
                results = await self.faiss_vector_retriever.asimilarity_search(query=query, k=top)
                return results
            except Exception as e:
                logger.error(f"error in custom_file_query: {e}")
                return []
    
    async def __check_relevance__(self, chunk: str, **kwargs) -> bool:
        result = await self.azure_openai_client.ainvoke(
            model=self.settings.FAST_LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content":  ReportPrompts.check_chunk_relevance(chunk_content=chunk, **kwargs)
                }
            ]
        )
        if result == "True":
            return True
        return False
    
    async def __score_chunks_by_llm__(self, chunks: List[ChunkModel], start_index: int = 0, **kwargs) -> List[Dict]:
        """
        Score chunks relevance score with LLM.
        
        Parameters:
            
            chunks (ChunkModel): list of chunks to sort.
            
            start_index (int): start index.
            
        Return:
        
            List[Dict]: chunks with score.
            
        Example:

            [
                {{
                    'id': 1,
                    'score': 97
                }},
                {{
                    'id': 2,
                    'score': 90
                }},
                {{
                    'id': 3,
                    'score': 80
                }},
                {{
                    'id': 4,
                    'score': 76
                }}    
            ]
        """
        result = await self.azure_openai_client.ainvoke(
            model=self.settings.FAST_LLM_MODEL,
            name="score-chunks",
            timeout=45,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": ReportPrompts.order_chunks(
                        chunks=json.dumps([
                            {  
                                "id": start_index + index + 1,
                                "content": chunk.content
                            }
                            for index, chunk in enumerate(chunks)
                        ]),
                        **kwargs
                    )
                }
            ]
        )
        return json.loads(result)["chunks"]
    
    async def __score_section_chunks_by_llm__(self, chunks: List[ChunkModel], start_index: int = 0, **kwargs) -> List[Dict]:
        """
        Score section chunks relevance score with LLM.
        
        Parameters:
            
            chunks (ChunkModel): list of chunks to sort.
            
            start_index (int): start index.
            
        Return:
        
            List[Dict]: chunks with score.
            
        Example:

            [
                {{
                    "id": 1,
                    "report_relevance_score": 96
                    "section_relevance_score": 97
                }},
                {{
                    "id": 2,
                    "report_relevance_score": 90
                    "section_relevance_score": 89
                }},
                {{
                    "id": 3,
                    "report_relevance_score": 85
                    "section_relevance_score": 80
                }},
                {{
                    "id": 4,
                    "report_relevance_score": 70
                    "section_relevance_score": 76
                }}
            ]
        """
        result = await self.azure_openai_client.ainvoke(
            model=self.settings.FAST_LLM_MODEL,
            name="score-section-chunks",  
            timeout=45,  
            response_format={"type": "json_object"},  
            messages=[  
                {
                    "role": "user",  
                    "content": ReportPrompts.order_section_chunks(
                        chunks=json.dumps([  
                            {  
                                "id": start_index + index + 1,  
                                "content": chunk.content  
                            }  
                            for index, chunk in enumerate(chunks)  
                        ]),  
                        **kwargs  
                    )  
                }  
            ]  
        )  
        return json.loads(result)["chunks"]  

    async def __order_chunk_by_llm__(self, chunks: List[ChunkModel], **kwargs) -> List[Dict]:
        """
        Order chunks by relevance score with LLM.
        Processing 10 chunks in one invoke, 5 invokes at once.
        
        Parameters:
            chunks (ChunkModel): list of chunks to sort.
            
        Return:
        
            List[Dict]: order of chunks
            
        Example:

            [
                {{
                    'id': 3,
                    'score': 97
                }},
                {{
                    'id': 2,
                    'score': 90
                }},
                {{
                    'id': 4,
                    'score': 80
                }},
                {{
                    'id': 1,
                    'score': 76
                }}    
            ]
        """
        chunks_in_one_invoke = 10
        batch_size = 5
        
        chunk_batches = [chunks[i:i + chunks_in_one_invoke] for i in range(0, len(chunks), chunks_in_one_invoke)]  

        results = []
        start_index = 0 
        while chunk_batches:  
            # Get the next 5 batches for parallel processing  
            current_batches = chunk_batches[:batch_size]  
            chunk_batches = chunk_batches[batch_size:]  

            # Run the 5 invokes in parallel
            if kwargs['section_title']=='':
                tasks = [self.__score_chunks_by_llm__(current_batches[i], start_index=start_index + i * 10, **kwargs) for i in range(len(current_batches))]  
            else:
                tasks = [self.__score_section_chunks_by_llm__(current_batches[i], start_index=start_index + i * 10, **kwargs) for i in range(len(current_batches))]  
            batch_results = await asyncio.gather(*tasks)  

            # Flatten the results and append to the main results list  
            for batch_result in batch_results:  
                results.extend(batch_result)

        # Sort the flattened results by score  
        if kwargs['section_title']=='':
            sorted_chunks = sorted(results, key=lambda x: x["score"], reverse=True)
        else:
            sorted_chunks = sorted(results, key=lambda x: x["section_relevance_score"], reverse=True)
        return sorted_chunks  
    
    def __remove_multiple_chunks__(self, chunks: List[ChunkModel]) -> List[ChunkModel]:
        """
        Clear multiple chunks
        """
        # Create a dict to track unique chunks  
        seen_chunks = {}  
        
        # List to store filtered chunks  
        filtered_chunks = []  
        
        for chunk in chunks:  
            key = (chunk.content, chunk.source)  
            
            if key not in seen_chunks:  
                seen_chunks[key] = True  
                filtered_chunks.append(chunk)  
        
        return filtered_chunks
    
    async def run_web_search_query(self, query: str, top: int = 5) -> List[ChunkModel]:
        """
        Run a web search query.

        Parameters:
        
            query (str): The search query to run.
            
            top (int): The number of top results to fetch. Default is 5.

        Returns:
        
            List[ChunkModel]: List of ChunkModels for the given query.
            
        """
        results = await self.__run_web_search_query__(query=query, top=top)
        chunk_list = []
        for result in results:
            chunk = ChunkModel(
                type=ChunkTypeEnum.WEB.value,
                report_id=self.report.uuid,
                query=query,
                source=result.url,
                content=result.content,
                captions_text=result.content,
                captions_highlights=result.content
            )
            chunk_list.append(chunk)
        
        return self.__remove_multiple_chunks__(chunk_list)
    
    async def run_internal_search_query(self, query: str, top: int = 5) -> List[ChunkModel]:
        """
        Run an internal search query.

        Parameters:
        
            query (str): The search query to run.
            
            top (int): The number of top results to fetch. Default is 5.

        Returns:
            List[ChunkModel]: List of ChunkModel for the given query.
        """
        index_name = self.tenant.ai_search_index_name
        service_name = self.tenant.ai_search_service_name

        results = await self.__run_rag_query__(
            query=query,
            index_name=index_name,
            service_name=service_name,
            top=top
        )
        
        chunk_list = []
        for result in results:
            chunk = ChunkModel(
                type=ChunkTypeEnum.INTERNAL.value,
                report_id=self.report.uuid,
                query=query,
                vector_similarity_score=result.score,
                source=result.source,
                content=result.content,
                captions_text=result.highlights,
                captions_highlights=result.highlights
            )
            chunk_list.append(chunk)
        
        return self.__remove_multiple_chunks__(chunk_list)
    
    async def run_custom_file_query(self, query: str, top: int = 5) -> List[ChunkModel]:
        """
        Run a custom file query.

        Parameters:
        
            query (str): The search query to run.
            
            top (int): The number of top results to fetch. Default is 5.

        Returns:
        
            List[ChunkModel]: List of ChunkModels for the given query.
            
        """
        results = await self.__run_custom_file_query__(query=query, top=top)
        chunk_list = []
        for result in results:
            chunk = ChunkModel(
                type=ChunkTypeEnum.FILE.value,
                report_id=self.report.uuid,
                query=query,
                source=result.metadata['source'],
                content=result.page_content,
                captions_text=result.page_content,
                captions_highlights=result.page_content
            )
            chunk_list.append(chunk)
            
        return self.__remove_multiple_chunks__(chunk_list)
    
    async def run_url_search_query(self, urls: List[str], query: str, top: int = 5) -> List[ChunkModel]:
        """
        Run url search query.
        
        Parameters:
        
            urls (str): URLs to search
        
            query (str): The search query to run.
            
            top (int): The number of top results to fetch. Default is 5.

        Returns:
        
            List[ChunkModel]: List of ChunkModels for the given query.
        """
        results = await self.__run_url_search_query__(query=query, urls=urls, top=top)
        chunk_list = []
        for result in results:
            chunk = ChunkModel(
                type=ChunkTypeEnum.URL.value,
                report_id=self.report.uuid,
                query=query,
                source=result.url,
                content=result.highlight,
                captions_text=result.highlight,
                captions_highlights=result.highlight
            )
            chunk_list.append(chunk)
        
        return self.__remove_multiple_chunks__(chunk_list)
    
    async def get_top_chunks_order_by_llm_relevance(self, chunks: List[ChunkModel], top: int = 10, section_info: dict = None) -> List[ChunkModel]:
        """
        Order chunks by LLM, calculate relevance score, and return only top chunks.
        
        Parameters:

            chunks (List[ChunkModel]): chunks to sort
            
            top (int): number of chunks to return

            section_info (dict): section information for score chunk
        """
        filtered_chunks = self.__remove_multiple_chunks__(chunks)
        
        chunk_orders = await self.__order_chunk_by_llm__(
            filtered_chunks,
            organization_name=self.tenant.name,
            organization_information=self.tenant.org_info,
            report_additional_information=self.report.report_additional_information,
            report_objective=self.report.report_objective,
            report_target_audience=self.report.report_target_audience,
            section_title=section_info['title'] if section_info else "",
            section_description=section_info['description'] if section_info else ""
        )
        
        final_chunks = []
        
        for chunk_order in chunk_orders[:top]:
            if section_info and section_info['title']!='':
                filtered_chunks[chunk_order['id'] - 1].llm_similarity_score = chunk_order["section_relevance_score"]
            else:
                filtered_chunks[chunk_order['id'] - 1].llm_similarity_score = chunk_order["score"]
            final_chunks.append(filtered_chunks[chunk_order['id'] - 1])
        
        return final_chunks
    
    async def run_custom_query(self, query: str, type: str, top: int = 10) ->List[ChunkModel]:
        if type == ChunkTypeEnum.INTERNAL:
            chunks = await self.run_internal_search_query(query=query, top=top)
        elif type == ChunkTypeEnum.WEB:
            chunks = await self.run_web_search_query(query=query, top=top)
        elif type == ChunkTypeEnum.FILE:
            chunks = await self.run_custom_file_query(query=query, top=top)
        elif type == ChunkTypeEnum.URL:
            urls = StringUtil.extract_urls(self.report.report_additional_information)
            chunks = await self.run_url_search_query(urls=urls, query=query, top=top)
            
        final_chunks = await self.get_top_chunks_order_by_llm_relevance(chunks=chunks, top=top)
        final_chunks = chunks
        for chunk in final_chunks:
            chunk = await self.chunk_service.add_chunk(chunk)
            
        return final_chunks
    
    async def run_web_search(self, config: dict = {}, queries: Optional[List] = None) -> List[ChunkModel]:
        """
        Run internal serach.
        
        Parameters:
            
            config (dict): config for web search.

                top_total: number of chunks to fetch totally. Default is 10.
                
                top_each_query: number of chunks to fetch for each query. Default is 10.
                
                number_of_queries: number of queries to search from a user report generation query Default is 5.

            queries (list): queries to run web search. Defaults to None. If it is None, it will create queries with llm.
            
        Returns:
        
            List[ChunkModel]: List of chunks.
        """
        final_config = {
            'top_total': 5,
            'top_each_query': 5,
            'number_of_queries': 3
        }
        final_config.update(**config)
        
        if not queries:
            queries = await self.__get_web_search_queries__(
                count=final_config['number_of_queries'],
                organization_name=self.tenant.name,
                organization_information=self.tenant.org_info,
                tenant_id=self.report.tenant_id,
                report_additional_information=self.report.report_additional_information,
                report_objective=self.report.report_objective,
                report_target_audience=self.report.report_target_audience
            )

        chunks = []
        tasks = [ self.run_web_search_query(query=query, top=final_config["top_each_query"]) for query in queries]
        
        results = await asyncio.gather(*tasks)
        
        for result in results:
            chunks.extend(result)
        
        final_chunks = await self.get_top_chunks_order_by_llm_relevance(chunks=chunks, top=final_config['top_total'])    
        # final_chunks = chunks
        
        return final_chunks

    async def run_web_search_for_section(self, section: dict = {}, config: dict = {}, queries: Optional[List] = None) -> List[ChunkModel]:
        """
        Run internal serach for section.
        
        Parameters:
            section (dict): section info dictionary

                section_title: the title of a certain section

                section_description: a short explanation about the section
        
            config (dict): config for web search.

                top_total: number of chunks to fetch totally. Default is 10.
                
                top_each_query: number of chunks to fetch for each query. Default is 10.
                
                number_of_queries: number of queries to search from a user report generation query Default is 5.

            queries (list): queries to run web search. Defaults to None. If it is None, it will create queries with llm.
            
        Returns:
        
            List[ChunkModel]: List of chunks.
        """
        final_config = {
            'top_total': 5,
            'top_each_query': 5,
            'number_of_queries': 3
        }
        final_config.update(**config)
        
        if not queries:
            queries = await self.__get_web_search_queries_for_section__(
                count=final_config['number_of_queries'],
                organization_name=self.tenant.name,
                organization_information=self.tenant.org_info,
                tenant_id=self.report.tenant_id,
                report_additional_information=self.report.report_additional_information,
                report_objective=self.report.report_objective,
                report_target_audience=self.report.report_target_audience,
                section = section
            )

        chunks = []
        tasks = [ self.run_web_search_query(query=query, top=final_config["top_each_query"]) for query in queries]
        
        results = await asyncio.gather(*tasks)
        
        for result in results:
            chunks.extend(result)
        
        final_chunks = await self.get_top_chunks_order_by_llm_relevance(chunks=chunks, top=final_config['top_total'], section_info=config['section_info'])    
        # final_chunks = chunks
        
        return final_chunks


    async def run_internal_search(self, config: dict = {}, queries: Optional[List] = None) -> List[ChunkModel]:
        """
        Run internal serach.
        
        Parameters:
            
            config (dict): config for internal search.

                top_total: number of chunks to fetch totally. Default is 10.
                
                top_each_query: number of chunks to fetch for each query. Default is 10.
                
                number_of_queries: number of queries to search from a user report generation query Default is 5.
            
            queries (list): queries to run internal search. Defaults to None. If it is None, it will create queries with llm(generate_rag_queries).
              
        Returns:
        
            List[ChunkModel]: List of chunks.
        """
        final_config = {
            'top_total': 5,
            'top_each_query': 5,
            'number_of_queries': 3
        }
        # final_config.update(**config)
        
        if not queries:
            queries = await self.__get_rag_search_queries__(
                count=final_config['number_of_queries'],
                organization_name=self.tenant.name,
                organization_information=self.tenant.org_info,
                tenant_id=self.report.tenant_id,
                report_additional_information=self.report.report_additional_information,
                report_objective=self.report.report_objective,
                report_target_audience=self.report.report_target_audience
            )
        
        # return []
        chunks = []
        tasks = [ 
            self.run_internal_search_query(
                query=query,
                top=final_config["top_each_query"]
            ) for query in queries
        ]
            
        results = await asyncio.gather(*tasks)
        for result in results:
            chunks.extend(result)
        
        final_chunks = await self.get_top_chunks_order_by_llm_relevance(chunks=chunks, top=final_config['top_total'], section_info=config['section_info'])
        # final_chunks = chunks
        
        return final_chunks
    
    async def run_custom_file_search(self, config: dict = {}, queries: Optional[List] = None) -> List[ChunkModel]:
        """
        Run custom file serach.
        
        Parameters:
            
            config (dict): config for internal search.

                top_total: number of chunks to fetch totally. Default is 10.
                
                top_each_query: number of chunks to fetch for each query. Default is 10.
                
                number_of_queries: number of queries to search from a user report generation query Default is 5.

            queries (list): queries to run custom file search. Defaults to None. If it is None, it will create queries with llm(generate_rag_search_queries).
            
        Returns:
        
            List[ChunkModel]: List of chunks.
        """
        final_config = {
            'top_total': 5,
            'top_each_query': 5,
            'number_of_queries': 3
        }
        final_config.update(**config)
        
        if not queries:
            queries = await self.__get_rag_search_queries__(
                count=final_config['number_of_queries'],
                organization_name=self.tenant.name,
                organization_information=self.tenant.org_info,
                tenant_id=self.report.tenant_id,
                report_additional_information=self.report.report_additional_information,
                report_objective=self.report.report_objective,
                report_target_audience=self.report.report_target_audience
            )
        
        # return []
        chunks = []
        tasks = [ 
            self.run_custom_file_query(
                query=query,
                top=final_config["top_each_query"]
            ) for query in queries
        ]
            
        results = await asyncio.gather(*tasks)
        for result in results:
            chunks.extend(result)
        
        final_chunks = await self.get_top_chunks_order_by_llm_relevance(chunks=chunks, top=final_config['top_total'], section_info=config['section_info'])
        # final_chunks = chunks
        
        return final_chunks
    
    async def run_url_search(self, urls: List[str] = [], config: dict = {}, queries: Optional[List] = None) -> List[ChunkModel]:
        """
        Run specific urls search.
        
        Parameters:
            
            config (dict): config for internal search.

                top_total: number of chunks to fetch totally. Default is 10.
                
                top_each_query: number of chunks to fetch for each query. Default is 10.
                
                number_of_queries: number of queries to search from a user report generation query Default is 5.

            queries (list): queries to run custom file search. Defaults to None. If it is None, it will create queries with llm(generate_rag_search_queries).
            
        Returns:
        
            List[ChunkModel]: List of chunks.
        """
        final_config = {
            'top_total': 5,
            'top_each_query': 5,
            'number_of_queries': 3
        }
        final_config.update(**config)
        
        if not queries:
            queries = await self.__get_rag_search_queries__(
                count=final_config['number_of_queries'],
                organization_name=self.tenant.name,
                organization_information=self.tenant.org_info,
                tenant_id=self.report.tenant_id,
                report_additional_information=self.report.report_additional_information,
                report_objective=self.report.report_objective,
                report_target_audience=self.report.report_target_audience
            )
        
        # return []
        chunks = []
        tasks = [ 
            self.run_url_search_query(
                urls=urls,
                query=query,
                top=final_config["top_each_query"]
            ) for query in queries
        ]
            
        results = await asyncio.gather(*tasks)
        for result in results:
            chunks.extend(result)
        
        final_chunks = await self.get_top_chunks_order_by_llm_relevance(chunks=chunks, top=final_config['top_total'], section_info=config['section_info'])
        # final_chunks = chunks
        
        return final_chunks
    
    async def embed_uploaded_file(self, file: UploadFile):
        """
        Embed a uploaded file.
        
        Parameters:
            file (UploadFile): uploaded file
        """
        file_util = FileUtil()
        path = await file_util.save_uploaded_file(file=file, file_path=f"/reports/{str(self.report.uuid)}/")
        documents = await file_util.load_file_as_documents(file_path=path)
        logger.info(documents)
        ids = await self.faiss_vector_retriever.add_documents(documents=documents, save_local=False)
    
    async def embed_uploaded_files(self, files: List[UploadFile]):
        """
        Embed uploaded files.
        
        Parameters:
            files (List[UploadFile]): uploaded files
        """
        with ElapsedTimeLogger(f"Embedding custom files"):
            for file in files:
                await self.embed_uploaded_file(file)
                
            self.faiss_vector_retriever.db.save_local(self.faiss_vector_retriever.file_path)
                
    async def chat_with_report(self, session_id: str) -> str:
        """
        Chat with report.
        
        Parameters:

            session_id (str): session_id to chat.
        """
        messages = await self.message_service.find_by_session_id(session_id)
        chunks = []
        for id in self.report.report_citations:
            chunk = await self.chunk_service.find_chunk_by_id(id)
            chunks.append(
                {
                    "content": chunk.content,
                    "source": chunk.source,
                    "id": str(chunk.uuid)
                }
            )
            
        result = await self.azure_openai_client.ainvoke(
            name="chat-with-report",
            timeout=45,
            messages=[
                {
                    "role": "system",
                    "content": ReportPrompts.chat_with_report_system_prompts(
                        report_content=self.report.report_content,
                        chunks=json.dumps(chunks),
                        organization_name=self.tenant.name,
                        organization_information=self.tenant.org_info,
                        report_additional_information=self.report.report_additional_information,
                        report_objective=self.report.report_objective,
                        report_target_audience=self.report.report_target_audience
                    )
                },
            ] + [
                {
                    "role": message.role,
                    "content": message.content
                }
                for message in messages
            ]
        )
        
        await self.message_service.add_message(
            MessageModel(
                role=MessageRoleEnum.ASSISTANT.value, content=result, session_id=session_id, type=MessageTypeEnum.REPORT.value
            )
        )
        
        return result
    
    async def generate_report_from_chunks(self, chunks: List[ChunkModel], retrying = 0) -> ReportModel:
        """
        Generate report from chunks.
        It will retry up to 5 times until it returns vaild report.
        
        Parameters:
        
            chunks (List[ChunkModel]): chunks to use
            
            retrying (int): number of retried counts(not using outside)
            
        """
        try:
            logger.info("Inside generate report service")
            result = await self.azure_openai_client.ainvoke(
                name="generate-report",
                response_format={"type": "json_object"},
                temperature=0,
                timeout=45,
                messages=[
                    {
                        "role": "user",
                        "content":  ReportPrompts.generate_report_prompts(
                            chunks=[
                                {
                                    "id": str(chunk.uuid),
                                    "content": chunk.content
                                }
                                for chunk in chunks
                            ],
                            organization_name=self.tenant.name,
                            organization_information=self.tenant.org_info,
                            report_additional_information=self.report.report_additional_information,
                            report_objective=self.report.report_objective,
                            report_target_audience=self.report.report_target_audience
                        )
                    }
                ]
            )
            
            result = json.loads(result)
                 
            final_results = StringUtil.extract_chunks_and_content(result['content'])
            
            await self.report.update(
                self.db_session,
                chunk_ids=[ str(chunk.uuid) for chunk in chunks ],
                report_content=result['content'],
                report_citations=[ id for id in final_results['citations']]
            )
            return self.report
        except Exception as e:
            logger.error(f"tried {retrying + 1}, but failed: {e}")
            
            if retrying < 5:
                logger.info(f"Trying again")
                await self.generate_report_from_chunks(chunks, retrying + 1)
            else:
                return self.report
    
    async def initiate_research(self, report_conf: dict = {}, files: List[UploadFile] = [], urls: List[str] = [], config: dict = {}) -> InitiateResearchResponseModel:
        """
        Initiate internal research and web research.
        It creates a new Report.
        
        Parameters:
        
            config (dict): report generation related configuration object.

            report_conf (dict): report generation params.
            
                Examples: 
                {
                    'tenant_id': 'uuid'
                    'report_target_audience': '.....',
                    'report_objective': '.....',
                    'report_additional_information: '.....'
                }
        """
        
        self.report = await self.report_service.add_report(ReportModel(**report_conf))  
        
        # Initialize required components  
        urls = StringUtil.extract_urls(self.report.report_additional_information)  
        self.faiss_vector_retriever = FaissVectorRetriever(
            file_path=str(self.report.uuid),
            langfuse_trace=self.langfuse_trace
        )
        self.langfuse_trace.update(metadata={"reportID": str(self.report.uuid)})  
        
        # Embed uploaded files if provided  
        if files:  
            await self.embed_uploaded_files(files=files)  
        
        # generate rag-queries first because internal, file and url all use these queries
        queries = await self.__get_rag_search_queries__(
            count=config['number_of_queries'] if 'number_of_queries' in config else 3,
            organization_name=self.tenant.name,
            organization_information=self.tenant.org_info,
            tenant_id=self.report.tenant_id,
            report_additional_information=self.report.report_additional_information,
            report_objective=self.report.report_objective,
            report_target_audience=self.report.report_target_audience
        )
        
        config['section_info']={
            'title': '',
            'description': ''
        }
        # Dictionary to map task types to their corresponding methods and parameters  
        task_methods = {  
            'internal': (self.run_internal_search, {'config': config, 'queries': queries}),  
            'web': (self.run_web_search, {'config': config}),  
            'file': (self.run_custom_file_search, {'config': config, 'queries': queries}) if files else None,  
            'url': (self.run_url_search, {'urls': urls, 'config': config, 'queries': queries}) if urls else None,  
        }  
        
        # Create tasks dynamically from the available types  
        tasks = []  
        task_index_map = {}  
        current_index = 0  
        
        for key, method_params in task_methods.items():  
            if method_params:  
                method, params = method_params  
                tasks.append(method(**params))  
                task_index_map[key] = current_index  
                current_index += 1  
        
        logger.info("Running tasks")  
        results = await asyncio.gather(*tasks)  
        
        # Save the chunks from results  
        for result_set in results:  
            for chunk in result_set:  
                await self.chunk_service.add_chunk(chunk)  
        
        # Build the response  
        response_chunks = ResearchResponseModel(  
            internal=[ChunkResponseModel(**result.model_dump()) for result in results[task_index_map['internal']]],  
            web=[ChunkResponseModel(**result.model_dump()) for result in results[task_index_map['web']]]  
        )  
        
        if 'file' in task_index_map:  
            response_chunks.file = [ChunkResponseModel(**result.model_dump()) for result in results[task_index_map['file']]]  
        if 'url' in task_index_map:  
            response_chunks.url = [ChunkResponseModel(**result.model_dump()) for result in results[task_index_map['url']]]  
        
        response = InitiateResearchResponseModel(  
            research_chunks=response_chunks,  
            report_id=self.report.uuid  
        )  

        return response  
    
    
    async def generate_template(self, section_count: int = 4, **kwargs) -> List:
        """
        Get internal search queries from user report generation params.
        
        Parameters:
            section_count (int): number of sections to generate. default to 4.

        Returns:
            sections (List): array of sections generated by openai
        """
        
        result = await self.azure_openai_client.ainvoke(
            model=self.settings.FAST_LLM_MODEL,
            name="generate-template-queries",
            timeout=45,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content":  ReportPrompts.get_template_queries(count=section_count, **kwargs)
                }
            ]
        )
        result = json.loads(result)
        for section in result['outlines']:
            section['research'] = True
        return result['outlines']
    
    async def generate_section_chunks(self, section: dict) -> List[ChunkModel]:
        """
        Generate a section chunks based on report information and rag queries

        Parameters:
            section (dict): a dictionary value of section information such as title and description
            {
                "title": "Green Foundation",
                "description": "focusing on their funding of cultural exchange events."
            }

            files (List[UploadFile]): a list of custom uploaded files

        Returns:
            chunks (List): result chunk list
        """
        config = {
            'top_total': 5,
            'top_each_query': 5,
            'number_of_queries': 3,
            'section_info': {
                'title': section['title'],
                'description': section['description']
            }
        }
        queries = await self.__get_section_rag_search_queries__(
            count=config['number_of_queries'],
            organization_name=self.tenant.name,
            organization_information=self.tenant.org_info,
            tenant_id=self.report.tenant_id,
            report_additional_information=self.report.report_additional_information,
            report_objective=self.report.report_objective,
            report_target_audience=self.report.report_target_audience,
            section_title=section['title'],
            section_description=section['description']
        )

        # Initialize required components  
        urls = StringUtil.extract_urls(self.report.report_additional_information)
        task_methods = {
            'internal': (self.run_internal_search, {'config': config, 'queries': queries}),  
            'web': (self.run_web_search_for_section, {'config': config, 'section':section}),  
            'file': (self.run_custom_file_search, {'config': config, 'queries': queries}) if self.files else None,  
            'url': (self.run_url_search, {'urls': urls, 'config': config, 'queries': queries}) if urls else None,  
        }
        # Create tasks dynamically from the available types  
        tasks = []  
        task_index_map = {}  
        current_index = 0  
        
        for key, method_params in task_methods.items():
            if method_params:
                method, params = method_params
                tasks.append(method(**params))
                task_index_map[key] = current_index
                current_index += 1
        results = await asyncio.gather(*tasks)

        # Save the chunks from results
        chunks=[]
        for result_set in results:  
            for chunk in result_set:
                chunks.append(chunk)
        self.chunks.extend(chunks)
        chunks = sorted(chunks, key=lambda x: x.llm_similarity_score, reverse=True)
        return chunks[:config['top_total']]
    
    async def generate_section(self, section:dict) -> str:
        section_content = ""
        if section['research'] == True:
            chunks = await self.generate_section_chunks(section)
            section_content = await self.azure_openai_client.ainvoke(
                model=self.settings.FAST_LLM_MODEL,
                name="generate-section-content",
                temperature=0,
                timeout=45,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "user",
                        "content":  ReportPrompts.generate_section_content_prompts(
                            chunks=[
                                {
                                    "id": str(chunk.uuid),
                                    "content": chunk.content
                                }
                                for chunk in chunks
                            ],
                            organization_name=self.tenant.name,
                            organization_information=self.tenant.org_info,
                            report_additional_information=self.report.report_additional_information,
                            report_objective=self.report.report_objective,
                            report_target_audience=self.report.report_target_audience,
                            section_title=section["title"],
                            section_description=section["description"]
                        )
                    }
                ]
            )
        return section_content

    async def generate_report_v2(self, report_conf : dict, files: List[UploadFile]):
        """
        Generate a report by configuring template and sections

        Parameters:

            report_conf (dict): configuration parameters of the report
                
                {
                    'tenant_id': 9939239,
                    'report_target_audience': "",
                    'report_additional_information': "report_additional_information",
                    'report_objective': "report_objective",
                    'outline': [
                        {
                            "title": "Section 1 Title",
                            "description": "Section 1 Description",
                            "research": true
                        },
                        {
                            "title": "Section 2 Title",
                            "description": "Section 2 Description",
                            "research": true
                        },
                        {
                            "title": "Section 3 Title",
                            "description": "Section 3 Description",
                            "research": false
                        }
                    ]
                }

            files (List[UploadFile]): Uploaded files from interface

        Returns:
            report (str): final report plain text
        """
        self.files = files
        if not report_conf['outline']:
            outline = await self.generate_template(**report_conf)
        else:
            outline = json.loads(report_conf['outline'])
        
        template = {
            "objective": report_conf["report_objective"],
            "audience": report_conf["report_target_audience"],
            "info": report_conf["report_additional_information"],
            "outline": outline
        }
        
        self.report = await self.report_service.add_report(ReportModel(**report_conf))
        
        # Embed uploaded files if provided
        if files:
            await self.embed_uploaded_files(files=files)

        tasks = [
            self.generate_section(section) for section in template['outline']
        ]
        sections = await asyncio.gather(*tasks)

        for chunk in self.chunks:
            chunk = await self.chunk_service.add_chunk(chunk)

        for index, section in enumerate(sections):
            template['outline'][index]['content'] = "" if section == "" else json.loads(section)['content']
        
        if not report_conf['outline']:
            template['outline'].insert(0, {"title": "Introduction", "description":"", "content":"", "research":False})
            template['outline'].append({"title": "Conclusion", "description":"", "content":"", "research":False})

        return await self.azure_openai_client.ainvoke(
            name="review-sections",
            model=self.settings.FAST_LLM_MODEL,
            temperature=0,
            timeout=45,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content":  ReportPrompts.review_sections(
                        organization_name=self.tenant.name,
                        organization_information=self.tenant.org_info,
                        report_additional_information=self.report.report_additional_information,
                        report_objective=self.report.report_objective,
                        report_target_audience=self.report.report_target_audience,
                        template = template['outline']
                    )
                }
            ]
        )

        # for section in template['outline']:
        # section = template["outline"][0]
            # section_content = await self.generate_section(section, files)
            # section['content'] = await self.generate_section(section, files)
        
        # return section_contents