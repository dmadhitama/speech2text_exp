import streamlit as st
from settings import CopilotSettings
from langchain_core.prompts import ChatPromptTemplate

import os
from streamlit_chat import message
from st_audiorec import st_audiorec

from llms.azure_llm import gpt
from llms.vertexai_llm import gemini
from prompts import sys_prompt

from stt_calls.azure_stt import recognize_using_azure
from stt_calls.vertexai_stt import recognize_using_vertexai

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


system_message = sys_prompt.system_message

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account/dwh-siloam-99402e61edd2.json"

wav_audio_data = st_audiorec()

if wav_audio_data is not None:
    st.audio(wav_audio_data, format='audio/wav')
# if wav_audio_data is not None:
    # txt_input = recognize_using_vertexai(content=wav_audio_data)
    txt_input = recognize_using_azure(content=wav_audio_data)
    txt_input = st.text_area('Transcript', txt_input, height=200)
    # st.write(txt_input)
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
