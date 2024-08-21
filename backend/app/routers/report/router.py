import json
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.database.config import get_agent_db_session, get_main_db_session
from app.database.main import TenantService
from app.database.agent import ReportService, ReportModel, ChunkService, MessageService, MessageModel
from app.services import ReportFlowService
from app.enums import ChunkTypeEnum, MessageRoleEnum, MessageTypeEnum
from app.utils.logging import AppLogger
from app.exceptions.http_exception import NotFoundHTTPException
from .schema import *
from .dependency import get_report_by_id

logger = AppLogger().get_logger()

router = APIRouter(prefix="/report", tags=["Report"])

@router.get("/", response_model=List[ReportResponseModel])
async def get_reports(
    skip: int = 0,
    limit: int = 10,
    agent_db_session=Depends(get_agent_db_session)
):
    """
    Get reports
    """
    report_service = ReportService(db_session=agent_db_session)
    return [ ReportResponseModel(**result.model_dump()) for result in await report_service.find_all(skip=skip, limit=limit)]

@router.get("/{report_id}", response_model=ReportResponseModel)
async def get_report(
    report: ReportModel = Depends(get_report_by_id)
):
    """
    Get report from report_id
    """
    return report

@router.delete("/{report_id}", response_model=ReportResponseModel)
async def get_report(
    report: ReportModel = Depends(get_report_by_id),
    agent_db_session=Depends(get_agent_db_session)
):
    """
    Get report from report_id
    """
    report_service = ReportService(db_session=agent_db_session)
    await report_service.delete_report(report)


@router.get("/{report_id}/chunks", response_model=List[ChunkResponseModel])
async def get_chunks(
    type: ChunkTypeEnum,
    skip: int = 0,
    limit: int = 10,
    report: ReportModel = Depends(get_report_by_id),
    agent_db_session=Depends(get_agent_db_session)
):
    """
    Get chunks by report id and chunk type
    """
    chunk_service = ChunkService(db_session=agent_db_session)
    chunks = await chunk_service.find_chunks_by_report_id_and_type(report_id=report.uuid, skip=skip, limit=limit, type=type.value)
    return chunks
     
@router.post("/{report_id}/run-query", response_model=List[ChunkResponseModel])
async def run_query(
    report_id: UUID, 
    model: RunQueryRequestModel,
    report: ReportModel = Depends(get_report_by_id),
    agent_db_session=Depends(get_agent_db_session),
    main_db_session=Depends(get_main_db_session),
):
    """
    Run additional custom user query.
    
    Parameters:
    
        report_id (str): Report ID for user to run query
        
        query (str): User query to run search
        
        type (str): Search Type. "INTERNAL" or "WEB" or "FILE" or "URL"
    
    Response:

        List of chunks.

    Example Responses:

        [
            {
                "type": "INTERNAL",
                "query": "Arts and Crafts Workshops conducted by Cadenza Children’s Foundation funded by the Smith Family",
                "score": 3.1973040103912354,
                "source": "34130cb7-d720-4f17-a214-ff960a34a65b/sharepoint/Cadenza Internal/Documents/Demo/Impact Reports/Quarterly Program Impact Summary.docx",
                "content": 'content',
                "captions_text": 'content',
                "captions_highlights": 'content',
                "report_id": "b10c5110-5fec-4d77-a67a-3eb055e15269",
                "created_at": "2024-07-07T18:05:41.983394",
                "updated_at": "2024-07-07T18:05:41.983398",
                "uuid": "cc44ba2a-7a08-4fb6-853b-a4656798d277",
            }
        ],
        
    """
    
    tenant_service = TenantService(db_session=main_db_session)

    tenant_model = await tenant_service.find_by_uuid(report.tenant_id)
    if not tenant_model:
        raise NotFoundHTTPException(msg=f"Tenant with {report.tenant_id} not found")
    
    report_flow_service = ReportFlowService(
        tenant=tenant_model,
        report=report,
        db_session=agent_db_session,
        langfuse_trace_args={
            "name": "run-custom-query",
            "metadata": {
                'reportID': report_id,
                "request_params": model.model_dump()
            },
        },
    )
    results = await report_flow_service.run_custom_query(query=model.query, type=model.type)
    return [ChunkResponseModel(**result.model_dump()) for result in results]

@router.post("/{report_id}/upload-file", response_model=bool)
async def upload_file(
    report: ReportModel = Depends(get_report_by_id),
    files: List[UploadFile] = File(...),
    agent_db_session=Depends(get_agent_db_session),
    main_db_session=Depends(get_main_db_session)
):
    """
    Upload custom files for the report.
    
    Parameters:
    
        files (List[UploadFile]): files to embed
        
    """
    
    tenant_service = TenantService(db_session=main_db_session)

    tenant_model = await tenant_service.find_by_uuid(report.tenant_id)
    if not tenant_model:
        raise NotFoundHTTPException(msg=f"Tenant with {report.tenant_id} not found")
    
    report_flow_service = ReportFlowService(
        tenant=tenant_model,
        report=report,
        db_session=agent_db_session
    )
    await report_flow_service.embed_uploaded_files(files=files)
    return True
        

