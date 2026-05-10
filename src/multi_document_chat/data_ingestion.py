import sys
import uuid
from pathlib import Path
from datetime import datetime
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalCustomException
from utils.model_loader import ModelLoader
class MultiDocumentIngestion:
    supported_file_types = {'.pdf', '.docx', '.txt'}
    def __init__(self, temp_path:str = 'data/multi_doc_chat', faiss_path:str = 'faiss_index', session_id:str = None):
        try:
            self.log = CustomLogger().get_logger(__name__)
            self.temp_path = Path(temp_path)
            self.temp_path.mkdir(parents=True, exist_ok=True)
            self.faiss_path = Path(faiss_path)
            self.faiss_path.mkdir(parents=True, exist_ok=True)

            #sessions path 
            self.session_id = session_id or f"session_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}_{uuid.uuid4().hex[:8]}"
            self.session_temp_path = self.temp_path / self.session_id
            self.session_temp_path.mkdir(parents=True, exist_ok=True)
            self.session_faiss_path = self.faiss_path / self.session_id
            self.session_faiss_path.mkdir(parents=True, exist_ok=True)
            self.model_loader = ModelLoader()
            self.log.info("Multi Document Ingestor initialized", temp_path=str(self.temp_path), faiss_path=str(self.faiss_path), session_id=self.session_id, session_temp_path=str(self.session_temp_path), session_faiss_path=str(self.session_faiss_path))

        except Exception as e:
            self.log.error("Failed to initialize MultiDocIngestor", error=str(e))
            raise DocumentPortalCustomException("Initialization error in MultiDocIngestor", sys)
    def ingest_files(self, uploaded_files):
        try:
            documents = []
            for uploaded_file in uploaded_files:
                file_extension = Path(uploaded_file.name).suffix.lower()
                if not file_extension in self.supported_file_types:
                    self.log.warning("Unsupported file type, skipping file", file=uploaded_file.name)
                    continue
                unique_filename = f"{uuid.uuid4().hex[:8]}{file_extension}"
                temp_path = self.session_temp_path / unique_filename
                with open(temp_path, "wb") as f_out:
                    f_out.write(uploaded_file.read())
                self.log.info("File saved for ingestion", filename=uploaded_file.name, file_path=str(temp_path))

                if file_extension == '.pdf':
                    loader = PyPDFLoader(str(temp_path))
                elif file_extension == '.docx':
                    loader = Docx2txtLoader(str(temp_path))
                elif file_extension == '.txt':
                    loader = TextLoader(str(temp_path),encoding="utf-8")
                else:
                    self.log.warning("Unsupported file type, skipping file", file=uploaded_file.name)
                    continue

                docs = loader.load()
                documents.extend(docs)
                if not documents:
                    self.log.error("Document loading failed", error="No documents loaded", uploaded_file = uploaded_file.name)
                    raise DocumentPortalCustomException("Error during file ingestion", sys)

            self.log.info("Files loaded", count=len(documents))
            return self._create_retriever(documents)
            

        except Exception as e:
            self.log.error("Document ingestion failed", error=str(e))
            raise DocumentPortalCustomException("Error during file ingestion", sys)
    def _create_retriever(self, documents):
        try:
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=300)
            chunks = splitter.split_documents(documents)
            self.log.info("Documents split into chunks", count=len(chunks))
            
            embeddings = self.model_loader.load_embedding_model()
            vectorstore = FAISS.from_documents(documents=chunks, embedding=embeddings)
            
            # save FAISS index
            vectorstore.save_local(str(self.session_faiss_path))
            self.log.info("FAISS index created and saved", faiss_path=str(self.session_faiss_path))
            
            retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
            self.log.info("Retriever created successfully", retriever_type=str(type(retriever)))
            return retriever 
        except Exception as e:
            self.log.error("Retriever creation failed", error=str(e))
            raise DocumentPortalCustomException("Error creating FAISS retriever", sys)
