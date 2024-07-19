from fastapi import FastAPI, File, UploadFile, Form  
from fastapi.responses import JSONResponse  
from pydub import AudioSegment  
from io import BytesIO  
from fastapi.middleware.cors import CORSMiddleware  

import os
import random
import string

from pathlib import Path  
import vertexai  
from google.cloud import aiplatform  

from stt_calls.groq_stt import recognize_using_groq
from stt_calls.azure_stt import recognize_using_azure
from stt_calls.vertexai_stt import recognize_using_vertexai, recognize_using_vertexai_via_uri
from utils.bytes2gcsuri import upload_wav_to_gcs

from langchain_core.prompts import ChatPromptTemplate  
from groq import Groq
from prompts import sys_prompt
from settings import CopilotSettings  

from llms.azure_llm import gpt
from llms.vertexai_llm import gemini
from llms.groq_llm import groq


config = CopilotSettings()
app = FastAPI()  
  
# Add CORS middleware  
app.add_middleware(  
    CORSMiddleware,  
    allow_origins=["*"],  # Allow all origins. Change this to specific origins in production.  
    allow_credentials=True,  
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)  
    allow_headers=["*"],  # Allow all headers  
)

@app.on_event("startup")  
async def startup_event():  
    # Initialize Vertex AI  
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
        aiplatform.init(project=PROJECT_ID, location=REGION, credentials=credentials)  
        vertexai.init(project=PROJECT_ID, location=REGION, credentials=credentials)
  
@app.post("/transcribe")  
async def transcribe(
    audio: UploadFile = File(...), 
    stt_model: str = Form(...)
):  
    audio_data = await audio.read()
      
    # Convert audio file to required format  
    audio_segment = AudioSegment.from_file(BytesIO(audio_data))  
    audio_segment = audio_segment.set_frame_rate(16000).set_channels(1)  
    audio_data = audio_segment.export(format="wav").read()  
      
    if stt_model == "azure":  
        transcript = recognize_using_azure(audio_data)  
    elif stt_model == "vertex":  
        transcript = recognize_using_vertexai(audio_data)  
    elif stt_model == "vertex_cloud":
        bucket_name = 'stt-poc-demo'
        wavname = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        destination_blob_name = f'audio_files/{wavname}.wav'  # Unique filename for the blob
        print("Uploading file to bucket...")
        gcs_uri = upload_wav_to_gcs(
            audio_data, 
            audio_segment.frame_rate, 
            audio_segment.channels, 
            bucket_name, 
            destination_blob_name
        )
        print("File uploaded to bucket!")
        transcript = recognize_using_vertexai_via_uri(gcs_uri)  
    elif stt_model == "groq":
        client = Groq(
            api_key=config.GROQ_API_KEY,
        )
        transcript = recognize_using_groq(client, audio_data)  
      
    return JSONResponse(content={"transcription": transcript})  
  
@app.post("/generate_soap")  
async def generate_soap(
    transcription: str = Form(...), 
    llm_model: str = Form(...)
): 
    # SOAP prompt system loading
    system_message = sys_prompt.system_message
    prompt = ChatPromptTemplate.from_messages(  
            [  
                ("system", system_message),  
                ("human", "{question}"),  
            ]
        )
    if llm_model == "gpt4":  
        llm = gpt()  
    elif llm_model == "gemini":  
        llm = gemini()  
    elif llm_model == "groq_gemma2":  
        llm = groq()  
    elif llm_model == "groq_llama3":  
        llm = groq(model="llama3-70b-8192")  
      
    chain = prompt | llm
    response = chain.invoke({"question": transcription}) 
    if not isinstance(response, str):  
        soap_note = response.content
    else:  
        soap_note = response 
      
    return JSONResponse(content={"soap_note": soap_note})
  
if __name__ == '__main__':  
    import uvicorn  
    uvicorn.run(app, host='127.0.0.1', port=8008)  
