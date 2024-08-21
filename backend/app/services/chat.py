import os
from uuid import UUID
from typing import AsyncGenerator, List, Optional, Dict
from fastapi import UploadFile
from langchain_core.messages import SystemMessage
from app.ai.agents import QAAgent
from app.ai.enums import AgentStreamingEventTypeEnum, ToolNameEnum
from app.ai.schemas import AgentStreamingEvent, QAAgentStreamingEvent
from app.ai.prompts import QAPrompts
from app.database.main import TenantModel
from app.database.agent import MessageModel, MessageService, ChunkModel, ChunkService, ReportService
from app.enums import ChunkTypeEnum, ChatTypeEnum
from app.utils.logging import AppLogger, ElapsedTimeLogger
from app.utils.string import StringUtil
from app.utils.file import FileUtil
from app.utils.vector_retriever import FaissVectorRetriever
from app.enums.message_enum import MessageRoleEnum, MessageTypeEnum
from .base import BaseService

logger = AppLogger().get_logger()

class ChatService(BaseService):
    """
    Service for handling chat.
    """
    def __init__(self, tenant: Optional[TenantModel], session_id: str, type: str, config: Dict = {}, **kwargs):
        """
        Initiate Chat Service.
        
        Parameters:
        
            tenant (TenantModel): tenant model that will be used in chat.
            
            type (str): type of the chat
            
            config (Dict): config
        """
        super().__init__(**kwargs)
        
        self.tenant = tenant

        self.message_service = MessageService(db_session=self.db_session)
        self.chunk_service = ChunkService(db_session=self.db_session)
        self.session_id = session_id
        self.type = type
        
        index_path = "./static/faiss-indexes" + self.__get_index_path__(session_id=session_id, type=type)
        # if os.path.exists(index_path):
        self.faiss_vector_retriever = FaissVectorRetriever(
            file_path=self.__get_index_path__(session_id=session_id, type=type)
        )
        # else:
        #     self.faiss_vector_retriever = None
        self.config = config
        
        if tenant:
            self.qa_agent = QAAgent(
                faiss_vector_store=self.faiss_vector_retriever if os.path.exists(index_path) else None,
                tenant=self.tenant,
                db_session=self.db_session,
                langfuse_trace=self.langfuse_trace
            )
            # self.qa_agent.system_prompt = self.__get_agent_system_prompt__(type)

    async def __get_agent_system_prompt__(self):
        if self.type == ChatTypeEnum.QA.value:
            return SystemMessage(
                content=QAPrompts.qa_system_prompt(
                    organization_name=self.tenant.name,
                    organization_information=self.tenant.org_info
                )
            )
        elif self.type == ChatTypeEnum.REPORT.value:
            report_service = ReportService(db_session=self.db_session)
            if self.config:
                report = await report_service.fetch_from_api_by_id(self.config.get("report_id", ""))
            else:
                report = ""
            return SystemMessage(
                content=QAPrompts.report_chat_system_prompt(
                    organization_name=self.tenant.name,
                    organization_information=self.tenant.org_info,
                    # report_target_audience=report.report_target_audience,
                    # report_objective=report.report_objective,
                    # report_additional_information=report.report_additional_information,
                    report=report
                )
            )
        else:
            return ""
            
    def __get_index_path__(self, session_id: str,  type: str):
    
        return f"/chat/{type}/{session_id}/"
    
    def __get_file_path__(self, session_id: str, type: str):
        return f"/chat/{type}/{session_id}/"
    
    async def __embed_uploaded_file__(self, file: UploadFile, type: ChatTypeEnum):
        """
        Embed a uploaded file.
        
        Parameters:
            file (UploadFile): uploaded file
        """
        file_util = FileUtil()
        logger.info(type)
        path = await file_util.save_uploaded_file(file=file, file_path=self.__get_file_path__(self.session_id, self.type))
        documents = await file_util.load_file_as_documents(file_path=path)
        ids = await self.faiss_vector_retriever.add_documents(documents=documents, save_local=False)
    
    async def embed_uploaded_files(self, files: List[UploadFile] = []):
        """
        Embed uploaded files.
        
        Parameters:
            files (List[UploadFile]): uploaded files
        """
        with ElapsedTimeLogger(f"Embedding custom files"):
            for file in files:
                await self.__embed_uploaded_file__(file, type=self.type)
                
            self.faiss_vector_retriever.db.save_local(self.faiss_vector_retriever.file_path)
    
    async def qa_chat_streaming(self, content: str, files: List[str]) -> AsyncGenerator[QAAgentStreamingEvent, None]:
        """
        Invoke QA Chat with QAAgent.
        
        Parameters:
            content (str): content of the chat.
            
            files (List[str]): files attached to this chat.
        """
        # urls = StringUtil.extract_urls(text=content)
        await self.message_service.add_message(
            message=MessageModel(
                role=MessageRoleEnum.USER.value,
                type=MessageTypeEnum.QUESTION.value,
                session_id=self.session_id,
                files=files,
                content=content
            )
        )
        
        self.qa_agent.system_prompt = await self.__get_agent_system_prompt__()
        
        web_chunks = []
        internal_chunks = []
        file_chunks = []
        url_chunks = []
        
        async for chunk in self.qa_agent.astreaming(self.session_id):
            if chunk.type.value == AgentStreamingEventTypeEnum.CAHIN_END.value:
                await self.message_service.add_message(
                    message=MessageModel(
                        role=MessageRoleEnum.ASSISTANT.value,
                        type=MessageTypeEnum.QUESTION.value,
                        session_id=self.session_id,
                        content=chunk.output
                    )
                )
                chunk_ids = StringUtil.extract_chunks_and_content(
                    content=chunk.output
                )
                
                logger.info(chunk_ids)
                for chunk_id in chunk_ids['citations']:
                    found = False
                    for obj in web_chunks:
                        if obj['uuid'] == chunk_id:
                            chunk_model = ChunkModel(
                                uuid=UUID(obj['uuid']),
                                type=ChunkTypeEnum.WEB.value,
                                session_id=self.session_id,
                                query=obj['query'],
                                source=obj['url'],
                                content=obj['content'],
                                captions_text=obj['content'],
                                captions_highlights=obj['content']
                            )
                            await self.chunk_service.add_chunk(chunk_model)
                            found = True
                            break
                    
                    if found == True:
                        continue
                    
                    for obj in internal_chunks:
                        if obj['uuid'] == chunk_id:
                            chunk_model = ChunkModel(
                                uuid=UUID(obj['uuid']),
                                type=ChunkTypeEnum.INTERNAL.value,
                                session_id=self.session_id,
                                query=obj['query'],
                                vector_similarity_score=obj['score'],
                                source=obj['source'],
                                content=obj['content'],
                                captions_text=obj['highlights'],
                                captions_highlights=obj['highlights']
                            )
                            await self.chunk_service.add_chunk(chunk_model)
                            found = True
                            break
                        
                    if found == True:
                        continue
                    
                    for obj in file_chunks:
                        if obj['uuid'] == chunk_id:
                            chunk_model = ChunkModel(
                                uuid=UUID(obj['uuid']),
                                type=ChunkTypeEnum.FILE.value,
                                session_id=self.session_id,
                                query=obj['query'],
                                source=obj['metadata']['source'],
                                content=obj['page_content'],
                                captions_text=obj['page_content'],
                                captions_highlights=obj['page_content']
                            )
                            await self.chunk_service.add_chunk(chunk_model)
                            found = True
                            break
                        
                    if found == True:
                        continue
                    
                    for obj in url_chunks:
                        if obj['uuid'] == chunk_id:
                            chunk_model = ChunkModel(
                                uuid=UUID(obj['uuid']),
                                type=ChunkTypeEnum.URL.value,
                                session_id=self.session_id,
                                query=obj['query'],
                                source=obj['url'],
                                content=obj['highlight'],
                                captions_text=obj['highlight'],
                                captions_highlights=obj['highlight']
                            )
                            await self.chunk_service.add_chunk(chunk_model)
                            found = True
                            break
                        
                chunk = QAAgentStreamingEvent(
                    **chunk.model_dump()
                )
                
            if chunk.type.value == AgentStreamingEventTypeEnum.TOOL_END.value:
                if chunk.name == ToolNameEnum.TAVILY_SEARCH.value:
                    web_chunks.extend(chunk.output)
                if chunk.name == ToolNameEnum.AZUREAI_SEARCH.value:
                    internal_chunks.extend(chunk.output)
                if chunk.name == ToolNameEnum.FAISS_SEARCH.value:
                    file_chunks.extend(chunk.output)
                if chunk.name == ToolNameEnum.EXA_SEARCH.value:
                    logger.info(url_chunks)
                    url_chunks.extend(chunk.output)
            
            yield chunk