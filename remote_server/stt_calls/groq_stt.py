import tempfile

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
    print("Result:")
    print(transcription.text)

    return transcription.text
