import fal_client
from settings import CopilotSettings
import os


config = CopilotSettings()
os.environ["FAL_KEY"] = config.FAL_KEY


def get_speakers(chunks: list):
    # list all speakers
    speakers = [chunk['speaker'] for chunk in chunks]
    return list(set(speakers))

def generate_transcripts(chunks):
    transcript = f"List of speakers:\n"
    for speaker in get_speakers(chunks):
        transcript += f"- {speaker}\n"
    transcript += "\n\nTranscript:\n"
    for chunk in chunks:
        speaker = chunk['speaker']
        text = chunk['text']
        transcript += f"{speaker}: {text}\n"
    return transcript

def recognize_diarization_fal(
    content: bytes,
    diar_model: str = "fal-ai/whisper",
    lang_id: str = "id",
    num_speakers: int = None
):
    url = fal_client.upload(content, "text/plain")
    args = {
        "task": "transcribe",
        "version": "3",
        "language": lang_id,
        "audio_url": url,
        "chunk_level": "segment",
        "diarize": True,
        "num_speakers": num_speakers,
    }
    
    result = fal_client.submit(diar_model, arguments=args)
    response = result.get()
    chunks = response['chunks']
    transcript = generate_transcripts(chunks)
    return transcript
