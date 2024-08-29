from fastapi import HTTPException
from loguru import logger
from zoneinfo import ZoneInfo  
import tzlocal  
import os
import time
import sys

from settings import CopilotSettings  
config = CopilotSettings()

def init_logger(log_file_path):
    os.environ['TZ'] = 'Asia/Bangkok'
    time.tzset()
    log_level = "DEBUG"
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS zz}</green> | <level>{level: <8}</level> | <yellow>Line {line: >4} ({file}):</yellow> <b>{message}</b>"
    logger.add(log_file_path, level=log_level, format=log_format, colorize=False, backtrace=True, diagnose=True)
    return logger

# Logger initialization
logger = init_logger(config.LOG_PATH)

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
    
def convert_time_to_gmt7(local_time):
    # Automatically detect the local timezone  
    local_tz = tzlocal.get_localzone()  
    # Attach local timezone info to the current local time  
    localized_time = local_time.replace(tzinfo=local_tz)  
    # Define the target timezone (GMT+7)  
    target_tz = ZoneInfo('Asia/Bangkok')  # GMT+7   
    # Convert the localized time to the target timezone  
    return localized_time.astimezone(target_tz)