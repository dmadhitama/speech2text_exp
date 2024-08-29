from pydub import AudioSegment  
from io import BytesIO  
import requests
from fastapi import HTTPException
from utils.helper import init_logger
from settings import CopilotSettings  

config = CopilotSettings()
# Logger initialization
logger = init_logger(config.LOG_PATH)

def get_confirm_token(response):  
    for key, value in response.cookies.items():  
        if key.startswith('download_warning'):  
            return value  
    return None  
  
def download_file_from_google_drive(file_url):  
    file_id = file_url.split('/')[-2]  
    base_url = "https://drive.google.com/uc?export=download"  
    session = requests.Session()  
  
    response = session.get(base_url, params={'id': file_id}, stream=True)  
    token = get_confirm_token(response)  
  
    if token:  
        params = {'id': file_id, 'confirm': token}  
        response = session.get(base_url, params=params, stream=True)    
    return response  
    
def get_filename_from_response(response):  
    if 'Content-Disposition' in response.headers:  
        content_disposition = response.headers['Content-Disposition']  
        filename = content_disposition.split('filename=')[1].strip('"')  
        return filename  
    return None  
  
def read_audio_from_google_drive(file_url, audio_format='mp3'):  
    response = download_file_from_google_drive(file_url)  
    filename = get_filename_from_response(response)
    if response.status_code == 200:
        try:
            audio_content = response.content
            file_extension = filename.split('.')[-1]
            if not file_extension:
                logger.error(f"Unsupported audio file extension. File format: {file_extension} found.")
                raise HTTPException(
                    status_code=415,
                    detail="Invalid audio file format. Only .wav & .mp3 are allowed."
                )  

            audio_segment = AudioSegment.from_file(BytesIO(audio_content))
            logger.debug(f"Audio duration: {len(audio_segment)} milliseconds")  
            logger.info(f"File: {filename} has been processed")
            audio_data = audio_segment.export(format=file_extension).read()
            return audio_data, file_extension
        except Exception as e:  
            err_msg = f"Failed to decode audio: {e}"
            logger.error(err_msg)
            raise HTTPException(
                status_code=400, 
                detail=err_msg
            )
    else:  
        err_msg = f"Failed to download file. Status code: {response.status_code}"
        logger.error(err_msg)  
        raise HTTPException(
            status_code=400, 
            detail=err_msg
        )