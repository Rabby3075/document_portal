import sys
from pathlib import Path
from langchain_community.vectorstores import FAISS
from src.single_document_chat.data_ingestion import SingleDocumentIngestor
from src.single_document_chat.retrieval import ConversationalRAG
from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalCustomException

FAISS_INDEX_PATH = Path("faiss_index")
def test_conversational_rag_on_pdf(pdf_path: str, question: str):
    try:
        model_loader = ModelLoader()
        if (FAISS_INDEX_PATH / "index.faiss").exists():
            print("Loading FAISS index...")
            embedding = model_loader.load_embedding_model()
            vectorstore = FAISS.load_local(folder_path=str(FAISS_INDEX_PATH), embeddings=embedding, allow_dangerous_deserialization=True)
            retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
            print("FAISS index loaded successfully.")
        else:
            print("FAISS index not found. Creating new index...")
            
            with open(pdf_path, "rb") as f:
                upload_files = [f]
                data_ingestor = SingleDocumentIngestor()
                retriever = data_ingestor.ingest_files(upload_files)
                print("FAISS index created successfully.")

        llm = model_loader.load_llm()
        print("====== Running Conversational RAG TEST ========")
        session_id = "test_session"
        rag = ConversationalRAG(retriever= retriever, session_id=session_id)
        response = rag.invoke(question)
        print(f"\nQuestion: {question}")
        print(f"\nAnswer: {response}")
        

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        pdf_path = Path(r"E:\\Project\\Document Portal\\mine one\\data\\single_document_chat\\NIPS-2017-attention-is-all-you-need-Paper.pdf")
        question = "What is the significance of this attention mechanism? Can you please describe eloborately?"
        if not Path(pdf_path).exists():
            print(f"File not found: {pdf_path}")
            sys.exit(1)
        test_conversational_rag_on_pdf(pdf_path, question)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)