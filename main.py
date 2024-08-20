from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse  
from fastapi.middleware.cors import CORSMiddleware  
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse 

import os
import random
import string
import json
import datetime
from pydub import AudioSegment  
from io import BytesIO  
from pathlib import Path  
import vertexai  
from google.cloud import aiplatform  

from stt_calls.groq_stt import recognize_using_groq
from stt_calls.azure_stt import recognize_using_azure
from stt_calls.vertexai_stt import recognize_using_vertexai, recognize_using_vertexai_via_uri
from utils.bytes2gcsuri import upload_wav_to_gcs
from utils.parse_soap import parse_soap_note

from langchain_core.prompts import ChatPromptTemplate  
from groq import Groq
from prompts import sys_prompt, sys_prompt_2
from settings import CopilotSettings  

from llms.azure_llm import gpt
from llms.vertexai_llm import gemini
from llms.groq_llm import groq
from llms.together_llm import together
from database.db import connect_and_insert

from loguru import logger

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
      
    logger.info(f"Project ID: {PROJECT_ID}\nRegion: {REGION}")  
    logger.info(f"Checking Credentials...")  
  
    if not any((Path.cwd()/"service_account").glob('*.json')):  
        logger.warning("Service account folder is empty. Fallback using default gcloud account")  
        aiplatform.init(project=PROJECT_ID, location=REGION)  
        vertexai.init(project=PROJECT_ID, location=REGION)  
    else:  
        logger.info('Using service account credentials from service_account folder')  
        from google.oauth2 import service_account
        sa_file = list((Path.cwd()/"service_account").glob('*.json'))[0]  
        logger.info(f"Using service account file: {sa_file}")  
        credentials = service_account.Credentials.from_service_account_file(sa_file)  
        aiplatform.init(project=PROJECT_ID, location=REGION, credentials=credentials)  
        vertexai.init(project=PROJECT_ID, location=REGION, credentials=credentials)

app.mount("/static", StaticFiles(directory="static"), name="static")
# Serve the index.html file at the root URL
@app.get("/")  
def read_root():  
    return FileResponse("static/index.html")
  
@app.post("/transcribe")  
async def transcribe(
    id: str = Form(...),
    audio: UploadFile = File(...), 
    stt_model: str = Form(...),
):  
    audio_data = await audio.read()
      
    # Convert audio file to required format  
    audio_segment = AudioSegment.from_file(BytesIO(audio_data))  
    audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    audio_data = audio_segment.export(format="wav").read()

    # Estimate the duration of the audio  
    audio_dur = audio_segment.duration_seconds
      
    if stt_model == "azure":  
        transcript = recognize_using_azure(audio_data)  
    elif stt_model == "vertex":  
        transcript = recognize_using_vertexai(
            audio_data,
            sample_rate=audio_segment.frame_rate,
            num_channels=audio_segment.channels,
        )
    elif stt_model == "vertex_cloud":
        bucket_name = 'stt-poc-demo'
        wavname = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        destination_blob_name = f'audio_files/{wavname}.wav'  # Unique filename for the blob
        logger.info("Uploading file to bucket...")
        gcs_uri = upload_wav_to_gcs(
            audio_data, 
            audio_segment.frame_rate, 
            audio_segment.channels, 
            bucket_name, 
            destination_blob_name
        )
        logger.info("File uploaded to bucket!")
        transcript = recognize_using_vertexai_via_uri(gcs_uri)  
    elif stt_model == "groq":
        client = Groq(
            api_key=config.GROQ_API_KEY,
        )
        transcript = recognize_using_groq(client, audio_data)  
      
    content = {
        "id": id,
        "transcription": transcript,
        "audio_duration": audio_dur,
    }
    return JSONResponse(content=content)  
  
@app.post("/generate_soap")  
async def generate_soap(
    id: str = Form(...),
    transcription: str = Form(...), 
    llm_model: str = Form(...)
): 
    # SOAP prompt system loading
    system_message = sys_prompt_2.system_message
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
    elif llm_model == "together_exp":
        llm = together()
      
    chain = prompt | llm
    response = chain.invoke({"question": transcription}) 
    if not isinstance(response, str):  
        soap_note = response.content
    else:  
        soap_note = response 
    
    content = {
        "id": id,
        "soap_note": soap_note
    }
    return JSONResponse(content=content)

