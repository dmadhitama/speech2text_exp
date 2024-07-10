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

def generate_response_from_gemini(input_text, config):
    # TBD
    pass

def GPT():
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

Here are some boundaries for you to remember:
- DO NOT add any additional sections in the SOAP notes other than the Subjective, Objective, Assessment, and Plan sections!
- Do not fabricate any information. If you are unsure about something, simply do not add any additional information.
- The transcripts might be in Indonesian, and you should generate the SOAP notes in Indonesian. 
- Do not include ICD-10 Codes information in the SOAP notes.
- Do not translate these Subjective, Objective, Assessment, & Plan title sections to Indonesian languages.
"""
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account/dwh-siloam-99402e61edd2.json"

# Text input
# txt_input = st.text_area('Enter your text', '', height=200)

# Form to accept user's text input for summarization
# result = []
with st.form('summarize_form'):#, clear_on_submit=True):
    txt_input = st.text_area('Enter your text', height=200)
    submitted = st.form_submit_button('Submit')

    if txt_input != '':
        with st.spinner('Processing...'):
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_message),
                    ("human", "{question}"),
                ]
            )
            chain = prompt | gemini()
            response = chain.invoke({"question": txt_input})
            # result.append(response)

        print(txt_input)
        print("================================================")
        print(response)
        # if len(result):
        st.info(response)
