from langchain_openai import AzureChatOpenAI
from settings import CopilotSettings

config = CopilotSettings()
def gpt():
    return AzureChatOpenAI(
            deployment_name=config.OPENAI_DEPLOYMENT_NAME,
            api_key=config.OPENAI_API_KEY,
            openai_api_version=config.OPENAI_API_VERSION,
            azure_endpoint=config.OPENAI_API_ENDPOINT,
            temperature=0,
            max_tokens=8192,
            streaming=False,
            # callback_manager=[stream_handler],
        )