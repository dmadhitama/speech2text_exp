import streamlit as st  
from settings import CopilotSettings  
from langchain_core.prompts import ChatPromptTemplate  
import os  
from st_audiorec import st_audiorec  
import soundfile as sf
from pydub import AudioSegment 
from io import BytesIO
import random
import string
import time

from llms.azure_llm import gpt
from llms.vertexai_llm import gemini
from llms.groq_llm import groq
from prompts import sys_prompt
from stt_calls.groq_stt import recognize_using_groq
from stt_calls.azure_stt import recognize_using_azure
from stt_calls.vertexai_stt import recognize_using_vertexai, recognize_using_vertexai_via_uri
from utils.bytes2gcsuri import upload_wav_to_gcs
from utils.convert_wav_audio import convert_audio_from_file, convert_audio_from_bytes

from pathlib import Path  
import vertexai  
from google.cloud import aiplatform  
from groq import Groq

config = CopilotSettings()

client = Groq(
        api_key=config.GROQ_API_KEY,
    )

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

# Page title
st.set_page_config(page_title='🏥 Speech/Text to SOAP App')
st.title('🏥 Speech/Text to SOAP App')
# Input patient name
patient_name = st.text_input("Patient name", "")

# SOAP prompt system loading
system_message = sys_prompt.system_message

# Dropdown list of STT models  
stt_str = st.selectbox(
    "Speech to Text Models",
    (
        "Azure (Local Processing)", 
        "Vertex AI (Local Processing)", 
        "Vertex AI (Cloud Processing)",
        "Groq (Local Processing)",
    )
)
# stt_str = "Vertex AI"

# Dropdown list of LLMs
llm_str = st.selectbox(
    "Large Language Models",
    (
        "GPT-4", 
        "Gemini-1.5", 
        "Groq"
    )
)
# llm_str = "Groq"

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

    # convert the audio data bytes to 16000 Hz sample rate nad mono
    st.session_state['audio_data'] = convert_audio_from_bytes(
        st.session_state['audio_data'],
        target_sample_rate=16000,
        target_channels=1,
    )

    # Convert the audio data bytes to an AudioSegment
    audio_bytes_data = BytesIO(st.session_state['audio_data'])
    audio_segment = AudioSegment.from_wav(audio_bytes_data)
    # Determine the number of channels and sample rate
    st.session_state['rec_channels'] = audio_segment.channels
    st.session_state['rec_sample_rate'] = audio_segment.frame_rate

    # Raised warning if this condition met
    if st.session_state['rec_channels'] != 1:
        print("Warning: audio is not mono! May be affecting the processing.")
    if st.session_state['rec_sample_rate'] != 16000:
        print("Warning: audio sample rate is not 16000 Hz! May be affecting the processing.")

if uploaded_file is not None:
    st.audio(uploaded_file, format='audio/wav')

    # convert the audio data bytes to 16000 Hz sample rate and mono
    start = time.time()
    uploaded_file = convert_audio_from_file(
        uploaded_file,
        target_sample_rate=16000,
        target_channels=1,
    )
    print(f"Audio converted to mono & 16000 Hz sample rate for about: {round(time.time() - start, 2)} seconds")
    st.session_state['file'] = uploaded_file.getvalue()

    data, st.session_state['file_sample_rate'] = sf.read(uploaded_file)
    # Determine the number of channels  
    if data.ndim == 1:  
        st.session_state['file_channels'] = 1  # Mono  
    else:  
        st.session_state['file_channels'] = data.shape[1]  # Stereo or more
    # Raised warning if this condition met
    if st.session_state['file_channels'] != 1:
        print("Warning: audio is not mono! May be affecting the processing.")
    if st.session_state['file_sample_rate'] != 16000:
        print("Warning: audio sample rate is not 16000 Hz! May be affecting the processing.")

# Dropdown list of what data will be transcribed
data_str = st.selectbox(
    "What data will be transcribed?",
    ("Recording", "File")
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
    start = time.time()
    with st.spinner('Transcribing...'):
        if stt_str == "Azure (Local Processing)":  
            st.session_state['transcript'] = recognize_using_azure(content=bytes_data)

        elif stt_str == "Vertex AI (Local Processing)":  
            st.session_state['transcript'] = recognize_using_vertexai(
                content=bytes_data,
                sample_rate=sample_rate,
                num_channels=num_channels
            )

        elif stt_str == "Vertex AI (Cloud Processing)":
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

        elif stt_str == "Groq (Local Processing)":
            st.session_state['transcript'] = recognize_using_groq(
                client,
                content=bytes_data
            )
        end = time.time() - start

    st.write(f"Transcription took {end:.2f} seconds")
  
    if patient_name != '':
        patient_str = "Nama pasien: " + patient_name + "\n"
        st.session_state['transcript'] = patient_str + st.session_state['transcript']
        patient_name = ''

# Text area for transcript
txt_input = st.text_area('Transcription result', st.session_state['transcript'], height=200)  
  
# Form to accept user's text input for summarization  
with st.form('summarize_form', clear_on_submit=True):
    if st.form_submit_button('Generate SOAP Note'):
        with st.spinner('Processing...'):
            start = time.time()
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
            elif llm_str == "Groq":
                llm = groq() 
  
            chain = prompt | llm  
            response = chain.invoke({"question": txt_input})  

            end = time.time() - start
            st.write(f"Transcription took {end:.2f} seconds")
  
        if not isinstance(response, str):  
            st.info(response.content)  
        else:  
            st.info(response)  

        # logging  
        print(txt_input)  
        print("================================================")  
        print(response)  
