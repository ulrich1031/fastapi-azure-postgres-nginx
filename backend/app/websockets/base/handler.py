from fastapi import WebSocket, WebSocketDisconnect  
from typing import Type  
from pydantic import BaseModel  
from app.utils.logging import AppLogger 
from app.utils.connection_manager import ConnectionManager
from .schema import WSErrorResponse
from .enum import WSResponseTypeEnum


logger = AppLogger().get_logger()  

class BaseWebSocketHandler:  
    def __init__(self, model: Type[BaseModel], **kwargs):  
        self.manager = ConnectionManager()  
        self.model = model  
        self.connected = False  

    async def connect(self, websocket: WebSocket):  
        await self.manager.connect(websocket)  
        self.connected = True  
    
    async def disconnect(self, websocket: WebSocket):  
        if self.connected:  
            await self.manager.disconnect(websocket)  
            self.connected = False  

    async def send_model(self, message: BaseModel, websocket: WebSocket):  
        try:  
            if self.connected:  
                await websocket.send_json(message.model_dump())  
            else:  
                logger.warning("Attempted to send a message on a closed WebSocket connection.")  
        except WebSocketDisconnect:  
            logger.warning("WebSocket is disconnected, failed to send message.")  
            self.connected = False  

    async def handle_message(self, message, websocket: WebSocket):  
        raise NotImplementedError("Must override handle_message in subclass")  

    async def handle_call(self, websocket: WebSocket, **kwargs):  
        """  
        A method to handle the specific logic for different WebSocket endpoints.  
        To be overridden by subclasses if needed.  
        """  
        await self.connect(websocket)  
        try:  
            while self.connected:  
                data = await websocket.receive_json()  
                obj = self.model(**data)  
                await self.handle_message(message=obj, websocket=websocket, **kwargs)  
        except WebSocketDisconnect as e:  
            logger.info(f"WebSocket disconnected with code: {e.code}")  
        except Exception as e:  
            try:  
                if self.connected:  
                    await websocket.send_json({  
                        "type": WSResponseTypeEnum.ERROR.value,  
                        "data": WSErrorResponse(content=str(e)).model_dump()  
                    })  
            except WebSocketDisconnect:  
                logger.warning("WebSocket is disconnected, failed to send error message.")  
            except Exception as e:
                logger.error(f"Error occurred: {e}")
                self.disconnect(websocket)
                

    async def __call__(self, websocket: WebSocket, **kwargs):  
        """  
        Default implementation of handling the call. Subclasses can override this  
        method to provide custom parameter handling logic.  
        """  
        await self.handle_call(websocket, **kwargs)    