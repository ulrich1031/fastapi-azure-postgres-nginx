from typing import Optional, List
from sqlmodel import select
from sqlalchemy.exc import NoResultFound
from .model import MessageModel
from app.enums.message_enum import MessageRoleEnum
from app.database.base.service import BaseService
from app.utils.logging import AppLogger


logger = AppLogger().get_logger()


class MessageService(BaseService):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def add_message(self, message: MessageModel) -> Optional[MessageModel]:
        """
        Add message to database
        
        Parameters:
        
            message (MessageModel): message to add
        
        Returns:

            Optional[MessageModel]: updated message model
        """
        await message.save(db_session=self.db_session)
        
        return message
        
    async def find_by_session_id(self, session_id: str) -> List[MessageModel]:
        """
        Retrieve all messages by session id.

        Parameters:

            session_id (str): session_id to retreive

        Returns:

            List[MessageModel]: List of messages.
        """

        statement = select(MessageModel).where(MessageModel.session_id == session_id).order_by(MessageModel.created_at.asc())
    
        try:
            result = await self.db_session.exec(statement)
            return result.all()
        except NoResultFound:
            return []