@router.post("/initiate-research", response_model=InitiateResearchResponseModel)
async def initiate_research(
    tenant_id: UUID = Form(...),  
    report_target_audience: str = Form(...),  
    report_additional_information: str = Form(...),  
    report_objective: str = Form(...), 
    files: List[UploadFile] = None,
    agent_db_session=Depends(get_agent_db_session),
    main_db_session=Depends(get_main_db_session),
):
    """
    Initiate web & internal research.
    
    Parameters (FormData):

        tenant_id (UUID): UUID of tenant
        
        report_target_audience (str): Target audience of the report
        
        report_additional_information (str): Additional Information of the report
        
        report_objective (str): Objective of the report
        
        files (List[UploadFile]): custom files to use for research.
        
    Response:

        report_id (UUID): UUID of the new report.
        
        research_chunks: internal and web search chunks.
        
            Example: 
                {
                    "internal": [
                        {
                            "type": "INTERNAL",
                            "query": "Arts and Crafts Workshops conducted by Cadenza Children’s Foundation funded by the Smith Family",
                            "score": 3.1973040103912354,
                            "source": "34130cb7-d720-4f17-a214-ff960a34a65b/sharepoint/Cadenza Internal/Documents/Demo/Impact Reports/Quarterly Program Impact Summary.docx",
                            "content": 'content',
                            "captions_text": 'content',
                            "captions_highlights": 'content',
                            "report_id": "b10c5110-5fec-4d77-a67a-3eb055e15269",
                            "created_at": "2024-07-07T18:05:41.983394",
                            "updated_at": "2024-07-07T18:05:41.983398",
                            "uuid": "cc44ba2a-7a08-4fb6-853b-a4656798d277",
                        }
                    ],
                    "web": [
                        {
                            "type": "WEB",
                            "query": "Impact of arts and crafts workshops on children's development",
                            "score": 0.8951667116997488,
                            "source": "https://www.parentcircle.com/benefits-of-arts-and-crafts-for-children-development/article",
                            "content": 'content',
                            "captions_text": 'content',
                            "captions_highlights": 'content',
                            "report_id": "b10c5110-5fec-4d77-a67a-3eb055e15269",
                            "created_at": "2024-07-07T18:05:48.841051",
                            "updated_at": "2024-07-07T18:05:48.841061",
                            "uuid": "097d403d-daf2-41c0-bd29-7b5182414f17",
                        }
                    ],
                }
    """
    tenant_service = TenantService(db_session=main_db_session)

    tenant_model = await tenant_service.find_by_uuid(tenant_id)
    if not tenant_model:
        raise NotFoundHTTPException(msg=f"Tenant with {tenant_id} not found")

    report_flow_service = ReportFlowService(
        tenant=tenant_model,
        db_session=agent_db_session,
        langfuse_trace_args={
            "name": "initiate-research",
            "metadata": {
                "request_params": {
                    'tenant_id': tenant_id,
                    'report_target_audience': report_target_audience,
                    'report_additional_information': report_additional_information,
                    'report_objective': report_objective
                }
            },
        },
    )
    
    return await report_flow_service.initiate_research(
        report_conf={
            'tenant_id': tenant_id,
            'report_target_audience': report_target_audience,
            'report_additional_information': report_additional_information,
            'report_objective': report_objective            
        },
        files=files,
        # urls=urls
    )

@router.post("/{report_id}/generate-report", response_model=ReportResponseModel)
async def generate_report(
    model: GenerateReportRequestModel,
    report: ReportModel = Depends(get_report_by_id),
    agent_db_session=Depends(get_agent_db_session),
    main_db_session=Depends(get_main_db_session)
):
    """
    Generate report based on chunks.
    
    Parameters:
    
        auto_select (bool): If False, it will use chunks specified in the chunk_ids.
                            If True, it will automatically select 10 top chunks ordered by llm_similarity_score from each web search chunks and internal search chunks, and use those 20 chunks.
                            Default is True.
        
        chunk_ids (List[UUID]): list of chunk ids to use. It will be ignoed when 'auto_select' is True. Default is [].
    """
    logger.info("getting db sessions")
    chunk_service = ChunkService(db_session=agent_db_session)
    tenant_service = TenantService(db_session=main_db_session)
    
    tenant_model = await tenant_service.find_by_uuid(report.tenant_id)
    if not tenant_model:
        raise NotFoundHTTPException(msg=f"Tenant with {report.tenant_id} not found")
    
    report_flow_service = ReportFlowService(
        tenant=tenant_model,
        report=report,
        db_session=agent_db_session,
        langfuse_trace_args={
            "name": "generate-report",
            "metadata": {
                "reportID": report.uuid,
                "request_params": model.model_dump()
            },
        },
    )
    
    if model.auto_select:
        internal_chunks = await chunk_service.find_chunks_by_report_id_and_type(report_id=report.uuid, type=ChunkTypeEnum.INTERNAL.value)
        web_chunks = await chunk_service.find_chunks_by_report_id_and_type(report_id=report.uuid, type=ChunkTypeEnum.WEB.value)
        logger.info("get chunks")
        return await report_flow_service.generate_report_from_chunks(chunks=web_chunks+internal_chunks)
    else:
        chunks = [ await chunk_service.find_chunk_by_id(id=id) for id in model.chunk_ids]
        return await report_flow_service.generate_report_from_chunks(chunks=chunks)

