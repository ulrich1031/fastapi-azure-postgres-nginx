import os
import uuid
import json
from typing import List, Dict
import highchartexport as hc_export
from app.ai.prompts import HighChartPrompts
from app.utils.openai import AzureOpenAIClient
from app.utils.logging import AppLogger

logger = AppLogger().get_logger()

class HighChartAI:
    def __init__(self):
        self.model = AzureOpenAIClient()
        
    def __export_to_file__(self, config: Dict, type="png", file_path="./static/images/charts", file_name=None):  
        # Ensure the file_path exists  
        if not os.path.exists(file_path):  
            os.makedirs(file_path)  

        if file_name is None:  
            file_name = "highchart_" + str(uuid.uuid4())
        else:
            file_name = "highchart_" + file_name

        # Complete file path  
        file_full_path = os.path.join(file_path, f"{file_name}.{type}")  

        if type == "png":
            hc_export.save_as_png(config, file_full_path)

        logger.info(f"Chart exported to: {file_full_path}")

        return file_name + "." + type
    
    async def generate_chart(self, data: List, query: str):
        logger.info("generating chart...")
        result = await self.model.ainvoke(
            name="generate-chart",
            timeout=30,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": HighChartPrompts.highchart_generation_prompt()
                },
                {
                    "role": "user",
                    "content":  '{query} \n\n {data}'.format(query=query, data=json.dumps(data))
                }
            ]
        )
        config = json.loads(result)
        
        config["credits"] = { 'enabled': False }
        
        logger.info(config)
        return self.__export_to_file__(config=config)