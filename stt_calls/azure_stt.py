import azure.cognitiveservices.speech as speechsdk
import tempfile
from settings import CopilotSettings

config = CopilotSettings()

def recognize_using_azure_old(content):
    # This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
    speech_config = speechsdk.SpeechConfig(
        subscription=config.AZURE_SPEECH_KEY, 
        region=config.AZURE_SPEECH_REGION
    )
    speech_config.speech_recognition_language="id-ID"

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(content)
        temp_file.seek(0)
        audio_config = speechsdk.audio.AudioConfig(filename=temp_file.name)

    # audio_config = speechsdk.audio.AudioConfig(stream=content) # using bytes
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, 
        audio_config=audio_config
    )

    speech_recognition_result = speech_recognizer.recognize_once_async().get()
    print("Recognition completed.")
    speech_config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "3000")

    # speech_recognition_result = speech_recognizer.start_continuous_recognition_async()
    # print("Recognizing...")
    # speech_recognizer.stop_continuous_recognition_async()
    # print("Recognition completed.")

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
    
    return speech_recognition_result

def recognize_using_azure(content):
    # This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
    speech_config = speechsdk.SpeechConfig(
        subscription=config.AZURE_SPEECH_KEY, 
        region=config.AZURE_SPEECH_REGION
    )
    speech_config.speech_recognition_language="id-ID"

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(content)
        temp_file.seek(0)
        audio_config = speechsdk.audio.AudioConfig(filename=temp_file.name)

    # audio_config = speechsdk.audio.AudioConfig(stream=content) # using bytes
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, 
        audio_config=audio_config
    )

    done = False

    def recognizing_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        print('RECOGNIZING: {}'.format(evt))

    def recognized_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        print('RECOGNIZED: {}'.format(evt))

    def stop_cb(evt: speechsdk.SessionEventArgs):
        """callback that signals to stop continuous recognition"""
        print('CLOSING on {}'.format(evt))
        nonlocal done
        done = True

    # Connect callbacks to the events fired by the speech recognizer
    speech_recognizer.recognizing.connect(recognizing_cb)
    speech_recognizer.recognized.connect(recognized_cb)
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    # Perform recognition. `start_continuous_recognition_async asynchronously initiates continuous recognition operation,
    # Other tasks can be performed on this thread while recognition starts...
    # wait on result_future.get() to know when initialization is done.
    # Call stop_continuous_recognition_async() to stop recognition.
    result_future = speech_recognizer.start_continuous_recognition_async()

    result_future.get()  # wait for voidfuture, so we know engine initialization is done.
    print('Continuous Recognition is now running, say something.')

    while not done:
        # No real sample parallel work to do on this thread, so just wait for user to type stop.
        # Can't exit function or speech_recognizer will go out of scope and be destroyed while running.
        print('type "stop" then enter when done')
        stop = input()
        if (stop.lower() == "stop"):
            print('Stopping async recognition.')
            speech_recognizer.stop_continuous_recognition_async()
            break

    print("recognition stopped, main thread can exit now.")
    return result_future