@router.post("/generate-report/v2")  
async def generate_report_v2(  
    tenant_id: UUID = Form(...),  
    report_target_audience: str = Form(...),  
    report_additional_information: str = Form(...),  
    report_objective: str = Form(...),  
    outline: Optional[str] = Form(None),
    files: List[UploadFile] = None,  
    agent_db_session = Depends(get_agent_db_session),  
    main_db_session = Depends(get_main_db_session)  
):
    """
    Generate report step by step from outlining based on chunks.
    
    Parameters:
    
        tenant_id (UUID): UUID of tenant
        
        report_target_audience (str): Target audience of the report
        
        report_additional_information (str): Additional Information of the report

        report_objective (str): Objective of the report

        outline (str): outline str
          example:
            {
                "outline": [
                    {
                        "title": "Section 1 Title",
                        "description": "Section 1 Description",
                        "research": true,
                    },
                    {
                        "title": "Section 2 Title",
                        "description": "Section 2 Description",
                        "research": false,
                    }
                ]
            }
        
        files (List[UploadFile]): custom files to use for research

    Returns:

        report (ReportModel) : final report
    """
    report = ReportModel(tenant_id=tenant_id, report_target_audience=report_target_audience, report_objective=report_objective)
    report_service = ReportService(db_session=agent_db_session)
    report = await report_service.add_report(report)

    tenant_service = TenantService(db_session=main_db_session)
    
    tenant_model = await tenant_service.find_by_uuid(report.tenant_id)
    if not tenant_model:
        raise NotFoundHTTPException(msg=f"Tenant with {report.tenant_id} not found")
    
    report_flow_service = ReportFlowService(
        tenant=tenant_model,
        report=report,
        db_session=agent_db_session,
        langfuse_trace_args={
            "name": "generate-report-v2",
            "metadata": {
                "reportID": report.uuid,
                "request_params": {
                    'tenant_id': tenant_id,
                    'report_target_audience': report_target_audience,
                    'report_additional_information': report_additional_information,
                    'report_objective': report_objective
                }
            },
        },
    )

    report = await report_flow_service.generate_report_v2(  
        report_conf={  
            'tenant_id': tenant_id,  
            'report_target_audience': report_target_audience,  
            'report_additional_information': report_additional_information,  
            'report_objective': report_objective,  
            'outline': outline
        },  
        files=files  
    )  
    return json.loads(report)["content"] 

@router.post("/{report_id}/chat/{session_id}", response_model=ChatWithReportResponseModel)
async def chat_with_report(
    session_id: str,
    model: ChatWithReportRequestModel,
    report: ReportModel =Depends(get_report_by_id),
    agent_db_session=Depends(get_agent_db_session),
    main_db_session=Depends(get_main_db_session)
):
    """
    Chat with report.
    
    Parameters:
    
        report_id (UUID): uuid of report to chat on.
        
        session_id (str): session ID.
        
        message (str): user message
    """
    tenant_service = TenantService(db_session=main_db_session)
    
    message_service = MessageService(db_session=agent_db_session)
    await message_service.add_message(
        message=MessageModel(
            session_id=session_id, 
            role=MessageRoleEnum.USER.value, 
            content=model.message,
            type=MessageTypeEnum.REPORT.value
        )
    )
    
    tenant_model = await tenant_service.find_by_uuid(report.tenant_id)
    if not tenant_model:
        raise NotFoundHTTPException(msg=f"Tenant with {report.tenant_id} not found")
    
    report_flow_service = ReportFlowService(
        tenant=tenant_model,
        report=report,
        db_session=agent_db_session,
        langfuse_trace_args={
            "name": "chat-with-report",
            "metadata": {
                "reportID": report.uuid,
                "session_id": session_id
            },
        },
    )
    
    return ChatWithReportResponseModel(
        content=await report_flow_service.chat_with_report(session_id=session_id)
    )

