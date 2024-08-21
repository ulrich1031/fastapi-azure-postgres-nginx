import os
import shutil
import aiohttp
import requests
import json
from uuid import UUID
from typing import Optional, List
from sqlalchemy.exc import NoResultFound
from sqlmodel import select

from app.utils.authentication import AuthenticationUtil
from .model import ReportModel
from app.database.base.service import BaseService
from app.utils.logging import AppLogger
from app.config import get_settings


logger = AppLogger().get_logger()


class ReportService(BaseService):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = get_settings()
        self.authUtil = AuthenticationUtil()
    
    async def add_report(self, report: ReportModel):
        """
        Add report to database

        Parameters:

            report (ReportModel): report to add

        Returns:

            ReportModel: updated report model
        """
        await report.save(db_session=self.db_session)
        return report
    
    async def find_by_id(self, id: UUID) -> Optional[ReportModel]:
        """
        Retrieve a report by its UUID.

        Parameters:
            id (UUID): The UUID of the report to retrieve.

        Returns:
            Optional[ReportModel]: The ReportModel object if found, otherwise None.
        """
        statement = select(ReportModel).where(ReportModel.uuid == id)

        try:
            result = await self.db_session.exec(statement)
            return result.one()
        except NoResultFound:
            return None
    
    async def fetch_from_api_by_id(self, id: UUID) -> Optional[str]:
        """
        Retrieve a report by its UUID from api server.

        Parameters:
            id (UUID): The UUID of the report to retrieve.

        Returns:
            str: HTML content of the report
        """

        payload = {  
            'report_id': str(id)  
        }  
        token = self.authUtil.jwt_encode(payload=payload)  
        url = f"{self.settings.DJANGO_SERVER}/api/core/fetch-report-as-html/?report_id={str(id)}&token={token}"  

        async with aiohttp.ClientSession() as session:  
            try:  
                async with session.get(url) as response:  
                    return await response.text()  
            except:  
                return None
        
    async def find_all(self, skip: int = 0, limit: int = 10) -> List[ReportModel]:
        """
        Retrieve all reports with pagination.

        Parameters:
            skip (int): The number of records to skip.
            limit (int): The maximum number of records to return.

        Returns:
            List[ReportModel]: A list of ReportModel objects.
        """
        statement = select(ReportModel).offset(skip).limit(limit)
        result = await self.db_session.exec(statement)
        return result.all()
    
    async def delete_report(self, report: ReportModel):
        """
        Delete report.
        """
        
        # remove faiss vector index
        path = f"./static/faiss-indexes/{str(report.uuid)}"
        if os.path.exists(path):  
            shutil.rmtree(path)
            
        # remove report related files
        path = f"./static/files/reports/{str(report.uuid)}"
        if os.path.exists(path):  
            shutil.rmtree(path)
        
        await report.delete(self.db_session)
        