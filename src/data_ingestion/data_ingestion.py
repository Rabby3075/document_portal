from __future__ import annotations
import os,sys,json,uuid,hashlib,shutil, fitz
from pathlib import Path
from datetime import datetime
from typing import Iterable, List, Optional, Dict, Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_community.vectorstores import FAISS

from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalCustomException

from utils.file_io import save_uploaded_files,generate_session_id
from utils.document_ops import load_documents, concat_for_comparison, concat_for_analysis

supporting_extension = {'.pdf', '.docx', '.txt'}
class FaissManager:
    def __init__(self, index_dir: Path, model_loader: Optional[ModelLoader] = None):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.index_dir / "meta.json"
        self._meta: Dict[str, Any] = {"rows": {}}
        if self.meta_path.exists():
            try:
                self._meta = json.loads(self.meta_path.read_text(encoding="utf-8")) or {"rows": {}}
            except Exception as e:
                self._meta = {"rows": {}}
        self.model_loader = model_loader or ModelLoader()
        self.embedding_model = self.model_loader.load_embedding_model()
        self.vs: Optional[FAISS] = None
    def _exist(self)->bool:
        return (self.index_dir / "index.faiss").exists() and (self.index_dir / "index.pkl").exists()
    @staticmethod
    def _fingerprint(text:str, md: Dict[str, Any])->str:
        src = md.get("source") or md.get("file_path")
        rid = md.get("id")
        if src is not None:
            return f"{src}::{'' if rid is None else rid}"
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    def _save_meta(self):
        self.meta_path.write_text(json.dumps(self._meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_or_create(self,texts:Optional[List[str]]=None, metadatas: Optional[List[dict]] = None):
        ## if we running first time then it will not go in this block
        if self._exist():
            self.vs = FAISS.load_local(
                str(self.index_dir),
                embeddings=self.embedding_model,
                allow_dangerous_deserialization=True,
            )
            return self.vs
         
        if not texts:
            raise DocumentPortalCustomException("No existing FAISS index and no data to create one", sys)
        self.vs = FAISS.from_texts(texts=texts, embedding=self.embedding_model, metadatas=metadatas or [])
        self.vs.save_local(str(self.index_dir))
        return self.vs
      

    def add_documents(self, docs: List[Document]):
        if self.vs is None:
            raise RuntimeError("Call load_or_create() before add_documents_idempotent()")
        new_docs: List[Document] = []
        for d in docs:
            key = self._fingerprint(d.page_content, d.metadata or {})
            if key in self._meta["rows"]:
                continue
            self._meta["rows"][key] = True
            new_docs.append(d)
        if new_docs:
            self.vs.add_documents(new_docs)
            self.vs.save_local(str(self.index_dir))
            self._save_meta()
        return len(new_docs)

class DocumentHandler:
    def __init__(self, data_dir: Optional[str] = None, session_id: Optional[str] = None):
        self.log = CustomLogger().get_logger(__name__)
        self.data_dir = data_dir or os.getenv("data_storage_path", os.path.join(os.getcwd(), "data", "document_analysis"))
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}_{uuid.uuid4().hex[:8]}"
        #create base session directory
        self.session_path = os.path.join(self.data_dir, self.session_id)
        os.makedirs(self.session_path, exist_ok=True)
        self.log.info("DocumentHandler initialized", session_id=self.session_id, session_path=self.session_path)
    def save_pdf(self, uploaded_file):
        try:
            filename = os.path.basename(uploaded_file.name)
            #checking if the uploaded file is a PDF
            if not filename.lower().endswith('.pdf'):
                raise ValueError("Uploaded file is not a PDF")
            save_path = os.path.join(self.session_path, filename) #save with original filename, can be changed to unique if needed
            
            with open(save_path, "wb") as f: #write the uploaded file to disk
                f.write(uploaded_file.getbuffer()) #getbuffer() is used to read the file content as bytes
            self.log.info("PDF saved successfully", file = filename, file_path=save_path, session_id = self.session_id)
            return save_path
        except Exception as e:
            self.log.error(f"Failed to save PDF: {e}")
            raise DocumentPortalCustomException(f"Failed to save PDF: {e}", sys)
    def read_pdf(self, file_path:str):
        try:
            if not file_path:
                raise ValueError("file_path is required to read a PDF")

            text_chunks = []
            with fitz.open(file_path) as doc:
                for page_num, page in enumerate(doc, start=1):
                    text_chunks.append(f"\n--- Page {page_num} ---\n{page.get_text()}")
            text = "\n".join(text_chunks)

            self.log.info("PDF read successfully", pdf_path=file_path, session_id=self.session_id, pages=len(text_chunks))
            return text
        except Exception as e:
            self.log.error(f"Error reading PDF: {e}")
            raise DocumentPortalCustomException("Error reading PDF", sys) from e

class DocumentComparator:
    def __init__(self, data_dir: Optional[str] = None, session_id: Optional[str] = None):
        self.log = CustomLogger().get_logger(__name__)
        self.data_dir = Path(data_dir or os.path.join(os.getcwd(), "data", "document_compare"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or generate_session_id()
        self.session_path = self.data_dir / self.session_id
        os.makedirs(self.session_path, exist_ok=True)
    def save_uploaded_files(self, reference_file:str, actual_file:str):
        try:
            # check if the uploaded files already exist in the data directory, if yes delete them before saving new ones
            self.delete_existing_files()
            self.log.info("Existing files deleted successfully, ready to save new uploaded files.")
            reference_path = self.session_path / reference_file.name
            actual_path = self.session_path / actual_file.name
            for fobj, out in ((reference_file, reference_path), (actual_file, actual_path)):
                if not fobj.name.lower().endswith('.pdf') :
                    raise ValueError("Both uploaded files must be PDFs")

                with open(out, "wb") as f: #write the uploaded file to disk
                    if hasattr(fobj, "read"):
                        f.write(fobj.read())
                    else:
                        f.write(fobj.getbuffer())
                self.log.info("PDF saved successfully", file = fobj.name, file_path=out, session_id = self.session_id)
            return reference_path, actual_path

            

        except Exception as e:
            self.log.error("Failed to save uploaded files", error=str(e))
            raise DocumentPortalCustomException("Failed to save uploaded files", sys) from e
    
    def read_uploaded_file(self, file_path:Path)->str:
        try:
            with fitz.open(file_path) as doc:
                if doc.is_encrypted:
                    raise ValueError("PDF is encrypted and cannot be read")
                
                all_text = []
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    text = page.get_text() # Extract text from the page
                    if text.strip(): # Check if the extracted text is not empty
                        all_text.append(f"\n--- Page {page_num + 1} ---\n{text}")
            self.log.info("PDF read successfully", file_path=str(file_path), pages=len(all_text))
            return "\n".join(all_text)
        except Exception as e:
            self.log.error(f"Error reading PDF: {e}")
            raise DocumentPortalCustomException("Error reading PDF", sys) from e
    def combine_document(self):
        try:
            content_dict = {}
            doc_parts = []
            for filename in sorted(self.session_path.iterdir()):
                if filename.is_file() and filename.suffix.lower() == ".pdf":
                    content_dict[filename.name] = self.read_uploaded_file(filename)
            for filename, content in content_dict.items():
                doc_parts.append(f"Document: {filename}\nContent:\n{content}")
            combined_text = "\n".join(doc_parts)
            self.log.info("Documents combined successfully", count = len(content_dict))
            return combined_text
        except Exception as e:
            self.log.error("Failed to combine documents", error=str(e))
            raise DocumentPortalCustomException("Failed to combine documents", sys) from e
    def clean_old_session(self, keep_latest: int = 3):
        try:
            session_folders = sorted(
                [f for f in self.data_dir.iterdir() if f.is_dir()],
                reverse=True
            )
            for folder in session_folders[keep_latest:]:
                for file in folder.iterdir():
                    file.unlink()
                folder.rmdir()
                self.log.info("Old session folder deleted", path=str(folder))

        except Exception as e:
            self.log.error("Error cleaning old sessions", error=str(e))
            raise DocumentPortalCustomException("Error cleaning old sessions", sys)
    def delete_existing_files(self):
        try:
            if self.session_path.exists() and self.session_path.is_dir():
                for file in self.session_path.iterdir():
                    if file.is_file():
                        file.unlink()
                        self.log.info("Deleted existing file", directory=str(self.session_path), file=str(file))
        except Exception as e:
            self.log.error("Failed to delete existing files", error=str(e))
            raise DocumentPortalCustomException("Failed to delete existing files", sys) from e

class ChatIngestor:
    def __init__(self, temp_path:str = 'data', faiss_path:str = 'faiss_index', session_id: Optional[str] = None, use_session_dirs: bool = True):
        try:
            self.log = CustomLogger().get_logger(__name__)
            self.model_loader = ModelLoader()
            self.use_session_dirs = use_session_dirs
            self.session_id = session_id or f"session_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}_{uuid.uuid4().hex[:8]}"
            self.temp_path = Path(temp_path); self.temp_path.mkdir(parents=True, exist_ok=True)
            self.faiss_path = Path(faiss_path); self.faiss_path.mkdir(parents=True, exist_ok=True)
            self.log.info("ChatIngestor initialized", session_id=self.session_id, temp_path=self.temp_path, faiss_path=self.faiss_path, sessionized = self.use_session_dirs)
        

        except Exception as e:
            self.log.error("Chat Ingestion Failed", error=str(e))
            raise DocumentPortalCustomException("Failed to chat Ingestion", sys) from  e
    def _resolve_dir(self, base: Path):
        if self.use_session_dirs:
            d = base / self.session_id
            d.mkdir(parents=True, exist_ok=True)
            return d
        return base
    def _splitt(self, docs: List[Document], chunk_size = 1000, chunk_overlap = 200) -> List[List[Document]]:
        try:
            splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            chunks = splitter.split_documents(docs)
            self.log.info("Document split successfully", session_id=self.session_id, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            return chunks
        except Exception as e:
            self.log.error("Failed to splitt uploaded files", error=str(e))
            raise DocumentPortalCustomException("Failed to splitt uploaded files", sys) from  e
    def built_retriever(self, uploaded_files: Iterable, chunk_size: int = 1000, chunk_overlap: int = 200, k: int = 5):
        try:
            paths = save_uploaded_files(uploaded_files, self._resolve_dir(self.temp_path))
            docs = load_documents(paths)
            if not docs:
                raise ValueError("No documents found")
            chunks = self._splitt(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            self.log.info("Document split successfully", session_id=self.session_id, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            fm = FaissManager(self._resolve_dir(self.faiss_path), self.model_loader)
            texts = [c.page_content for c in chunks]
            metas = [c.metadata for c in chunks]
            try:
                vs = fm.load_or_create(texts= texts, metadatas=metas)
            except Exception as e:
                vs = fm.load_or_create(texts= texts, metadatas=metas)
            added = fm.add_documents(chunks)
            self.log.info("Documents added to FAISS successfully", index = str(self.faiss_path), session_id=self.session_id, added=added)
            return vs.as_retriever(search_type="similarity", search_kwargs={"k": k})

        except Exception as e:
            self.log.error("Failed to retrive uploaded files", error=str(e))
            raise DocumentPortalCustomException("Failed to retrive uploaded files", sys) from  e