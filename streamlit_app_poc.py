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

st.title('🦜🔗 Speech/Text to SOAP App')

def generate_response_from_gpt(
        input_text, 
        config,
        messages
    ):
    system_message = """
    You are an expert physician. Generate a separate SOAP note for each problem from the following transcript. The SOAP note should be concise and utilize bullet point format. Include ICD-10 and CPT codes in parentheses next to the diagnosis and services. Generate a detailed Subjective section, with all diagnoses separated. Include plans for each assessment. Include all relevant information discussed in the transcript.

    The transcripts will be in Indonesian language and you will also generate the text in Indonesian.

    After the SOAP note is generated, there might be multiple follow-up questions. You should answer them only if they are related to the SOAP generation process. You can fix the answer or revise only part of the SOAP. Do not make things up in this section. If you don't know what you are doing, just say you do not know.

    Generate the SOAP answer as markdown formatted.
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_message
            ),
            MessagesPlaceholder(variable_name="message"),
        ]
    )
    llm = AzureChatOpenAI(
        deployment_name=config.OPENAI_DEPLOYMENT_NAME,
        api_key=config.OPENAI_API_KEY,
        openai_api_version=config.OPENAI_API_VERSION,
        azure_endpoint=config.OPENAI_API_ENDPOINT,
        temperature=0,
        max_tokens=8192,
        streaming=False,
    )
    chain = (
        prompt
        | llm
    )
    query = HumanMessage(
        content=input_text
    )
    messages.append(query)
    response = chain.invoke({"message": messages})
    return response

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
You are an expert physician. Generate a separate SOAP note for each problem from the following transcript. The SOAP note should be concise and utilize bullet point format. Include ICD-10 and CPT codes in parentheses next to the diagnosis and services. Generate a detailed Subjective section, with all diagnoses separated. Include plans for each assessment. Include all relevant information discussed in the transcript.

The transcripts will be in Indonesian language and you will also generate the text in Indonesian.

After the SOAP note is generated, there might be multiple follow-up questions. You should answer them only if they are related to the SOAP generation process. You can fix the answer or revise only part of the SOAP. Do not make things up in this section. If you don't know what you are doing, just say you do not know.
"""
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account/dwh-demo-357404-3324cccb0fbf.json"
msgs = StreamlitChatMessageHistory(key="special_app_key")

if len(msgs.messages) == 0:
    msgs.add_ai_message("Ada yang bisa saya bantu?")

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_message),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ]
)
chain = prompt | gemini()


chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: msgs,  # Always return the instance created earlier
    input_messages_key="question",
    history_messages_key="history",
)

for msg in msgs.messages:
    st.chat_message(msg.type).write(msg.content)

if prompt := st.chat_input():
    st.chat_message("human").write(prompt)

    # As usual, new messages are added to StreamlitChatMessageHistory when the Chain is called.
    config = {"configurable": {"session_id": "any"}}
    response = chain_with_history.invoke({"question": prompt}, config)
    st.chat_message("ai").write(response)
