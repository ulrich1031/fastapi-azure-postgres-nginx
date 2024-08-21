from typing import Dict, Optional
from fastapi import WebSocket, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.enums import AgentStreamingEventTypeEnum
from app.ai.schemas import AgentStreamingEvent
from app.database.main import TenantService
from app.database.config import get_main_db_session, get_agent_db_session
from app.services import ChatService
from app.enums import ChatTypeEnum
from app.utils.logging import AppLogger
from app.websockets.base import BaseWebSocketHandler
from ..schema import QARequestSchema, QAMessageSchema, QAResponseSchema, WSErrorResponse, QAMessageEndResponse, QAMessageStreamResponse
from ..enum import QARequestTypeEnum, QAResponseTypeEnum

logger = AppLogger().get_logger()

class QAWebSocketHandler(BaseWebSocketHandler):
    
    def __init__(self):
        super().__init__(QARequestSchema)
        self.config = {}
        
    async def handle_message_event(self, chat_type: str, session_id: str, data: QAMessageSchema, config: Optional[Dict], websocket: WebSocket):
        tenant_service = TenantService(db_session=self.main_db_session)

        tenant_model = await tenant_service.find_by_uuid(data.tenant_id)
        
        logger.info("Get tenant")
        
        if not tenant_model:
            self.send_model(
                message=QAResponseSchema(
                    type=QAResponseTypeEnum.ERROR,
                    data=WSErrorResponse(content="Tenant with {data.tenant_id} not found")
                ),
                websocket=websocket
            )

        chat_service = ChatService(
            tenant=tenant_model,
            session_id=session_id,
            type=chat_type,
            db_session=self.agent_db_session,
            config=config,
            langfuse_trace_args={
                "name": "chat",
                "metadata": {
                    "chat_type": chat_type,
                    "tenantID": data.tenant_id,
                    "sessionID": session_id
                }
            }
        )
        
        async for chunk in chat_service.qa_chat_streaming(content=data.content, files=data.files):
            
            if chunk.type == AgentStreamingEventTypeEnum.MESSAGE:
                await self.send_model(
                    message=QAResponseSchema(
                        type=QAResponseTypeEnum.MESSAGE_STREAM,
                        data=QAMessageStreamResponse(content=chunk.content)
                    ),
                    websocket=websocket
                )
            
            elif chunk.type == AgentStreamingEventTypeEnum.CAHIN_END:
                await self.send_model(
                    message=QAResponseSchema(
                        type=QAResponseTypeEnum.MESSAGE_END,
                        data=QAMessageEndResponse(
                            content=chunk.output
                        )
                    ),
                    websocket=websocket
                )
    
    async def handle_message(self, message: QARequestSchema, websocket: WebSocket, session_id: str, chat_type: str):  
        if message.type == QARequestTypeEnum.MESSAGE:
            await self.handle_message_event(
                chat_type=chat_type,
                session_id=session_id,
                data=message.data,
                config=message.config,
                websocket=websocket
            )
        else:
            self.send_model(
                message=QAResponseSchema(
                    type=QAResponseTypeEnum.ERROR,
                    data=WSErrorResponse(content="Invalid message type.")
                )
            )
            
    async def __call__(
        self,
        chat_type: str,
        session_id: str,
        websocket: WebSocket,
        main_db_session: AsyncSession = Depends(get_main_db_session),
        agent_db_session: AsyncSession = Depends(get_agent_db_session)
    ):
        """
        session_id (str): session id of the chat 
        """
        self.main_db_session = main_db_session
        self.agent_db_session = agent_db_session
        await self.handle_call(websocket, chat_type=chat_type, session_id=session_id)