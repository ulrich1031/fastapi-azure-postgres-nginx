from typing import Optional
from fastapi import Depends, HTTPException  
from uuid import UUID
from app.database.config import get_agent_db_session
from app.database.agent import ReportService, ReportModel

async def get_report_by_id(report_id: UUID, agent_db_session=Depends(get_agent_db_session)) -> Optional[ReportModel]:  
    report_service = ReportService(db_session=agent_db_session)  
    report = await report_service.find_by_id(report_id)  
    if not report:  
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")  
    return report  