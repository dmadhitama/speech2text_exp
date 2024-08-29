import tempfile
from utils.helper import init_logger
from settings import CopilotSettings  

config = CopilotSettings()
# Logger initialization
logger = init_logger(config.LOG_PATH)

def recognize_using_groq(
        client,
        content: bytes,  # Audio file in bytes
        language: str = "id",  # Optional, defaults to "id-ID"
        model: str = "whisper-large-v3"  # Optional, defaults to ""whisper-large-v3""
    ):

    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
        temp_file.write(content)
        temp_file.seek(0)

    transcription = client.audio.transcriptions.create(
        file=(temp_file.name, content),
        model=model,
        prompt="Specify context or spelling",  # Optional
        response_format="json",  # Optional
        language=language,  # Optional
        temperature=0.0  # Optional
    )
    logger.debug("Result:")
    logger.debug(transcription.text)

    return transcription.text
