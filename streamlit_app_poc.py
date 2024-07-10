import streamlit as st
from settings import CopilotSettings

from langchain_openai import AzureChatOpenAI
from langchain_google_vertexai import VertexAI, ChatVertexAI, create_structured_runnable

from settings import CopilotSettings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.chat_message_histories import (
    StreamlitChatMessageHistory,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.callbacks.base import BaseCallbackHandler

from langchain.schema import ChatMessage
import os
from streamlit_chat import message
from st_audiorec import st_audiorec

config = CopilotSettings()

# Initialize Vertex AI
from pathlib import Path
import vertexai
from google.cloud import aiplatform

PROJECT_ID = 'dwh-siloam'
REGION = 'asia-southeast1'
print(f"Project ID: {PROJECT_ID}\nRegion: {REGION}")

print(f"Checking Credentials...")
if not any((Path.cwd()/"service_account").glob('*.json')):
    print("Service account folder is empty. Fallback using default gcloud account")
    aiplatform.init(project=PROJECT_ID, location=REGION)
    vertexai.init(project=PROJECT_ID, location=REGION)
else:
    print('Using service account credentials from service_account folder')
    from google.oauth2 import service_account
    sa_file = list((Path.cwd()/"service_account").glob('*.json'))[0]
    print(f"Using service account file: {sa_file}")
    credentials = service_account.Credentials.from_service_account_file(sa_file)
    aiplatform.init(project=PROJECT_ID, location=REGION, credentials=credentials)
    vertexai.init(project=PROJECT_ID, location=REGION, credentials=credentials)


# Page title
st.set_page_config(page_title='🦜🔗 Speech/Text to SOAP App')
st.title('🦜🔗 Speech/Text to SOAP App')

def gpt():
    return AzureChatOpenAI(
            deployment_name=config.OPENAI_DEPLOYMENT_NAME,
            api_key=config.OPENAI_API_KEY,
            openai_api_version=config.OPENAI_API_VERSION,
            azure_endpoint=config.OPENAI_API_ENDPOINT,
            temperature=0,
            max_tokens=8192,
            streaming=False,
            # callback_manager=[stream_handler],
        )

def gemini():
    return VertexAI(
        model_name=config.GCP_AGENT_MODEL_NAME, 
        temperature=0, 
        max_output_tokens=8192
    )


system_message = """
You are an expert physician. Generate a single SOAP (Subjective, Objective, Assessment, & Plan) note from the following transcript. The SOAP note should be concise and use bullet points.

Create a detailed Subjective section, with all diagnoses separated. Provide plans for each assessment and include all relevant information discussed in the transcript. In the Assessment section, include detailed disease information. If the transcript does not contain any information related to medication or prescriptions, you should provide detailed medicine information (including prescription details) based on your own knowledge, as it is necessary for the pharmacy to prepare the medicine. But do not provide this information as a new section.

Please provide a SOAP note only if the transcript contains sufficient information, such as patient details, doctor's assessment, diagnostic information, or medication-related information. If the information is insufficient, simply state that the information is not enough and specify the additional details needed to complete the note.

Here are some boundaries for you to remember:
- DO NOT add any additional sections in the SOAP notes other than the Subjective, Objective, Assessment, and Plan sections!
- Do not fabricate any information. If you are unsure about something, simply do not add any additional information.
- The transcripts might be in Indonesian, and you should generate the SOAP notes in Indonesian. 
- Do not include ICD-10 Codes information in the SOAP notes.
- Do not translate these Subjective, Objective, Assessment, & Plan title sections to Indonesian languages.
"""
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account/dwh-siloam-99402e61edd2.json"

wav_audio_data = st_audiorec()

if wav_audio_data is not None:
    st.audio(wav_audio_data, format='audio/wav')

def recognize(filename=None, content=None):
    import azure.cognitiveservices.speech as speechsdk

    # This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
    speech_config = speechsdk.SpeechConfig(
        subscription=config.AZURE_SPEECH_KEY, 
        region=config.AZURE_SPEECH_REGION
    )
    speech_config.speech_recognition_language="id-ID"

    # audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True) # using microphone
    # if filename:
    #     audio_config = speechsdk.audio.AudioConfig(filename=filename) # using file
    # elif content:
    audio_config = speechsdk.audio.AudioConfig(content=content) # using bytes
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, 
        audio_config=audio_config
    )

    print("Speak into your microphone.")
    speech_recognition_result = speech_recognizer.recognize_once_async().get()
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
    return speech_recognition_result

from google.cloud import speech
def transcribe_model_selection(
    # speech_file: str,
    # model: str,
    content
) -> speech.RecognizeResponse:
    """Transcribe the given audio file synchronously with
    the selected model."""
    client = speech.SpeechClient()

    # with open(speech_file, "rb") as audio_file:
    #     content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=44100,
        language_code="id-ID",
        audio_channel_count=2,
        # model=model,
    )

    response = client.recognize(config=config, audio=audio)

    for i, result in enumerate(response.results):
        alternative = result.alternatives[0]
        print("-" * 20)
        print(f"First alternative of result {i}")
        print(f"Transcript: {alternative.transcript}")

    return alternative.transcript

# Text input
# txt_input = st.text_area('Transcript', '', height=200)
st.write("Transcript:\n")
if wav_audio_data is not None:
    txt_input = transcribe_model_selection(content=wav_audio_data)
    st.write(txt_input)
else:
    txt_input = ''

# Dropdown list of models
llm_str = st.selectbox(
    "Large Language Models",
    ("GPT-4", "Gemini-1.5")
)

# Form to accept user's text input for summarization
with st.form('summarize_form', clear_on_submit=True):
    submitted = st.form_submit_button('Submit')

    if txt_input != '':
        with st.spinner('Processing...'):
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_message),
                    ("human", "{question}"),
                ]
            )
            if llm_str == "GPT-4":
                llm = gpt()
            elif llm_str == "Gemini-1.5":
                llm = gemini()
            chain = prompt | llm
            response = chain.invoke({"question": txt_input})
            # result.append(response)

        # logging
        print(txt_input)
        print("================================================")
        print(response)
        
        if not isinstance(response, str):
            st.info(response.content)
        else:
            st.info(response)
