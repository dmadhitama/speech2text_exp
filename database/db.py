from sqlalchemy import create_engine, Column, Integer, String, Float, MetaData, Table, inspect  
from sqlalchemy.orm import sessionmaker  
from sqlalchemy.exc import SQLAlchemyError

from fastapi import HTTPException
from loguru import logger

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
        raise HTTPException(
            status_code=420, 
            detail="Error occurred while inserting data."
        )
    finally:  
        session.close() 