import os
from collections import deque
from fastapi import APIRouter, Depends, HTTPException, Query  
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/log", tags=["Log"])

@router.get("")
async def get_log(lines: int = Query(100)):
    """
    Return log file content.
    
    Query Params:

        lines (int): number of lines to check. Default is 100.
    """
    try:
        with open("/var/log/cadenza/app.log", "r") as log_file:
            log_contents= ''.join(deque(log_file, 100))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read log file: {str(e)}")
    
    return PlainTextResponse(log_contents)
