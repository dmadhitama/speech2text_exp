import streamlit as st  
from settings import CopilotSettings  
from langchain_core.prompts import ChatPromptTemplate  
import os  
from streamlit_chat import message  
from st_audiorec import st_audiorec  
import soundfile as sf
from pydub import AudioSegment 
from io import BytesIO

from llms.azure_llm import gpt
from llms.vertexai_llm import gemini
from prompts import sys_prompt
from stt_calls.azure_stt import recognize_using_azure
from stt_calls.vertexai_stt import recognize_using_vertexai

from pathlib import Path  
import vertexai  
from google.cloud import aiplatform  


# Initialize Vertex AI
if 'credentials' not in st.session_state:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account/dwh-siloam-99402e61edd2.json"

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
        st.session_state['credentials'] = credentials
        aiplatform.init(project=PROJECT_ID, location=REGION, credentials=credentials)
        vertexai.init(project=PROJECT_ID, location=REGION, credentials=credentials)

config = CopilotSettings()

# Page title
st.set_page_config(page_title='🦜🔗 Speech/Text to SOAP App')
st.title('🦜🔗 Speech/Text to SOAP App')

# SOAP prompt system loading
system_message = sys_prompt.system_message

# Dropdown list of STT models  
stt_str = st.selectbox(
    "Speech to Text Models",
    ("Azure", "Vertex AI")
)

# Dropdown list of LLMs
llm_str = st.selectbox(
    "Large Language Models",
    ("GPT-4", "Gemini-1.5")
)

# Initialize session state for audio data and transcript
if 'audio_data' not in st.session_state:
    st.session_state['audio_data'] = None
if 'file' not in st.session_state:
    st.session_state['file'] = None
if 'transcript' not in st.session_state:  
    st.session_state['transcript'] = ''
  
# Audio recording  
new_audio_data = st_audiorec()  

# Audio file uploading
uploaded_file = st.file_uploader("Choose an audio file", type=["wav"])
  
# Update session state with new audio data  
if new_audio_data is not None:  
    st.session_state['audio_data'] = new_audio_data  
    st.audio(st.session_state['audio_data'], format='audio/wav')
    # Convert the audio data bytes to an AudioSegment  
    bytes_data = new_audio_data
    audio_bytes_data = BytesIO(bytes_data)
    audio_segment = AudioSegment.from_wav(audio_bytes_data)
    # Determine the number of channels and sample rate
    num_channels = audio_segment.channels
    sample_rate = audio_segment.frame_rate

if uploaded_file is not None:
    data, sample_rate = sf.read(uploaded_file)
    # Determine the number of channels  
    if data.ndim == 1:  
        num_channels = 1  # Mono  
    else:  
        num_channels = data.shape[1]  # Stereo or more
    bytes_data = uploaded_file.getvalue()

# Button for transcription
if st.button('Transcribe'):  
    if st.session_state['file'] is not None or st.session_state['audio_data'] is not None:  
        with st.spinner('Transcribing...'):
            if stt_str == "Azure":  
                st.session_state['transcript'] = recognize_using_azure(content=bytes_data)  
            elif stt_str == "Vertex AI":  
                st.session_state['transcript'] = recognize_using_vertexai(
                    content=bytes_data,
                    sample_rate=sample_rate,
                    num_channels=num_channels
                )
  
# Text area for transcript  
txt_input = st.text_area('Transcript', st.session_state['transcript'], height=200)  
  
# Form to accept user's text input for summarization  
with st.form('summarize_form', clear_on_submit=True):  
    if st.form_submit_button('Generate SOAP note'):
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
  
        if not isinstance(response, str):  
            st.info(response.content)  
        else:  
            st.info(response)  
  
        # logging  
        print(txt_input)  
        print("================================================")  
        print(response)  
