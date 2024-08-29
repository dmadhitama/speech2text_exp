from pydub import AudioSegment  
from io import BytesIO  
import os  
from urllib.parse import urlparse  
from loguru import logger
from fastapi import HTTPException
from utils.helper import init_logger

from settings import CopilotSettings  
config = CopilotSettings()
# Logger initialization
logger = init_logger(config.LOG_PATH)

# Function to read the audio file from S3 into a variable  
def read_audio_file_from_s3(s3, bucket_name, object_key):  
    try:  
        # Get the object from S3  
        s3_object = s3.get_object(Bucket=bucket_name, Key=object_key)  
        # Read the object's content into a BytesIO buffer  
        audio_segment = AudioSegment.from_file(BytesIO(s3_object['Body'].read()))  
        logger.info(f"Read {object_key} from bucket {bucket_name} into memory")  
        return audio_segment  
    except Exception as e:
        err_msg = "Error reading file from S3: " + str(e)
        logger.error(err_msg)
        raise HTTPException(
            status_code=400, 
            detail=err_msg
        )
  
# Function to detect the filename from the S3 object key  
def get_filename_from_key(object_key):  
    return os.path.basename(object_key)  
  
# Function to parse the S3 URI  
def parse_s3_uri(s3_uri):  
    parsed_uri = urlparse(s3_uri)  
    bucket_name = parsed_uri.netloc  
    object_key = parsed_uri.path.lstrip('/')  
    return bucket_name, object_key  

def read_audio_from_s3_bucket(s3, s3_uri):

    # Parse the S3 URI  
    bucket_name, object_key = parse_s3_uri(s3_uri)  

    # Detect the filename  
    filename = get_filename_from_key(object_key)
    logger.debug(f"Detected filename: {filename}")  
    file_extension = filename.split('.')[-1]
    if not file_extension:
        logger.error(f"Unsupported audio file extension. File format: {file_extension} found.")
        raise HTTPException(
            status_code=415,
            detail="Invalid audio file format. Only .wav & .mp3 are allowed."
        )
        
    # Read the audio file from S3 into a variable  
    audio_segment = read_audio_file_from_s3(s3, bucket_name, object_key)
    logger.debug(f"Audio duration: {len(audio_segment)} milliseconds")  
    logger.info(f"File: {filename} has been processed")
    audio_data = audio_segment.export(format=file_extension).read()
        
    return audio_data, file_extension
