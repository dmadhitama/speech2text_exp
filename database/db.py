from sqlalchemy import create_engine, Column, Integer, String, Float, MetaData, Table, inspect  
from sqlalchemy.orm import sessionmaker  
from sqlalchemy.exc import SQLAlchemyError

import datetime
from fastapi import HTTPException
from typing import Dict

from utils.helper import init_logger, convert_time_to_gmt7
from settings import CopilotSettings  

config = CopilotSettings()
# Logger initialization
logger = init_logger(config.LOG_PATH)

def connect_and_insert(
        database, 
        user, 
        password, 
        host, 
        port, 
        row_data
    ):  
    """
    This function is used to connect to the database and insert the data.
    Args:
        database (str): The name of the database.
        user (str): The username to connect to the database.
        password (str): The password to connect to the database.
        host (str): The host to connect to the database.
        port (str): The port to connect to the database.
        row_data (tuple): The data to insert into the database.
    """
    # Create an engine and connect to the PostgreSQL database  
    engine = create_engine(f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}')  
      
    # Create a metadata instance  
    metadata = MetaData()  
  
    # Define the table  
    soap_stt = Table('soap_stt', metadata,  
        Column('id', Integer, primary_key=True, autoincrement=True),  
        Column('datetime', String),  
        Column('audio_duration', Float),  
        Column('token_prompt', Integer),  
        Column('token_completion', Integer),  
        Column('token_total', Integer),  
        Column('transcript', String),  
        Column('llm_response', String)  
    )  
      
    # Check if the table exists, create if not  
    inspector = inspect(engine)  
    if not inspector.has_table('soap_stt'):  
        metadata.create_all(engine)  
        logger.info("Table soap_stt created.")  
    else:  
        logger.info("Table soap_stt already exists.")

    logger.info("Connection to database established.")
      
    # Create a session  
    Session = sessionmaker(bind=engine)  
    session = Session()  
  
    try:  
        # Insert data  
        insert_stmt = soap_stt.insert().values(  
            datetime=row_data[0],  
            audio_duration=row_data[1],  
            token_prompt=row_data[2],  
            token_completion=row_data[3],  
            token_total=row_data[4],  
            transcript=row_data[5],  
            llm_response=row_data[6]  
        )  
        session.execute(insert_stmt)  
        session.commit()  
        logger.info("Data inserted.")  
    except SQLAlchemyError as e:  
        session.rollback()  
        logger.error(f"Error occurred: {e}")
    finally:  
        session.close() 

class MetadataSaver:  
    """
    This class is used to save the metadata to the database.
    Args:
        audio_duration (float): The duration of the audio.
        metadata (Dict): The metadata from the STT.
        transcript (str): The transcript from the STT.
        soap_note (str): The SOAP note from the LLM.
    """
    def __init__(
            self, 
            audio_duration: float, 
            transcript: str, 
            metadata: Dict = None, 
            soap_note: str = None
        ):  
        self.audio_duration = audio_duration  
        self.metadata = metadata  
        self.transcript = transcript  
        self.soap_note = soap_note  

    def update_metadata(self, new_metadata):
        self.metadata = new_metadata

    def update_soap_note(self, new_soap_note):
        self.soap_note = new_soap_note
  
    def save_metadata(self): 
        if self.metadata is not None:
            token_usage = self.metadata.get('token_usage', self.metadata)
            token_prompt = token_usage.get('prompt_tokens') or token_usage.get('input_tokens', 0)
            token_completion = token_usage.get('completion_tokens') or token_usage.get('output_tokens', 0)
            token_total = token_usage.get('total_tokens', token_prompt + token_completion)
        else:
            token_prompt = 0
            token_completion = 0
            token_total = 0
        
        logger.debug(f"Token prompt: {token_prompt}")
        logger.debug(f"Token completion: {token_completion}")
        logger.debug(f"Token total: {token_total}")
        row_data = (  
            str(convert_time_to_gmt7(datetime.datetime.now())),  
            self.audio_duration,  
            token_prompt,  
            token_completion,  
            token_total,  
            self.transcript,  
            self.soap_note  
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
            raise HTTPException(
                status_code=500, 
                detail="Error saving metadata information to database."
            )  