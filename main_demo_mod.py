from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
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
from utils.gdrive import read_audio_from_google_drive
from utils.s3 import read_audio_from_s3_bucket
from utils.helper import (
    get_file_extension_from_mime,
    check_audio_duration,
    convert_time_to_gmt7,
    init_logger
)

from groq import Groq
from settings import CopilotSettings  

from llms.groq_llm import groq
from database.db import connect_and_insert, MetadataSaver
from utils.json_handler import JSONHandler
from processor.audio import AudioProcessor
from processor.transcript2soap import Transcript2SOAP

import base64
import magic


config = CopilotSettings()
app = FastAPI()  

# Logger initialization
logger = init_logger(config.LOG_PATH)

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
    json_handler = JSONHandler(id, json_data_dir)
    json_handler.check_and_create_json_dir()
      
    #### Checking existing id and json files ####  
    if not json_handler.json_exists():
        # STT Process 
        audio_processor = AudioProcessor(
            logger=logger,
            audio=audio,
            base64_audio=base64_audio,
            google_drive_url=google_drive_url,
            s3_uri=s3_uri,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        await audio_processor.process_audio()
  
        try:  
            client = Groq(api_key=config.GROQ_API_KEY)  
            transcript = recognize_using_groq(
                client, 
                audio_processor.audio_data, 
                lang_id
            )  
        except Exception as e:  
            raise HTTPException(
                status_code=500, 
                detail="Error while transcribing audio."
            )  
        
        # SOAP Generating Process
        transcript2soap = Transcript2SOAP(transcript)
        transcript2soap.generate_soap()
        # transcript2soap.generate_soap_with_structured_output_parser() # TBD - NEXT FIX
  
        metadata_saver = MetadataSaver(
            audio_processor.audio_duration, 
            transcript2soap.metadata, 
            transcript, 
            transcript2soap.soap_note
        )  
        metadata_saver.save_metadata()  
  
        soap_note_dict = transcript2soap.parse_soap()  
  
        content = {  
            "id": id,  
            "datetime": str(convert_time_to_gmt7(datetime.datetime.now())),  
            "audio_duration": audio_processor.audio_duration,  
            "transcript": transcript,  
            "raw_soap_note": transcript2soap.soap_note,  
            "json_soap_note": soap_note_dict  
        }  
        json_handler.save_json(content) 
        
    else:
        content = json_handler.load_json()

    return JSONResponse(content=content)
  
if __name__ == '__main__':  
    import uvicorn  
    uvicorn.run(app, host='0.0.0.0', port=1433)  
