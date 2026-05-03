import os
import sys
import fitz
import uuid
from datetime import datetime
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalCustomException

class DocumentHandler:
    """
    Handles PDF saving and reading operations.
    Automatically logs all actions and supports session-based organization
    """

    def __init__(self, data_dir=None, session_id=None):
        try:
            self.log = CustomLogger().get_logger(__name__)
            self.data_dir = data_dir or os.getenv(
                "data_storage_path",
                os.path.join(os.getcwd(), "data", "document_analysis")
            )
            self.session_id = session_id or f"session_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}_{uuid.uuid4().hex[:8]}"
            #create base session directory
            self.session_path = os.path.join(self.data_dir, self.session_id)
            os.makedirs(self.session_path, exist_ok=True)
            self.log.info("DocumentHandler initialized", session_id=self.session_id, session_path=self.session_path)
        except Exception as e:
            self.log.error(f"Failed to initialize DocumentHandler: {e}")
            raise DocumentPortalCustomException(f"Failed to initialize DocumentHandler: {e}", sys)

    def save_pdf(self,uploaded_file):
        """
        Saves the uploaded PDF to a session-specific directory with a unique filename.
        """
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
            raise DocumentPortalCustomException("Error reading PDF", e) from e

if __name__ == "__main__":
    from pathlib import Path
    from io import BytesIO

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    
    pdf_path=r"E:\\Project\\Document Portal\\mine one\\data\\document_analysis\\NIPS-2017-attention-is-all-you-need-Paper.pdf"
    class DummnyFile:
        def __init__(self,file_path):
            self.name = Path(file_path).name
            self._file_path = file_path
        def getbuffer(self):
            return open(self._file_path, "rb").read()
        
    dummy_pdf = DummnyFile(pdf_path)
    
    handler = DocumentHandler()
    
    try:
        saved_path=handler.save_pdf(dummy_pdf)
        print(saved_path)
        
        content=handler.read_pdf(saved_path)
        print("PDF Content:")
        print(content[:500])  # Print first 500 characters of the PDF content
        
    except Exception as e:
        print(f"Error: {e}")
    
