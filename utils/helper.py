from fastapi import HTTPException
from loguru import logger

def get_file_extension_from_mime(mime_type):  
    if mime_type == "audio/wav" or mime_type == "audio/x-wav":  
        return "wav"  
    elif mime_type == "audio/mpeg":  
        return "mp3"  
    else:  
        return None 
    
def check_audio_duration(audio_duration):
    if audio_duration < 5:
        logger.error("Audio duration is less than 5 seconds.")
        raise HTTPException(
            status_code=417, 
            detail="Audio duration is less than 5 seconds."
        )
    if audio_duration > 600:
        logger.error("Audio duration is over 10 minutes.")
        raise HTTPException(
            status_code=417, 
            detail="Audio duration is over 10 minutes."
        )