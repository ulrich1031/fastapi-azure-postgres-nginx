from typing import Optional
from sqlalchemy.exc import NoResultFound
from sqlmodel import select
from .model import TenantModel
from app.database.base.service import BaseService


class TenantService(BaseService):
    """
    Tenant Service
    """

    async def find_by_uuid(self, uuid: str) -> Optional[TenantModel]:
        """
        Retrieve tenant by UUID

        Parameters:

            uuid (str): uuid of the tenant to retreive

        Returns:

            Optional[TenantModel]: Tenant modle object if found, otherwise None.
        """

        statement = select(TenantModel).where(TenantModel.uuid == uuid)

        try:
            result = await self.db_session.exec(statement)
            return result.one()
        except NoResultFound:
            return None
