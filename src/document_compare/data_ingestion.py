import os
import sys
from pathlib import Path
import fitz
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalCustomException
from datetime import datetime
import uuid
class DocumentComparatorIngestion:
    """
    Compares two documents and identifies differences.
    Automatically logs all actions and handles exceptions gracefully.
    """

    def __init__(self, data_dir:str = "data/document_compare", session_id = None):
        self.log = CustomLogger().get_logger(__name__)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}_{uuid.uuid4().hex[:8]}"
        self.session_path = self.data_dir / self.session_id
        os.makedirs(self.session_path, exist_ok=True)
        self.log.info("DocumentComparator initialized successfully.")
    
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

    def save_upload_files(self,reference_file:str, actual_file:str):
        try:
            # check if the uploaded files already exist in the data directory, if yes delete them before saving new ones
            self.delete_existing_files()
            self.log.info("Existing files deleted successfully, ready to save new uploaded files.")
            reference_path = self.session_path / reference_file.name
            actual_path = self.session_path / actual_file.name
            if not reference_file.name.lower().endswith('.pdf') or not actual_file.name.lower().endswith('.pdf'):
                raise ValueError("Both uploaded files must be PDFs")
            
            with open(reference_path, "wb") as f: #write the uploaded file to disk
                f.write(reference_file.getbuffer())
            
            with open(actual_path, "wb") as f: #write the uploaded file to disk
                f.write(actual_file.getbuffer())
            
            self.log.info("Uploaded files saved successfully", reference_file=str(reference_path), actual_file=str(actual_path))
            return reference_path, actual_path
            

        except Exception as e:
            self.log.error("Failed to save uploaded files", error=str(e))
            raise DocumentPortalCustomException("Failed to save uploaded files", sys) from e
    
    def read_pdf(self, file_path:Path)->str:
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
            self.log.error("Failed to read PDF", error=str(e))
            raise DocumentPortalCustomException("Failed to read PDF", sys) from e

    def read_pdf_pages(self, file_path:Path)->list[dict]:
        try:
            pages = []
            with fitz.open(file_path) as doc:
                if doc.is_encrypted:
                    raise ValueError("PDF is encrypted and cannot be read")

                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    pages.append({
                        "page": page_num + 1,
                        "text": text.strip()
                    })
            self.log.info("PDF pages read successfully", file_path=str(file_path), pages=len(pages))
            return pages

        except Exception as e:
            self.log.error("Failed to read PDF pages", error=str(e))
            raise DocumentPortalCustomException("Failed to read PDF pages", sys) from e
    
    def combine_document(self)->str:
        try:
            content_dict = {}
            doc_parts = []
            for filename in sorted(self.session_path.iterdir()):
                if filename.is_file() and filename.suffix.lower() == ".pdf":
                    content_dict[filename.name] = self.read_pdf(filename)
            for filename, content in content_dict.items():
                doc_parts.append(f"Document: {filename}\nContent:\n{content}")
            combined_text = "\n".join(doc_parts)
            self.log.info("Documents combined successfully", count = len(content_dict))
            return combined_text
        except Exception as e:
            self.log.error("Failed to combine documents", error=str(e))
            raise DocumentPortalCustomException("Failed to combine documents", sys) from e

    def combine_document_pages(self)->list[dict]:
        try:
            documents = []
            for filename in sorted(self.session_path.iterdir()):
                if filename.is_file() and filename.suffix.lower() == ".pdf":
                    documents.append({
                        "filename": filename.name,
                        "pages": self.read_pdf_pages(filename)
                    })

            if len(documents) != 2:
                raise ValueError(f"Expected 2 PDFs for comparison, found {len(documents)}")

            self.log.info("Document pages combined successfully", count=len(documents))
            return documents
        except Exception as e:
            self.log.error("Failed to combine document pages", error=str(e))
            raise DocumentPortalCustomException("Failed to combine document pages", sys) from e
    
    def clean_old_sessions(self, keep_latest: int = 3):
        """
        Optional method to delete older session folders, keeping only the latest N.
        """
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

# if __name__ == "__main__":
#     try:
#         ingestion = DocumentComparatorIngestion()
#         ref_path, act_path = ingestion.save_upload_files(
#             reference_file=Path(r"E:\\Project\\Document Portal\\mine one\\data\\document_compare\\Long_Report_V1.pdf"),
#             actual_file=Path(r"E:\\Project\\Document Portal\\mine one\\data\\document_compare\\Long_Report_V2.pdf")
#         )
#         combined_docs = ingestion.combine_document()
#         print(combined_docs[:500]) #print the first 500 characters of the combined document
#     except Exception as e:
#         print(f"Error during document ingestion: {e}")



    
