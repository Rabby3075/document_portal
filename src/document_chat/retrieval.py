import os,sys

from typing import List, Optional
from operator import itemgetter

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import FAISS

from utils.model_loader import ModelLoader
from exception.custom_exception import DocumentPortalCustomException
from logger.custom_logger import CustomLogger
from prompt.prompt_library import PROMPT_REGISTRY
from model.models import PromptTypes
class DocumentConversationalRag:
    def __init__(self, session_id: str, retriever = None):
        try:
            self.log = CustomLogger().get_logger(__name__)
            self.session_id = session_id
            self.llm = self._load_llm()
            self.contextualize_prompt = PROMPT_REGISTRY[PromptTypes.CONTEXTUALIZE_QUESTION.value]
            self.qa_prompt = PROMPT_REGISTRY[PromptTypes.CONTEXT_QA.value]
            self.retriever = retriever
            self.chain = None
            if retriever is not None:
                self._build_lcel_chain()
            self.log.info("Initialized MultiDocConversationalRag", session_id=session_id, has_retriever=retriever is not None)
        except Exception as e:
            self.log.error("Failed to initialize MultiDocConversationalRag", error=str(e))
            raise DocumentPortalCustomException("Initialization error in MultiDocConversationalRag", sys)
    def load_retriever_from_faiss(self, index_path: str):
        try:
            embeddings = ModelLoader().load_embedding_model()
            if not os.path.isdir(index_path):
                raise FileNotFoundError(f"FAISS index directory not found: {index_path}")

            vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
            self.retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
            self._build_lcel_chain()
            self.log.info("Loaded retriever from FAISS index", index_path=index_path)
            return self.retriever

        except Exception as e:
            self.log.error("Failed to load retriever from FAISS", error=str(e))
            raise DocumentPortalCustomException("Error loading retriever from FAISS", sys)
    def _load_llm(self):
        try:
            llm = ModelLoader().load_llm()
            self.log.info("LLM loaded successfully", class_name=llm.__class__.__name__)
            return llm
        except Exception as e:
            self.log.error("Error loading LLM via ModelLoader", error=str(e))
            raise DocumentPortalCustomException("Failed to load LLM", sys)
    def invoke(self, user_input: str, chat_history: Optional[List[BaseMessage]] = None)->str:
        try:
            chat_history = chat_history or []
            payload={"input": user_input, "chat_history": chat_history}
            answer = self.chain.invoke(payload)
            if not answer:
                self.log.warning("Empty answer received", session_id=self.session_id)
                return "No answer."
            self.log.info("Chain invoked successfully", session_id=self.session_id, user_input=user_input, answer_preview=answer)
            return answer
            
        except Exception as e:
            self.log.error("Failed to invoke MultiDocConversationalRag", error=str(e))
            raise DocumentPortalCustomException("Failed to invoke MultiDocConversationalRag", sys)
    @staticmethod
    def _formate_documents(docs):
        return "\n\n".join(doc.page_content for doc in docs)
    def _build_lcel_chain(self):
        try:
            #rewrite the question using chat history
            question_rewriter = (
                {"input": itemgetter("input"), "chat_history": itemgetter("chat_history")}
                | self.contextualize_prompt
                | self.llm
                | StrOutputParser()
            )
            #retireve docs for rewritten 
            retrieve_docs = question_rewriter |self.retriever | self._formate_documents
            # feed context, input, chat history to generate answer
            self.chain = ({
                "context": retrieve_docs, 
                "input": itemgetter("input"),
                "chat_history": itemgetter("chat_history")
            }
            | self.qa_prompt
            | self.llm
            | StrOutputParser()
            )
            self.log.info("LCEL graph built successfully", session_id=self.session_id)
    
        except Exception as e:
            self.log.error("Failed to build LCEL chain", error=str(e))
            raise DocumentPortalCustomException("Error building LCEL chain", sys)