import sys
import os
from dotenv import load_dotenv
import streamlit as st
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
        """
        Initialize the Conversational RAG.

        Args:
            session_id (str): The session ID.
            retriever: The retriever to use for the RAG.
        """
        try:
            self.log = CustomLogger().get_logger(__name__)
            self.session_id = session_id
            self.retriever = retriever
            self.session_history_store: dict[str, BaseChatMessageHistory] = {}
            self.llm = self._load_llm()
            self.contextualize_prompt = PROPMT_REGISTRY[PromptTypes.CONTEXTUALIZE_QUESTION.value]
            self.qa_prompt = PROPMT_REGISTRY[PromptTypes.CONTEXT_QA.value]
            self.history_aware_retriever = create_history_aware_retriever(
                self.llm, self.retriever, self.contextualize_prompt
                )
            self.log.info("Conversational RAG initialized successfully.", session_id = session_id)
            self.qa_chain = create_stuff_documents_chain(
                self.llm,  self.qa_prompt
            )
            self.rag_chain = create_retrieval_chain(self.history_aware_retriever, self.qa_chain)
            self.log.info("Conversational RAG initialized successfully.", session_id = session_id)
            self.final_chain = RunnableWithMessageHistory(
                self.rag_chain,
                self._get_session_history,
                input_messages_key="input",
                history_messages_key="chat_history",
                output_messages_key="answer",
            )
            self.log.info("Created RunnableWithMessageHistory successfully.", session_id = session_id)
        except Exception as e:
            self.log.error("Error initializing conversational rag", error = str(e), session_id = session_id)
            raise DocumentPortalCustomException("Failed to initialize Conversational RAG", sys)
    
    def _load_llm(self):
        try:
            llm = ModelLoader().load_llm()
            self.log.info("Loaded llm successfully.", class_name = llm.__class__.__name__)
            return llm
        except Exception as e:
            self.log.error("Error loading llm", error = str(e))
            raise DocumentPortalCustomException("Failed to load llm", sys)
    
    def _get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        try:
            if session_id not in self.session_history_store:
                self.session_history_store[session_id] = ChatMessageHistory()
                self.log.info("Created new session history.", session_id=session_id)
            return self.session_history_store[session_id]
        except Exception as e:
            self.log.error("Error getting session history", session_id=session_id, error=str(e))
            raise DocumentPortalCustomException("Failed to get session history", sys)
    
    def load_retriever_from_faiss(self, index_path: str):
        try:
            embeddings = ModelLoader().load_embeddings()
            if not os.path.isdir(index_path):
                raise FileNotFoundError(f"Index not found at {index_path}")
            vectorstore = FAISS.load_local(index_path, embeddings)
            self.log.info("Loaded retriever from faiss successfully.", index_path = index_path)
            return vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
        except Exception as e:
            self.log.error("Error loading retriever from faiss", error = str(e))
            raise DocumentPortalCustomException("Failed to load retriever from faiss", sys)
    
    def invoke(self, user_input: str):
        try:
            response = self.final_chain.invoke(
                {"input": user_input},
                config = {"configurable": {"session_id": self.session_id}}
            )
            answer = response.get("answer", "No Answer Found")
            if not answer:
                self.log.warning("No Answer Found.", session_id = self.session_id)
            self.log.info("Invoked successfully.", session_id = self.session_id, user_input = user_input, answer = answer)
            return answer
        except Exception as e:
            self.log.error("Error invoking", error = str(e))
            raise DocumentPortalCustomException("Failed to invoke", sys)
        
    