import streamlit as st  
import queue  
import re  
import sys  
from google.cloud import speech  
import pyaudio  
import threading  
  
# Audio recording parameters  
RATE = 16000  
CHUNK = int(RATE / 10)  # 100ms  
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account/dwh-siloam-99402e61edd2.json"
  
# Global variable to manage recording state  
recording = False  
  
# Queue to store transcription results  
transcription_queue = queue.Queue()  
  
class MicrophoneStream:  
    """Opens a recording stream as a generator yielding the audio chunks."""  
    def __init__(self, rate=RATE, chunk=CHUNK):  
        self._rate = rate  
        self._chunk = chunk  
        self._buff = queue.Queue()  
        self.closed = True  
  
    def __enter__(self):  
        self._audio_interface = pyaudio.PyAudio()  
        self._audio_stream = self._audio_interface.open(  
            format=pyaudio.paInt16,  
            channels=1,  
            rate=self._rate,  
            input=True,  
            frames_per_buffer=self._chunk,  
            stream_callback=self._fill_buffer,  
        )  
        self.closed = False  
        return self  
  
    def __exit__(self, type, value, traceback):  
        self._audio_stream.stop_stream()  
        self._audio_stream.close()  
        self.closed = True  
        self._buff.put(None)  
        self._audio_interface.terminate()  
  
    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):  
        self._buff.put(in_data)  
        return None, pyaudio.paContinue  
  
    def generator(self):  
        while not self.closed:  
            chunk = self._buff.get()  
            if chunk is None:  
                return  
            data = [chunk]  
            while True:  
                try:  
                    chunk = self._buff.get(block=False)  
                    if chunk is None:  
                        return  
                    data.append(chunk)  
                except queue.Empty:  
                    break  
            yield b"".join(data)  
  
def listen_print_loop(responses):  
    global recording  
    num_chars_printed = 0  
    for response in responses:  
        if not response.results:  
            continue  
        result = response.results[0]  
        if not result.alternatives:  
            continue  
        transcript = result.alternatives[0].transcript  
        overwrite_chars = " " * (num_chars_printed - len(transcript))  
        if not result.is_final:  
            sys.stdout.write(transcript + overwrite_chars + "\r")  
            sys.stdout.flush()  
            num_chars_printed = len(transcript)  
            st.write(transcript + overwrite_chars + "\r")  
        else:  
            print(transcript + overwrite_chars)  
            transcription_queue.put(transcript + overwrite_chars)  
            num_chars_printed = 0  
        if not recording:  
            break  
    return transcript  
  
def main():  
    language_code = "en-US"  
    client = speech.SpeechClient()  
    config = speech.RecognitionConfig(  
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,  
        sample_rate_hertz=RATE,  
        language_code=language_code,  
    )  
    streaming_config = speech.StreamingRecognitionConfig(  
        config=config, interim_results=True  
    )  
  
    with MicrophoneStream(RATE, CHUNK) as stream:  
        audio_generator = stream.generator()  
        requests = (  
            speech.StreamingRecognizeRequest(audio_content=content)  
            for content in audio_generator  
        )  
        responses = client.streaming_recognize(streaming_config, requests)  
        transcript = listen_print_loop(responses)  
  
def start_recording():  
    global recording  
    recording = True  
    st.session_state.transcript = ""  
    threading.Thread(target=main).start()  
  
def stop_recording():  
    global recording  
    recording = False  
  
st.title("Real-Time Speech-to-Text Transcription")  
  
if "transcript" not in st.session_state:  
    st.session_state.transcript = ""  
  
if st.button("Record"):  
    start_recording()  
  
if st.button("Stop"):  
    stop_recording()  
  
# Display the transcription results from the queue  
while not transcription_queue.empty():  
    st.session_state.transcript += transcription_queue.get() + "\n"  
  
st.write("Transcript:")  
st.write(st.session_state.transcript)  
