import sys
from dotenv import load_dotenv
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalCustomException
import pandas as pd
from model.models import *
from prompt.prompt_library import PROPMT_REGISTRY
from utils.model_loader import ModelLoader
from langchain_core.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser

class DocumentComparatorLLM:

    def __init__(self):
        load_dotenv()
        self.log = CustomLogger().get_logger(__name__)
        self.loader = ModelLoader()
        self.llm = self.loader.load_llm()
        self.parser = JsonOutputParser(pydantic_object=SummaryResponse)
        self.fixing_parser = OutputFixingParser.from_llm(parser = self.parser, llm = self.llm)
        self.prompt = PROPMT_REGISTRY["document_comparison"]
        self.chain = self.prompt | self.llm | self.fixing_parser

    def compare_document(self, combined_docs:str)->pd.DataFrame:
        try:
            inputs = {
                "combined_docs": combined_docs,
                "format_instruction": self.parser.get_format_instructions()
            }
            self.log.info("Starting document comparison", inputs=inputs)
            response = self.chain.invoke(inputs)
            self.log.info("Document comparison completed successfully", response=response)
            return self._formate_response(response)
        except Exception as e:
            self.log.error("Document comparison failed", error=str(e))
            raise DocumentPortalCustomException("Document comparison failed",sys) from e

    def _formate_response(self, response: list[dict])->pd.DataFrame:
        try:
            df = pd.DataFrame(response)
            self.log.info("Formating response into DataFrame", dataframe = df)
            return df
        except Exception as e:
            self.log.error("Response formating failed", error=str(e))
            raise DocumentPortalCustomException("Response formating failed",sys) from e
