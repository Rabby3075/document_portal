import os
import sys
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
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

    MAX_DIRECT_CHARS = 24000
    CHUNK_SIZE = 12000
    CHUNK_OVERLAP = 1000

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
            self.summary_prompt = PROPMT_REGISTRY["document_analysis_summary_prompt"]
            self.summary_chain = self.summary_prompt | self.llm | StrOutputParser()
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
            analysis_text = self._prepare_document_text(document_text)

            response = chain.invoke({
                "format_instructions": self.parser.get_format_instructions(),
                "document_text": analysis_text
            })

            self.log.info("Metadata extraction successful", keys=list(response.keys()))
            
            return response

        except Exception as e:
            self.log.error("Metadata analysis failed", error=str(e))
            raise DocumentPortalCustomException("Metadata extraction failed", sys) from e

    def _prepare_document_text(self, document_text: str) -> str:
        if len(document_text) <= self.MAX_DIRECT_CHARS:
            return document_text

        chunks = self._chunk_text(document_text)
        self.log.info("Document is large, summarizing chunks first", chunks=len(chunks), characters=len(document_text))

        summaries = []
        for index, chunk in enumerate(chunks, start=1):
            summary = self.summary_chain.invoke({
                "chunk_number": index,
                "total_chunks": len(chunks),
                "document_chunk": chunk
            })
            summaries.append(f"Chunk {index} summary:\n{summary}")

        combined_summary = "\n\n".join(summaries)
        if len(combined_summary) <= self.MAX_DIRECT_CHARS:
            return combined_summary

        self.log.info("Combined summaries are still large, condensing once more", characters=len(combined_summary))
        return self.summary_chain.invoke({
            "chunk_number": 1,
            "total_chunks": 1,
            "document_chunk": combined_summary
        })

    def _chunk_text(self, text: str) -> list[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP
        )
        return splitter.split_text(text)


    
