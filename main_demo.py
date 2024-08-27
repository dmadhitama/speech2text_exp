from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse  
from fastapi.middleware.cors import CORSMiddleware  
from typing import Optional  

import os
import json
import datetime
from pydub import AudioSegment  
from io import BytesIO  
import boto3

from stt_calls.groq_stt import recognize_using_groq
from utils.parse_soap import parse_soap_note
from utils.gdrive import read_audio_from_google_drive
from utils.s3 import read_audio_from_s3_bucket
from utils.helper import (
    get_file_extension_from_mime,
    check_audio_duration
)

from langchain_core.prompts import ChatPromptTemplate  
from groq import Groq
from prompts import (
    sys_prompt, 
    sys_prompt_2,
    sys_prompt_mod,
)
from settings import CopilotSettings  

from llms.azure_llm import gpt
from llms.vertexai_llm import gemini
from llms.groq_llm import groq
from llms.together_llm import together
from database.db import connect_and_insert

from loguru import logger
import sys
import base64
import magic


log_level = "DEBUG"
log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS zz}</green> | <level>{level: <8}</level> | <yellow>Line {line: >4} ({file}):</yellow> <b>{message}</b>"
logger.add(sys.stderr, level=log_level, format=log_format, colorize=True, backtrace=True, diagnose=True)
logger.add("logs.log", level=log_level, format=log_format, colorize=False, backtrace=True, diagnose=True)


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

