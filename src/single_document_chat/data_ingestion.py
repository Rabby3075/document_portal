
import sys
from pathlib import Path
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalCustomException
from datetime import datetime
import uuid
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from utils.model_loader import ModelLoader

class SingleDocumentIngestor:
    def __init__(self, data_dir: str = "data/single_document", faiss_dir: str = "faiss_index"):
        try:
            self.log = CustomLogger().get_logger(__name__)
            self.data_dir = Path(data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.faiss_dir = Path(faiss_dir)
            self.faiss_dir.mkdir(parents=True, exist_ok=True)
            self.model_loader = ModelLoader()
            self.log.info("SingleDocIngestor initialized successfully.", temp_path = str(self.data_dir), faiss_path = str(self.faiss_dir))

        except Exception as e:
            self.log.error("Failed to initialized SingleDocIngestor", error=str(e))
            raise DocumentPortalCustomException("Initialization error in singleDocIngestor",sys)
        
    def ingest_files(self,uploaded_files):
            """
            Ingests files from a directory and returns a list of documents.
            """
            try:
                documents = []
                for uploaded_file in uploaded_files:
                    unique_filename = f"session_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}_{uuid.uuid4().hex[:8]}"
                    temporary_path = self.data_dir / unique_filename
                    with open (temporary_path, "wb") as f:
                        f.write(uploaded_file.read())
                    self.log.info("File saved successfully.", filename = uploaded_file.name)
                    loader = PyPDFLoader(temporary_path)
                    documents.extend(loader.load())
                self.log.info("Files ingested successfully.", count = len(documents))
                return self._create_retriever(documents)
            
            except Exception as e:
                self.log.error("Failed to initialized Document", error=str(e))
                raise DocumentPortalCustomException("Initialization error in Ingest_file",sys)
        
    
    def _create_retriever(self, documents):
        try:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=300
            )
            doc_chunks = splitter.split_documents(documents)
            self.log.info("Splitter created successfully.", count = len(doc_chunks))
            embedding_model = self.model_loader.load_embedding_model()
            vectorstore = FAISS.from_documents(doc_chunks, embedding_model)
            #save faiss index
            vectorstore.save_local(self.faiss_dir)
            self.log.info("Vectorstore saved successfully.", faiss_path = str(self.faiss_dir))
            retriever = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            self.log.info("Retriever created successfully.", retriever_type = str(type(retriever)))
            return retriever
        except Exception as e:
            self.log.error("Failed to create retriever", error=str(e))
            raise DocumentPortalCustomException("Failed to create retriever",sys)
        


