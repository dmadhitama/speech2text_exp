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
        # raise HTTPException(
        #     status_code=420, 
        #     detail="Error occurred while inserting data."
        # )
    finally:  
        session.close() 

class MetadataSaver:  
    def __init__(
            self, 
            audio_duration: float, 
            metadata: Dict, 
            transcript: str, 
            soap_note: str
        ):  
        self.audio_duration = audio_duration  
        self.metadata = metadata  
        self.transcript = transcript  
        self.soap_note = soap_note  
  
    def save_metadata(self):  
        row_data = (  
            str(convert_time_to_gmt7(datetime.datetime.now())),  
            self.audio_duration,  
            self.metadata.get('token_usage', {}).get('prompt_tokens', 0),  
            self.metadata.get('token_usage', {}).get('completion_tokens', 0),  
            self.metadata.get('token_usage', {}).get('total_tokens', 0),  
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
            raise HTTPException(status_code=500, detail="Error saving metadata information to database.")  