from fastapi import Request
@app.post("/soap_demo")  
async def soap_demo(   
    request: Request, 
    id: Optional[str] = Form(None),  
    lang_id: Optional[str] = Form(None),  
    audio: Optional[UploadFile] = File(None),  
    base64_audio: Optional[str] = Form(None),  
    google_drive_url: Optional[str] = Form(None),  
    s3_uri: Optional[str] = Form(None),  
    aws_access_key_id: Optional[str] = Form(None),  
    aws_secret_access_key: Optional[str] = Form(None)  
):  
    if request.headers.get("Content-Type") == "application/json":  
        body = await request.json()  
        id = body.get("id")  
        lang_id = body.get("lang_id")  
        base64_audio = body.get("base64_audio")  
        google_drive_url = body.get("google_drive_url")  
        s3_uri = body.get("s3_uri")  
        aws_access_key_id = body.get("aws_access_key_id")  
        aws_secret_access_key = body.get("aws_secret_access_key")  
        # Note: Handling file uploads in raw JSON is not straightforward and typically not recommended.  
        # You might need to handle file uploads separately or use a different approach. 
    
    json_data_dir = "json_data/"  
      
    #### Checking existing id and json files ####  
    if not os.path.exists(json_data_dir):  
        logger.error("JSON directory does not exist!")  
        logger.info("Creating new JSON directory...")  
        os.makedirs(json_data_dir)  
        logger.info("New JSON directory created!")  
      
    json_ids = [json_id.replace(".json", "") for json_id in os.listdir(json_data_dir)]  
      
    if id not in json_ids:  
        #### STT Process ####  
        # Validate and read audio data  
        audio_data = None  
        file_extension = None  
          
        if audio:  
            file_extension = audio.filename.split(".")[-1].lower()  
            audio_data = await audio.read()  
          
        elif base64_audio:  
            try:  
                audio_data = base64.b64decode(base64_audio)  
                mime = magic.Magic(mime=True)  
                mime_type = mime.from_buffer(audio_data)  
                logger.info(f"Detected MIME type: {mime_type}")  
                file_extension = get_file_extension_from_mime(mime_type)  
                if not file_extension:  
                    logger.error(f"Unsupported audio file extension. File format: {file_extension} found.")  
                    raise HTTPException(  
                        status_code=415,  
                        detail="Invalid audio file format. Only .wav & .mp3 are allowed."  
                    )  
            except Exception as e:  
                logger.error("Invalid base64 audio data.")  
                logger.error(f"{str(e)}")  
                raise HTTPException(  
                    status_code=400,  
                    detail="Invalid base64 audio data."  
                )  
          
        elif google_drive_url:  
            try:  
                audio_data, file_extension = read_audio_from_google_drive(google_drive_url)  
            except Exception as e:  
                logger.error("Error downloading audio from Google Drive.")  
                logger.error(f"{str(e)}")  
                raise HTTPException(  
                    status_code=400,  
                    detail="Error downloading audio from Google Drive."  
                )  
          
        elif s3_uri and aws_access_key_id and aws_secret_access_key:  
            try: 
                # Authentication 
                if os.environ.get("AWS_ACCESS_KEY_ID") is None:
                    os.environ["AWS_ACCESS_KEY_ID"] = aws_access_key_id
                if os.environ.get("AWS_SECRET_ACCESS_KEY") is None:
                    os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret_access_key
                # Initialize the S3 client  
                s3 = boto3.client('s3')  
                # Read audio data from S3 bucket
                audio_data, file_extension = read_audio_from_s3_bucket(s3, s3_uri)
            except Exception as e:
                logger.error("Error reading audio from S3 bucket.")  
                logger.error(f"{str(e)}")  
                raise HTTPException(  
                    status_code=400,  
                    detail="Error reading audio from S3 bucket."  
                )
            
        else:  
            raise HTTPException(  
                status_code=400,  
                detail="No valid audio input provided."  
            )
        
        # Validate file extension  
        allowed_extensions = {"wav", "mp3"}  
        if file_extension not in allowed_extensions:  
            logger.error("Invalid file format. Only .wav & .mp3 are allowed.")  
            raise HTTPException(  
                status_code=415,  
                detail="Invalid audio file format. Only .wav & .mp3 are allowed."  
            ) 
        
        # Convert audio file to required format  
        audio_segment = AudioSegment.from_file(BytesIO(audio_data))  
        audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        audio_data = audio_segment.export(format=file_extension).read()

        # Estimate the duration of the audio  
        audio_dur = audio_segment.duration_seconds

        # Error response for under length or over length audio duration
        try:
            check_audio_duration(audio_dur)
        except Exception as e:
            logger.error("Audio duration is below or over the required duration.")
            logger.error(f"{str(e)}")
            raise HTTPException(
                status_code=417, 
                detail="Audio duration is below or over the required duration."
            )

        # Transcription process
        try:
            client = Groq(
                api_key=config.GROQ_API_KEY,
            )
            transcript = recognize_using_groq(
                client, 
                audio_data,
                lang_id
            )
        except Exception as e:
            logger.error("Error while transcribing audio:")
            logger.error(f"{str(e)}")
            raise HTTPException(
                status_code=500, 
                detail="Error while transcribing audio."
            )

        #### SOAP Generation ####
        # SOAP prompt system loading
        system_message = sys_prompt.system_message
        prompt = ChatPromptTemplate.from_messages(  
                [  
                    ("system", system_message),  
                    ("human", "{question}"),  
                ]
            )
        # groq available models
        # "llama3-70b-8192", "gemma2-9b-it"
        llm = groq(model="gemma2-9b-it")
        chain = prompt | llm
        
        try:
            response = chain.invoke({"question": transcript})
        except Exception as e:
            logger.error("Error while generating SOAP note:")
            logger.error(f"{str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error while generating SOAP note."
            )
        
        if not isinstance(response, str):  
            soap_note = response.content
            metadata = response.response_metadata
        else:  
            soap_note = response

        # Save metadata information to database
        row_data = (  
            str(datetime.datetime.now()),  # datetime  
            audio_dur, # audio_duration  
            metadata['token_usage']['prompt_tokens'], # token_prompt  
            metadata['token_usage']['completion_tokens'], # token_completion  
            metadata['token_usage']['total_tokens'], # token_total  
            transcript, # transcript  
            soap_note # llm_response  
        )

        try:
            connect_and_insert(
                database=config.POSTGRES_DB, 
                user=config.POSTGRES_USER, 
                password=config.POSTGRES_PASSWORD, 
                host=config.POSTGRES_HOST, 
                port=config.POSTGRES_PORT,
                row_data=row_data
            )
        except Exception as e:
            logger.error("Error saving metadata information to database:")
            logger.error(f"{str(e)}")

        # Parse the response into JSON format
        try:
            soap_note_dict = parse_soap_note(soap_note)
        except Exception as e:
            logger.error("Error parsing SOAP note:")
            logger.error(f"{str(e)}")
            raise HTTPException(
                status_code=422, 
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
    uvicorn.run(app, host='0.0.0.0', port=1433)  
