from google.cloud import speech
from loguru import logger

def recognize_using_vertexai(
    # speech_file: str,
    # model: str,
    content: bytes,
    language: str = "id-ID",
    sample_rate: int = 16000,
    num_channels: int = 1
) -> speech.RecognizeResponse:
    """Transcribe the given audio file synchronously with
    the selected model."""
    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(content=content)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate,
        language_code=language,
        audio_channel_count=num_channels,
        # model=model,
    )

    response = client.recognize(config=config, audio=audio)

    full_results = []
    for i, result in enumerate(response.results):
        alternative = result.alternatives[0]
        logger.debug("-" * 20)
        logger.debug(f"First alternative of result {i}")
        logger.debug(f"Transcript: {alternative.transcript}")
        full_results.append(alternative.transcript)

    return ". ".join(full_results)

def recognize_using_vertexai_via_uri(
    gcs_uri: str,
    language: str = "id-ID",
    sample_rate: int = 16000,
    num_channels: int = 1
) -> str:
    """Asynchronously transcribes the audio file specified by the gcs_uri.

    Args:
        gcs_uri: The Google Cloud Storage path to an audio file.
        language: The language code for the audio file.
        sample_rate: The sample rate of the audio file.
        num_channels: The number of channels in the audio file.

    Returns:
        The generated transcript from the audio file provided.
    """

    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate,
        language_code=language,
        audio_channel_count=num_channels,
    )

    operation = client.long_running_recognize(config=config, audio=audio)

    logger.info("Waiting for operation to complete...")
    response = operation.result(timeout=90)

    transcript_builder = []
    results = []
    # Each result is for a consecutive portion of the audio. Iterate through
    # them to get the transcripts for the entire audio file.
    for result in response.results:
        # The first alternative is the most likely one for this portion.
        transcript_builder.append(f"\nTranscript: {result.alternatives[0].transcript}")
        transcript_builder.append(f"\nConfidence: {result.alternatives[0].confidence}")
        results.append(result.alternatives[0].transcript)

    transcript = "".join(transcript_builder)
    logger.debug(transcript)

    return '. '.join(results)
