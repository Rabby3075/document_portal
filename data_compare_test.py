import io
from pathlib import Path
from src.document_compare.data_ingestion import DocumentComparatorIngestion
from src.document_compare.document_comparator import DocumentComparatorLLM 

def load_dummy_uploaded_file(file_path:str):
    return io.BytesIO(file_path.read_bytes())

def test_document_comparator():
    ref_path = Path(r"E:\\Project\\Document Portal\\mine one\\data\\document_compare\\Long_Report_V1.pdf")
    act_path = Path(r"E:\\Project\\Document Portal\\mine one\\data\\document_compare\\Long_Report_V2.pdf")

    class FakeUpload:
        def __init__(self, file_path:Path):
            self.name = file_path.name
            self._buffer = file_path.read_bytes()

        def getbuffer(self):
            return self._buffer
    

    comparator = DocumentComparatorIngestion()
    ref_upload = FakeUpload(ref_path)
    act_upload = FakeUpload(act_path)

    ref_file, act_file = comparator.save_upload_files(ref_upload, act_upload)
    combined_docs = comparator.combine_document()
    print("\n --- Combined Document Preview ---\n")
    print(combined_docs[:1000])  # Print the first 1000 characters of the combined document

    comparator_llm = DocumentComparatorLLM()
    df = comparator_llm.compare_document(combined_docs)
    print("\n --- Comparison Result DataFrame ---\n")
    print(df.head())  # Print the first few rows of the comparison result DataFrame
if __name__ == "__main__":
    test_document_comparator()
