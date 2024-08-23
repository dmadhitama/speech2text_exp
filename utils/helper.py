def get_file_extension_from_mime(mime_type):  
    if mime_type == "audio/wav" or mime_type == "audio/x-wav":  
        return "wav"  
    elif mime_type == "audio/mpeg":  
        return "mp3"  
    else:  
        return None 