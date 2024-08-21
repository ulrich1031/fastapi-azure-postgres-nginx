import os
from typing import Optional, Type, List
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool, tool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from app.utils.highchart_ai import HighChartAI
from app.config import get_settings


class HighChartInput(BaseModel):
    # pass
    data: List = Field(description="data to visualize")
    query: str = Field(description="natural language description of the chart including chart type, title, and other details")
    
    
class HighChartTool(BaseTool):
    name = "highchart_tool"
    description = "useful to generate various types of chart with popular Highcharts for visualization of data"
    args_schema: Type[BaseModel] = HighChartInput
    
    def _run(
        self, data: List, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        raise NotImplemented

    async def _arun(
        self, data: List, query: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        highchart_ai = HighChartAI()
        result = await highchart_ai.generate_chart(data=data, query=query)
        settings = get_settings()
        return {
            "link": settings.DOMAIN + "static/images/charts/" + result
        }
        # hc_export.save_as_png(config=high_chart_config, filename="./result.png")
        