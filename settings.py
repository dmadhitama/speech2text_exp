"""
Configuration Settings for the application
"""
from pathlib import Path

from pydantic_settings import BaseSettings

# Load Environment File
env_file = "envs/.env.dev"
if not Path(env_file).exists():
    print(
        f"Environment File {env_file} not found. please create one based on envs/.env.dev. exiting..."
    )
    exit()


class CopilotSettings(BaseSettings):
    """Settings for the application"""

    ENV: str = "DEV"

    # API
    API_CHAT_NAME: str = "Copilot Chat API"
    API_CHAT_DESCRIPTION: str = "API for Copilot Chat"
    API_CHAT_VERSION: str = "0.1.0"

    # Prompts
    PROMPT_DIR: Path = Path("prompts")
    SYSTEM_PROMPT_DIR: str = "systems"
    TXT2SQL_PROMPT_DIR: str = "text_to_sql"
    GWI_PROMPT_DIR: str = "gwi"
    GWI_TABLE_DESC: str = "gwi_table_description.prompt"
    GWI_SUMMARIZER_PROMPT: str = "gwi_summarize_question.prompt"

    # STT
    PROSA_API_KEY: str = "ajksdh12398ajlds1209"
    GROQ_API_KEY: str = "adjk128"
    AZURE_SPEECH_KEY: str = "asdkjwkwkwk213"
    AZURE_SPEECH_REGION: str = "pemalang23"
    
    # LLM
    GCP_PROJECT_ID: str = "test"
    GCP_SERVICE_ACCOUNT: str = "service-account.json"
    GCP_MODEL_NAME: str = "text-bison@002"
    GCP_GEMINI_MODEL_NAME: str = "gemini-1.5-pro-001"
    GCP_AGENT_MODEL_NAME: str = "text-bison-32k@002"
    GCP_EMBEDDING_MODEL_NAME: str = "textembedding-gecko@003"
    GCP_MULTILINGUAL_EMBEDDING_MODEL_NAME: str = "text-multilingual-embedding-002"
    GCP_CODE_MODEL_NAME: str = "code-bison@latest"
    GCP_CHAT_MODEL_NAME: str = "chat-bison@latest"
    GCP_VERTEXAI_REGION: str = "asia-southeast1"
    OPENAI_API_TYPE: str = "azure"
    OPENAI_API_VERSION: str = "2024-02-01"
    OPENAI_API_ENDPOINT: str = "test"
    OPENAI_API_BASE: str = "https://api.openai.com"
    OPENAI_API_KEY: str = "3123xasd"
    OPENAI_DEPLOYMENT_NAME: str = "test"
    OPENAI_MODEL_NAME: str = "text-davinci-003"  # "gpt-35-turbo"
    TEMPERATURE: float = 0
    MAX_TOKENS: int = 2048
    STREAMING: bool = True
    EMBEDDING_DIM: int = 768
    MAX_SQL_GENERATOR_RETRIES: int = 1

    AZURE_DOCS_INT_ENDPOINT: str = "https://www.google.com"
    AZURE_DOCS_INT_API_KEY: str = "das312"

    # DB
    DATA_FOLDER: Path = Path("data")
    SERVICE_ACCOUNT_FOLDER: Path = Path("service_account")
    SQLITE_DB_FILE: str = "copilot.db"
    CHROMA_DB_FILE: str = "chroma_db"

    # PostgreDB
    POSTGRES_USER: str = "testuser"
    POSTGRES_PASSWORD: str = "testpwd"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_DB: str = "copilot_db"
    POSTGRES_PORT: int = 5432

    # Data
    DATA_EMPTY: str = "Data is empty."

    # MEMORY
    MEMORY_KEY: str = "chat_history"
    MEMORY_SIZE: int = 5

    class Config:
        env_file = env_file
        env_file_encoding = "utf-8"
