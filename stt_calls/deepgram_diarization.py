from deepgram import DeepgramClient, PrerecordedOptions, FileSource
import re
from settings import CopilotSettings
from utils.helper import init_logger

config = CopilotSettings()
# Logger initialization
logger = init_logger(config.LOG_PATH)
DEEPGRAM_API_KEY = config.DEEPGRAM_API_KEY

def generate_transcript(paragraphs):
    """
    It should be run using smart_format=True mode
    """
    speaker_id = []
    metadata = []
    transcript = ""
    for paragraph in paragraphs:
        spk_id = paragraph.speaker
        speaker_id.append(spk_id)
        transcript += f"Speaker {spk_id}: "
        for sentence in paragraph.sentences:
            metadata.append({
                "text": sentence.text,
                "start": sentence.start,
                "end": sentence.end,
                "speaker_id": spk_id
            })
            transcript += sentence.text + " "
        transcript += "\n"
    return transcript, metadata, list(set(speaker_id))

def recognize_diarization_deepgram(
        url: str = None,
        file: str = None,
        audio_data: bytes = None,
        model: str = "whisper-medium",
        language: str = "id",
        diarization: bool = True,
        api_key: str = DEEPGRAM_API_KEY
):
    try:
        logger.info("Starting Deepgram Diarization")
        deepgram = DeepgramClient(api_key)

        options = PrerecordedOptions(
            model=model,
            language=language,
            smart_format=True,
            utt_split=0.8,
            diarize=diarization,
        )

        if url:
            AUDIO_URL = {
                "url": url
            }
            response = deepgram.listen.prerecorded.v("1").transcribe_url(AUDIO_URL, options)
        elif file:
            with open(file, "rb") as f:
                buffer_data = f.read()
            payload: FileSource = {
                "buffer": buffer_data,
            }
            response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
        elif audio_data:
            payload: FileSource = {
                "buffer": audio_data,
            }
            response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)

        paragraphs = response.results.channels[0].alternatives[0].paragraphs.paragraphs
        raw_transcript, metadata, speaker_id = generate_transcript(paragraphs)

        # concatenate the transcript with the speaker name
        transcript = "List of Speakers:\n"
        for speaker in speaker_id:
            transcript += f"- Speaker {speaker}\n"

        transcript += "\nTranscript:\n" + raw_transcript
        # logger.debug(response)
        logger.debug(f"List of Speakers: {speaker_id}")
        return response, transcript, metadata

    except Exception as e:
        logger.error(f"Exception: {e}")

        return None, None, None
