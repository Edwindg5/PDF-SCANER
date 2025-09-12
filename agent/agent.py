#scanner/ agent/agent.py
from pydantic_ai import Agent
from dotenv import load_dotenv
from .output import ReporteAnalisisSuelo
import os
from typing import  List
load_dotenv()

agent = Agent(
    "gemini-2.5-flash",
    system_prompt=(
       """ Eres un extractor de datos de  documentos especializado. tu funcion 
        es extraer datos estructurados de documentos PDF y sobre cada hoja del PDF
        """
       
    ),
  output_type = List[ReporteAnalisisSuelo]
)
