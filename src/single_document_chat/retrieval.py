import sys
import os
from dotenv import load_dotenv
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.vectorstores import FAISS
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from utils.model_loader import ModelLoader
from prompt.prompt_library import PROPMT_REGISTRY
from model.models import PromptTypes
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalCustomException

class ConversationalRAG:
    def __init__(self, session_id: str, retriever):
        try:
            self.log = CustomLogger().get_logger(__name__)
        except Exception as e:
            self.log.error("Error initializing conversational rag", error = str(e), session_id = session_id)
            raise DocumentPortalCustomException("Failed to initialize Conversational RAG", sys)
    
    def _load_llm(self):
        try:
            pass
        except Exception as e:
            self.log.error("Error loading llm", error = str(e))
            raise DocumentPortalCustomException("Failed to load llm", sys)
    
    def _get_session_history(self,session_id:str):
        try:
            pass
        except Exception as e:
            self.log.error("Error getting session history", session_id = session_id ,error = str(e))
            raise DocumentPortalCustomException("Failed to get session history", sys)
    
    def load_retriever_from_faiss(self):
        try:
            pass
        except Exception as e:
            self.log.error("Error loading retriever from faiss", error = str(e))
            raise DocumentPortalCustomException("Failed to load retriever from faiss", sys)
    
    def invoke(self):
        try:
            pass
        except Exception as e:
            self.log.error("Error invoking", error = str(e))
            raise DocumentPortalCustomException("Failed to invoke", sys)
        
    