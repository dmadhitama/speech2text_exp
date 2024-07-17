import streamlit as st  
from settings import CopilotSettings  
from langchain_core.prompts import ChatPromptTemplate  
import os  
from streamlit_chat import message  
from st_audiorec import st_audiorec  
import soundfile as sf
from pydub import AudioSegment 
from io import BytesIO
import random
import string

from llms.azure_llm import gpt
from llms.vertexai_llm import gemini
from prompts import sys_prompt
from stt_calls.azure_stt import recognize_using_azure
from stt_calls.vertexai_stt import recognize_using_vertexai, recognize_using_vertexai_via_uri
from utils.bytes2gcsuri import upload_wav_to_gcs

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
# stt_str = st.selectbox(
#     "Speech to Text Models",
#     ("Azure", "Vertex AI")
# )
stt_str = "Vertex AI"

# Dropdown list of LLMs
# llm_str = st.selectbox(
#     "Large Language Models",
#     ("GPT-4", "Gemini-1.5")
# )
llm_str = "Gemini-1.5"

# Initialize session state for audio data and transcript
if 'audio_data' not in st.session_state:
    st.session_state['audio_data'] = None
if 'file' not in st.session_state:
    st.session_state['file'] = None
if 'transcript' not in st.session_state:  
    st.session_state['transcript'] = ''
if 'rec_sample_rate' not in st.session_state:
    st.session_state['rec_sample_rate'] = 0
if 'rec_channels' not in st.session_state:
    st.session_state['rec_channels'] = 0
if 'file_sample_rate' not in st.session_state:
    st.session_state['file_sample_rate'] = 0
if 'file_channels' not in st.session_state:
    st.session_state['file_channels'] = 0
  
# Audio recording  
new_audio_data = st_audiorec()  
# Audio file uploading
uploaded_file = st.file_uploader("Choose an audio file", type=["wav"])
  
# Update session state with new audio data  
if new_audio_data is not None:  
    st.session_state['audio_data'] = new_audio_data
    # Convert the audio data bytes to an AudioSegment
    audio_bytes_data = BytesIO(st.session_state['audio_data'])
    audio_segment = AudioSegment.from_wav(audio_bytes_data)
    # Determine the number of channels and sample rate
    st.session_state['rec_channels'] = audio_segment.channels
    st.session_state['rec_sample_rate'] = audio_segment.frame_rate

if uploaded_file is not None:
    st.audio(uploaded_file, format='audio/wav')
    data, st.session_state['file_sample_rate'] = sf.read(uploaded_file)
    # Determine the number of channels  
    if data.ndim == 1:  
        st.session_state['file_channels'] = 1  # Mono  
    else:  
        st.session_state['file_channels'] = data.shape[1]  # Stereo or more
    st.session_state['file'] = uploaded_file.getvalue()

# Dropdown list of what data will be transcribed
data_str = st.selectbox(
    "What data will be transcribed?",
    ("Recording", "File")
)
# Drop down whether file saved locally or on cloud
store_str = st.selectbox(
    "Where to store audio file?",
    ("Local", "Cloud")
)

if data_str == "Recording":
    bytes_data = st.session_state['audio_data']
    sample_rate = st.session_state['rec_sample_rate']
    num_channels = st.session_state['rec_channels']
elif data_str == "File":
    bytes_data = st.session_state['file']
    sample_rate = st.session_state['file_sample_rate']
    num_channels = st.session_state['file_channels']

# Button for transcription
if st.button('Transcribe'):
    if store_str == "Local":
        with st.spinner('Transcribing...'):
            if stt_str == "Azure":  
                st.session_state['transcript'] = recognize_using_azure(content=bytes_data)  
            elif stt_str == "Vertex AI":  
                st.session_state['transcript'] = recognize_using_vertexai(
                    content=bytes_data,
                    sample_rate=sample_rate,
                    num_channels=num_channels
                )

    elif store_str == "Cloud":
        with st.spinner('Transcribing...'):
            if stt_str == "Azure":
                pass
            elif stt_str == "Vertex AI":
                bucket_name = 'stt-poc-demo'
                wavname = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
                destination_blob_name = f'audio_files/{wavname}.wav'  # Unique filename for the blob
                print("Uploading file to bucket...")
                gcs_uri = upload_wav_to_gcs(
                    bytes_data, 
                    sample_rate, 
                    num_channels, 
                    bucket_name, 
                    destination_blob_name
                )
                print("File uploaded to bucket!")
                st.session_state['transcript'] = recognize_using_vertexai_via_uri(
                    gcs_uri=gcs_uri,
                    sample_rate=sample_rate,
                    num_channels=num_channels
                )
  
# Text area for transcript  
txt_input = st.text_area('Transcription result', st.session_state['transcript'], height=200)  
  
# Form to accept user's text input for summarization  
with st.form('summarize_form', clear_on_submit=True):  
    if st.form_submit_button('Generate SOAP Note'):
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
