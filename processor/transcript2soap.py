from prompts import (
    sys_prompt, 
    sys_prompt_2,
    sys_prompt_mod,
    sys_prompt_structured_output,
)
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from fastapi import HTTPException
from utils.parse_soap import parse_soap_note
from llms.groq_llm import groq
from utils.helper import init_logger
from settings import CopilotSettings  
import re


config = CopilotSettings()

# Logger initialization
logger = init_logger(config.LOG_PATH)

class Transcript2SOAP:  
    """
    This class is used to generate a SOAP note from a transcript.
    Args:
        transcript (str): The transcript from the STT.
        model (str): The model to use for the LLM.
    """
    def __init__(
            self, 
            transcript: str,
            model: str = "gemma2-9b-it",
        ):  
        self.transcript = transcript
        self.model = model
  
    def generate_soap(self):  
        system_message = sys_prompt_mod.system_message  
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_message), 
                ("human", "{question}")
            ]
        )  
        llm = groq(model=self.model)  
        chain = prompt | llm  
        try:  
            response = chain.invoke(
                {"question": self.transcript}
            )  
        except Exception as e:  
            msg_err =  f"Error processing SOAP response. {str(e)}"
            logger.error(msg_err)
            raise HTTPException(
                status_code=422, 
                detail=msg_err
            )  
        if not isinstance(response, str):  
            self.soap_note = response.content  
            self.metadata = response.response_metadata  
        else:  
            self.soap_note = response  
            self.metadata = {}  
  
    def generate_soap_with_structured_output_parser(self):  
        response_schemas = [
            ResponseSchema(
                name="subjective", 
                description="This section captures the patient's personal experiences, feelings, and perceptions about their health condition. It includes the chief complaint (CC), history of present illness (HPI), past medical history (PMH), family history (FH), social history (SH), and review of systems (ROS). Put null value if there is no medical information in the transcript."
            ),
            ResponseSchema(
                name="objective", 
                description="This section includes measurable, observable, and verifiable data collected by the healthcare provider. It encompasses physical examination findings, vital signs, laboratory results, imaging studies, and other diagnostic data. Put null value if there is no medical information in the transcript.",
            ),
            ResponseSchema(
                name="assessment", 
                description="This section provides the healthcare provider's medical diagnosis or differential diagnoses based on the subjective and objective information gathered. It includes the clinician's interpretation of the data and the rationale for the diagnosis. Put null value if there is no medical information in the transcript.",
            ),
            ResponseSchema(
                name="plan", 
                description="This section outlines the proposed management and treatment plan for the patient. It includes medications, therapies, lifestyle modifications, follow-up appointments, patient education, and any referrals to specialists. Put null value if there is no medical information in the transcript.",
            ),
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

        format_instructions = output_parser.get_format_instructions()
        prompt = PromptTemplate(
            template="{system_message}\n{question}\n{format_instructions}",
            input_variables=["system_message", "question"],
            partial_variables={"format_instructions": format_instructions},
        )

        llm = groq(model=self.model)  
        intermediate_chain = prompt | llm
        try:
            intermediate_response = intermediate_chain.invoke(
                {
                    "question": self.transcript,
                    "system_message": sys_prompt_structured_output.system_message
                }
            )
            # Extract the content from the AIMessage
            if hasattr(intermediate_response, 'content'):
                intermediate_content = intermediate_response.content
            else:
                intermediate_content = str(intermediate_response)
            
            # remove the trailing comma that causes parsing error
            intermediate_content = re.sub(r',\s*}', '}', intermediate_content)  
            logger.debug(intermediate_content)

            # Parse the response
            logger.debug("Parsing the LLM response")
            response = output_parser.parse(intermediate_content)
            logger.debug(response)

            # Check if any of the keys in the response dictionary contain None
            if any(value is None for value in response.values()):
                raise ValueError("SOAP note contains invalid content.")
    
            self.response = response

        except Exception as e: 
            msg_err =  f"Error processing SOAP response. {str(e)}\n"
            msg_err += f"It might be caused by non-medical content or information in your audio recording."
            logger.error(msg_err)
            raise HTTPException(
                status_code=422, 
                detail=msg_err
            )  
        if not isinstance(response, str):  
            self.soap_note = intermediate_content 
            self.metadata = intermediate_response.usage_metadata 
        else:  
            self.soap_note = response  
            self.metadata = {}  
  
    def parse_soap(self):  
        try:  
            return parse_soap_note(self.soap_note)  
        except Exception as e:  
            msg_err =  f"Error processing SOAP response. {str(e)}\n"
            msg_err += f"It might be caused by non-medical content or information in your audio recording."
            logger.error(msg_err)
            raise HTTPException(
                status_code=422, 
                detail=msg_err
            )  