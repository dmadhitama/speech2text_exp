from typing import Optional  
from fastapi import UploadFile, HTTPException  
import os
import boto3
import base64
import magic
from io import BytesIO
from pydub import AudioSegment  

from utils.helper import check_audio_duration, get_file_extension_from_mime
from utils.gdrive import read_audio_from_google_drive
from utils.s3 import read_audio_from_s3_bucket

class AudioProcessor:  
    def __init__(
            self, 
            logger,
            audio: Optional[UploadFile], 
            base64_audio: Optional[str], 
            google_drive_url: Optional[str], 
            s3_uri: Optional[str], 
            aws_access_key_id: Optional[str], 
            aws_secret_access_key: Optional[str]
        ):  
        self.logger = logger
        self.audio = audio  
        self.base64_audio = base64_audio  
        self.google_drive_url = google_drive_url  
        self.s3_uri = s3_uri  
        self.aws_access_key_id = aws_access_key_id  
        self.aws_secret_access_key = aws_secret_access_key  
        self.audio_data = None  
        self.file_extension = None  
  
    async def process_audio(self):  
        if self.audio:  
            self.file_extension = self.audio.filename.split(".")[-1].lower()  
            self.audio_data = await self.audio.read()  
        elif self.base64_audio:  
            self._process_base64_audio()  
        elif self.google_drive_url:  
            self._process_google_drive_audio()  
        elif self.s3_uri and self.aws_access_key_id and self.aws_secret_access_key:  
            self._process_s3_audio()  
        else:  
            raise HTTPException(
                status_code=400, 
                detail="No valid audio input provided."
            )  
        self._validate_file_extension()  
        self._convert_audio_format()  
  
    def _process_base64_audio(self):  
        try:  
            self.audio_data = base64.b64decode(self.base64_audio)  
            mime = magic.Magic(mime=True)  
            mime_type = mime.from_buffer(self.audio_data)  
            self.file_extension = get_file_extension_from_mime(mime_type)  
            if not self.file_extension:  
                self.logger.error(f"Unsupported audio file extension. File format: {self.file_extension} found.")  
                raise HTTPException(
                    status_code=415, 
                    detail="Invalid audio file format. Only .wav & .mp3 are allowed."
                )  
        except Exception as e: 
            err_msg = f"Invalid base64 audio data. {str(e)}"
            self.logger.error(err_msg)
            raise HTTPException(
                status_code=400, 
                detail=err_msg
            )  
  
    def _process_google_drive_audio(self):  
        self.audio_data, self.file_extension = read_audio_from_google_drive(self.google_drive_url)  
  
    def _process_s3_audio(self):  
        if os.environ.get("AWS_ACCESS_KEY_ID") is None:  
            os.environ["AWS_ACCESS_KEY_ID"] = self.aws_access_key_id  
        if os.environ.get("AWS_SECRET_ACCESS_KEY") is None:  
            os.environ["AWS_SECRET_ACCESS_KEY"] = self.aws_secret_access_key  
        s3 = boto3.client('s3')  
        self.audio_data, self.file_extension = read_audio_from_s3_bucket(s3, self.s3_uri) 
  
    def _validate_file_extension(self):  
        allowed_extensions = {"wav", "mp3"}  
        if self.file_extension not in allowed_extensions:  
            self.logger.error("Invalid file format. Only .wav & .mp3 are allowed.")
            raise HTTPException(
                status_code=415, 
                detail="Invalid audio file format. Only .wav & .mp3 are allowed."
            )  
  
    def _convert_audio_format(self):  
        audio_segment = AudioSegment.from_file(BytesIO(self.audio_data))  
        audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)  
        self.audio_data = audio_segment.export(format=self.file_extension).read()  
        self.audio_duration = audio_segment.duration_seconds  
        check_audio_duration(self.audio_duration) 