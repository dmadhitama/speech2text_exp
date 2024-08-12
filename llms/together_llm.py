from langchain_together import ChatTogether
from settings import CopilotSettings

config = CopilotSettings()

def together(
    config=config,
    model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
):
    return ChatTogether(
        temperature=0,
        model=model,
        together_api_key=config.TOGETHER_API_KEY # Optional if not set as an environment variable
    )