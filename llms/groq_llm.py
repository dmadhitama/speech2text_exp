from langchain_groq import ChatGroq
from settings import CopilotSettings  

config = CopilotSettings()

def groq(
    config=config,
    model="gemma2-9b-it"
):
    return ChatGroq(
        temperature=0,
        model=model,
        api_key=config.GROQ_API_KEY # Optional if not set as an environment variable
    )