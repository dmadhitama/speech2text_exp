import streamlit as st
from settings import CopilotSettings

from langchain_openai import AzureChatOpenAI
from settings import CopilotSettings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import (
    StreamlitChatMessageHistory,
)
from langchain_core.runnables.history import RunnableWithMessageHistory

config = CopilotSettings()

st.title('🦜🔗 Chatbot App')

def generate_response_from_gpt(
        input_text, 
        config,
        messages
    ):
    system_message = """
    You are a helpful assistant.
    Answer the question below using Indonesian language.
    Do not make any assumptions. If you don't know the answer, just answer that you don't know.
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

messages = [
    AIMessage(
        content="Halo, apa kabar?",
    ),
    HumanMessage(
        content="Baik."
    ),
    AIMessage(
        content="Ada yang bisa saya bantu?",
    ),
]
history = StreamlitChatMessageHistory(key="chat_messages")
history.add_ai_message("Halo! Apa kabar?")
history.add_user_message("Baik.")
history.add_ai_message("Ada yang bisa saya bantu?")

system_message = """
You are a helpful assistant.
Answer the question below using Indonesian language.
Do not make any assumptions. If you don't know the answer, just answer that you don't know.
"""
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_message),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
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

chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: history,  # Always return the instance created earlier
    input_messages_key="question",
    history_messages_key="history",
)

for msg in history.messages:
    st.chat_message(msg.type).write(msg.content)

if prompt := st.chat_input():
    st.chat_message("human").write(prompt)

    # As usual, new messages are added to StreamlitChatMessageHistory when the Chain is called.
    config = {"configurable": {"session_id": "any"}}
    response = chain_with_history.invoke({"question": prompt}, config)
    st.chat_message("ai").write(response.content)

# with st.form('my_form'):
#     text = st.text_area('Masukkan pertanyaan:')
#     submitted = st.form_submit_button('Submit')
#     response = generate_response_from_gpt(
#         text, 
#         config,
#         messages
#     )

#     print(text)
#     print(response)
#     answer = response.content
#     st.info(answer)

#     query = HumanMessage(
#         content=text
#     )
#     answer = AIMessage(
#         content=answer
#     )

#     messages.append(answer)
#     messages.append(query)