@app.post("/transcribe_and_generate_soap")  
async def transcribe_and_generate_soap(
    id: str = Form(...),
    lang_id: str = Form(...),
    audio: UploadFile = File(...)
):  
    json_data_dir = "json_data/"
    #### Checking existing id and json files ####
    if not os.path.exists(json_data_dir):
        logger.error("JSON directory is not exists!")
        raise HTTPException(
            status_code=490, 
            detail="JSON directory is not exists!"
        )
    
    json_ids = [json_id.replace(".json", "") for json_id in os.listdir(json_data_dir)]

    if id not in json_ids:
        #### STT Process ####
        # Validate file extension  
        allowed_extensions = {"wav", "mp3"}  
        file_extension = audio.filename.split(".")[-1].lower()  
        if file_extension not in allowed_extensions:
            logger.error("Invalid file format. Only .wav & .mp3 are allowed.")
            raise HTTPException(
                status_code=410, 
                detail="Invalid file format. Only .wav & .mp3 are allowed."
            )
        
        audio_data = await audio.read()
        
        # Convert audio file to required format  
        audio_segment = AudioSegment.from_file(BytesIO(audio_data))  
        audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        audio_data = audio_segment.export(format=file_extension).read()

        # Estimate the duration of the audio  
        audio_dur = audio_segment.duration_seconds

        # Error response for under length or over length audio duration
        if audio_dur < 5:
            logger.error("Audio duration is less than 5 seconds.")
            raise HTTPException(
                status_code=411, 
                detail="Audio duration is less than 5 seconds."
            )
        if audio_dur > 600:
            logger.error("Audio duration is over 10 minutes.")
            raise HTTPException(
                status_code=412, 
                detail="Audio duration is over 10 minutes."
            )

        # Transcription process
        client = Groq(
            api_key=config.GROQ_API_KEY,
        )
        transcript = recognize_using_groq(
            client, 
            audio_data,
            lang_id
        )

        #### SOAP Generation ####
        # SOAP prompt system loading
        system_message = sys_prompt_2.system_message
        prompt = ChatPromptTemplate.from_messages(  
                [  
                    ("system", system_message),  
                    ("human", "{question}"),  
                ]
            )
        llm = groq(model="gemma2-9b-it")
        chain = prompt | llm
        response = chain.invoke({"question": transcript}) 
        if not isinstance(response, str):  
            soap_note = response.content
            metadata = response.response_metadata
        else:  
            soap_note = response

        # Save metadata information to database
        row_data = (  
            str(datetime.datetime.now()),  # datetime  
            audio_dur,                  # audio_duration  
            metadata['token_usage']['prompt_tokens'], # token_prompt  
            metadata['token_usage']['completion_tokens'], # token_completion  
            metadata['token_usage']['total_tokens'], # token_total  
            transcript, # transcript  
            soap_note   # llm_response  
        )      
        connect_and_insert(
            database=config.POSTGRES_DB, 
            user=config.POSTGRES_USER, 
            password=config.POSTGRES_PASSWORD, 
            host=config.POSTGRES_HOST, 
            port=config.POSTGRES_PORT,
            row_data=row_data
        )

        # Parse the response into JSON format
        try:
            soap_note_dict = parse_soap_note(soap_note)
        except Exception as e:
            logger.error("Error parsing SOAP note:")
            logger.error(f"{str(e)}")
            raise HTTPException(
                status_code=401, 
                detail=f"Error parsing SOAP note: {str(e)}"
            )

        content = {
            "id": id,
            "datetime": str(datetime.datetime.now()),
            "audio_duration": audio_dur,
            "transcript": transcript,
            "raw_soap_note": soap_note,
            "json_soap_note": soap_note_dict
        }

        json_data_path = os.path.join(json_data_dir, f"{id}.json")
        with open(json_data_path, 'w') as f:
            json.dump(content, f)

    else:
        # JSON file with specific ID exists, hence read its content
        json_data_path = os.path.join(json_data_dir, f"{id}.json")
        with open(json_data_path, 'r') as f:
            content = json.load(f)

    return JSONResponse(content=content)
  
if __name__ == '__main__':  
    import uvicorn  
    uvicorn.run(app, host='127.0.0.1', port=8008)  
