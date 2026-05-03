import os
import sys
from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalCustomException
from model.models import *
from langchain.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser

class DocumentAnalyzer:
    """
    Analyzes documents using embedding and LLM models.
    Automatically logs all actions and handles exceptions gracefully.
    """

    def __init__(self):
        pass
    def analyze_metadata(self, document_path):
        pass
