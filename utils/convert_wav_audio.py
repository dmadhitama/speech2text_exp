import io  
from pydub import AudioSegment  
  
def convert_audio_from_file(input_file, target_sample_rate, target_channels):
    # Load the audio from the uploaded file
    audio = AudioSegment.from_file(input_file, format="wav") 
      
    # Set the target sample rate and number of channels  
    audio = audio.set_frame_rate(target_sample_rate)  
    audio = audio.set_channels(target_channels)  
      
    # Export the modified audio to bytes  
    output_io = io.BytesIO()  
    audio.export(output_io, format="wav")  
      
    # # Get the bytes from the BytesIO object  
    # output_bytes = output_io.getvalue()  
      
    # return output_bytes
    
    # Reset the cursor of the BytesIO object to the beginning  
    output_io.seek(0)  
      
    return output_io 
  
def convert_audio_from_bytes(input_bytes, target_sample_rate, target_channels):
    # Create a BytesIO object from the input bytes  
    input_io = io.BytesIO(input_bytes)  
      
    # Load the audio from bytes  
    audio = AudioSegment.from_wav(input_io)  
      
    # Set the target sample rate and number of channels  
    audio = audio.set_frame_rate(target_sample_rate)  
    audio = audio.set_channels(target_channels)  
      
    # Export the modified audio to bytes  
    output_io = io.BytesIO()  
    audio.export(output_io, format="wav")  
      
    # Get the bytes from the BytesIO object  
    output_bytes = output_io.getvalue()  
      
    return output_bytes  