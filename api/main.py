import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, List, Optional, Any
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from src.data_ingestion.data_ingestion import DocumentHandler, DocumentComparator, ChatIngestor, FaissManager
from src.document_analyzer.data_analysis import DocumentAnalyzer
from src.document_compare.document_comparator import DocumentComparatorLLM
from src.document_chat.retrieval import DocumentConversationalRag

BASE_DIR = Path(__file__).resolve().parent.parent
FIASS_BASE = os.getenv("faiss_index", "faiss_index")
Upload_Base = os.getenv("UPLOAD_BASE", "data")

# In-memory chat history keyed by session_id. NOTE: cleared on server restart.
# Swap for Redis/SQLite if persistence matters.
SESSION_HISTORIES: Dict[str, List[BaseMessage]] = {}
print(BASE_DIR)
app = FastAPI(title="Document Portal API", version="1.0")
app.mount(
    "/static",
    StaticFiles(directory = BASE_DIR / "static"),
    name="static",
)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health()->Dict[str, str]:
    return {"status": "ok", "service": "document-portal-api"}

def _read_pdf_via_handler(handler: DocumentHandler, path:str)->str:
    try:
        if hasattr(handler, "read_pdf"):
            return handler.read_pdf(path)
        if hasattr(handler, "read_"):
            return handler.read_(path)
        raise RuntimeError("DocHandler has neither read_pdf nor read_ method.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}")
class FastAPIFileAdapter:
    """Adapt FastAPI UploadFile -> .name + .getbuffer() API"""
    def __init__(self, uplaod_file: UploadFile):
        self._upload_file = uplaod_file
        self.name = uplaod_file.filename
    def getbuffer(self) -> bytes:
        self._upload_file.file.seek(0)
        return self._upload_file.file.read()


@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    try:
        doc_handler = DocumentHandler()
        saved_path = doc_handler.save_pdf(FastAPIFileAdapter(file))
        text = _read_pdf_via_handler(doc_handler, saved_path)
        document_analyzer = DocumentAnalyzer()
        result = document_analyzer.analyze_document(text)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}")

@app.post("/compare")
async def compare_document(reference_file: UploadFile = File(...), actual_file: UploadFile = File(...)):
    try:
        dc = DocumentComparator()
        ref_path, act_path = dc.save_uploaded_files(FastAPIFileAdapter(reference_file), FastAPIFileAdapter(actual_file))
        _ = ref_path, act_path
        combined_text = dc.combine_document()
        comparator_llm = DocumentComparatorLLM()
        df = comparator_llm.compare_document(combined_text)
        return {"rows":df.to_dict(orient="records"), "session_id":dc.session_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}")
    
@app.post("/chat/index")
async def chat_index(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
    use_session_dirs: bool = Form(True),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    k: int = Form(5),
)->Any:
    try:
        wrapped = [FastAPIFileAdapter(f) for f in files]
        chat_ingestor = ChatIngestor(
            temp_path= Upload_Base,
            faiss_path = FIASS_BASE,
            use_session_dirs = use_session_dirs,
            session_id = session_id,
        )
        chat_ingestor.built_retriever(wrapped, chunk_size=chunk_size, chunk_overlap = chunk_overlap, k = k)
        return {"session_id": chat_ingestor.session_id, "k": k, "use_session_dirs": use_session_dirs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/query")
async def chat_query(
    question: str = Form(...),
    session_id: Optional[str] = Form(None),
    use_session_dirs: bool = Form(True),
    k: int = Form(5),
)->Any:
    try:
        if use_session_dirs and not session_id:
            raise HTTPException(status_code=400, detail="session_id is required when use_session_dirs is true")
        
        #prepare faiss index path
        faiss_index_path = os.path.join(FIASS_BASE, session_id) if use_session_dirs else FIASS_BASE #type:ignore
        if not os.path.isdir(faiss_index_path):
            raise HTTPException(status_code=404, detail=f"Index not found at {faiss_index_path}")
        #initialize lcel-chain
        rag = DocumentConversationalRag(session_id=session_id,) #type:ignore
        rag.load_retriever_from_faiss(faiss_index_path)

        # Pull (or start) this session's running history, run the chain with it,
        # then append the new user turn + answer so the next call sees them.
        history_key = session_id or "_default"
        history = SESSION_HISTORIES.setdefault(history_key, [])
        response = rag.invoke(question, chat_history=history)
        history.append(HumanMessage(content=question))
        history.append(AIMessage(content=response))

        return {
            "answer": response,
            "session_id": session_id,
            "k": k,
            "use_session_dirs": use_session_dirs,
            "engine": "lcel-chain",
            "turns": len(history) // 2,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/reset")
async def chat_reset(session_id: Optional[str] = Form(None)) -> Dict[str, Any]:
    """Clear in-memory chat history for a session (FAISS index untouched)."""
    history_key = session_id or "_default"
    removed = SESSION_HISTORIES.pop(history_key, None) is not None
    return {"session_id": session_id, "cleared": removed}