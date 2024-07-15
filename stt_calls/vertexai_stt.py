from google.cloud import speech

def recognize_using_vertexai(
    # speech_file: str,
    # model: str,
    content,
    sample_rate=16000,
    num_channels=1
) -> speech.RecognizeResponse:
    """Transcribe the given audio file synchronously with
    the selected model."""
    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(content=content)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate,
        language_code="id-ID",
        audio_channel_count=num_channels,
        # model=model,
    )

    response = client.recognize(config=config, audio=audio)

    full_results = []
    for i, result in enumerate(response.results):
        alternative = result.alternatives[0]
        print("-" * 20)
        print(f"First alternative of result {i}")
        print(f"Transcript: {alternative.transcript}")
        full_results.append(alternative.transcript)

    return ". ".join(full_results)