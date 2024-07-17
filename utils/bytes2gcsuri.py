import wave  
import io  
from google.cloud import storage  
import uuid  
  
def upload_wav_to_gcs(
        audio_bytes, 
        sample_rate, 
        num_channels, 
        bucket_name, 
        destination_blob_name
    ) -> str:  
    # Create a wave file from the bytes input  
    with io.BytesIO() as wav_io:  
        with wave.open(wav_io, 'wb') as wav_file:  
            wav_file.setnchannels(num_channels)  
            wav_file.setsampwidth(2)  # Assuming 16-bit audio  
            wav_file.setframerate(sample_rate)  
            wav_file.writeframes(audio_bytes)  
          
        # Reset the buffer's position to the beginning  
        wav_io.seek(0)  
          
        # Initialize a client  
        storage_client = storage.Client()  
          
        # Get the bucket  
        bucket = storage_client.bucket(bucket_name)  
          
        # Create a blob  
        blob = bucket.blob(destination_blob_name)  
          
        # Upload the file to GCS  
        blob.upload_from_file(wav_io, content_type='audio/wav')  
        
        # Return the GCS URI  
        gcs_uri = f'gs://{bucket_name}/{destination_blob_name}'  
        return gcs_uri  