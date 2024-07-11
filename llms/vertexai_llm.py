from langchain_google_vertexai import VertexAI, ChatVertexAI, create_structured_runnable
from settings import CopilotSettings

config = CopilotSettings()

def gemini():
    return VertexAI(
        model_name=config.GCP_AGENT_MODEL_NAME, 
        temperature=0, 
        max_output_tokens=8192
    )