import azure.cognitiveservices.speech as speechsdk
import tempfile
from settings import CopilotSettings

config = CopilotSettings()

def recognize_using_azure(
        content: bytes,
        language: str = "id-ID",
        silence_timeout: str = "5000",
    ):
    # This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
    speech_config = speechsdk.SpeechConfig(
        subscription=config.AZURE_SPEECH_KEY, 
        region=config.AZURE_SPEECH_REGION
    )
    speech_config.speech_recognition_language = language
    speech_config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, silence_timeout)

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(content)
        temp_file.seek(0)
        audio_config = speechsdk.audio.AudioConfig(filename=temp_file.name)

    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, 
        audio_config=audio_config
    )
    
    # speech_recognition_result = speech_recognizer.recognize_once_async().get()
    speech_recognition_result = speech_recognizer.recognize_once()
    print("Recognition completed.")

    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print("Recognized: {}".format(speech_recognition_result.text))
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
            print("Did you set the speech resource key and region values?")
    
    return speech_recognition_result.text