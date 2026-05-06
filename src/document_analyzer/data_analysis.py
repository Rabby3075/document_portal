import os
import sys
from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalCustomException
from model.models import *
from langchain_core.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser
from prompt.prompt_library import PROPMT_REGISTRY

class DocumentAnalyzer:
    """
    Analyzes documents using embedding and LLM models.
    Automatically logs all actions and handles exceptions gracefully.
    """

    def __init__(self):
        self.log = CustomLogger().get_logger(__name__)
        try:
            self.loader = ModelLoader()
            self.llm = self.loader.load_llm()

            #prepare persar
            self.parser = JsonOutputParser(pydantic_object=Metadata)
            self.fixing_parser = OutputFixingParser.from_llm(parser = self.parser, llm = self.llm)

            #promopt
            self.prompt = PROPMT_REGISTRY["document_analysis"]
            self.log.info("DocumentAnalyzer initialized successfully.")


        except Exception as e:
            self.log.error(f"Failed to initialize DocumentAnalyzer: {e}")
            raise DocumentPortalCustomException(f"Failed to initialize DocumentAnalyzer: {e}", sys)
        
    def analyze_document(self, document_text:str)-> dict:
        """
        Analyze a document's text and extract structured metadata & summary.
        """
        try:
            chain = self.prompt | self.llm | self.fixing_parser
            
            self.log.info("Meta-data analysis chain initialized")

            response = chain.invoke({
                "format_instructions": self.parser.get_format_instructions(),
                "document_text": document_text
            })

            self.log.info("Metadata extraction successful", keys=list(response.keys()))
            
            return response

        except Exception as e:
            self.log.error("Metadata analysis failed", error=str(e))
            raise DocumentPortalCustomException("Metadata extraction failed") from e


    
