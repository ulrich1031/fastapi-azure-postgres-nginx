from fastapi import APIRouter
from app.utils.logging import AppLogger
from .handlers import QAWebSocketHandler


logger = AppLogger().get_logger()

websockets_router = APIRouter(prefix="/chat")


qa_handler = QAWebSocketHandler()
websockets_router.websocket("/{chat_type}/{session_id}")(qa_handler)