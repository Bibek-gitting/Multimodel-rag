import shutil

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pathlib import Path
from rag_base.main import query_rag_system
from rag_base.main import process_uploaded_file
from rag_base.pgvector_config import db
from fastapi.concurrency import run_in_threadpool
from starlette import status
from starlette.staticfiles import StaticFiles
import uvicorn
import os
import uuid
from typing import Set

# Base directories and configuration
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploaded_media_files"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
CHUNK_SIZE = 1024 * 1024  # 1MB

# Allowed types
ALLOWED_EXTS: Set[str] = {".png", ".jpg", ".jpeg", ".pdf", ".mp3", ".doc", ".docx"}
ALLOWED_CONTENT_TYPES: Set[str] = {
    "image/png",
    "image/jpeg",
    "application/pdf",
    "audio/mpeg",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

app = FastAPI()
db.setup()

# Enable CORS (env-driven)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    """Request body for the RAG question endpoint."""
    question: str = Field(..., min_length=1, max_length=2000)


def _safe_extension(filename: str) -> str:
    return Path(filename).suffix

def _encrypt_filename(filename: str) -> str:
    return f"{uuid.uuid4().hex}{Path(filename).suffix}"

def _validate_upload(file: UploadFile) -> str:
    """Validate incoming file by extension and content-type; return normalized extension."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")

    ext = _safe_extension(file.filename)
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type.")

    # Basic content-type validation: ensure declared type is broadly expected
    if file.content_type:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            # Allow generic image/* for image extensions
            if not (file.content_type.startswith("image/") and ext in {".png", ".jpg", ".jpeg"}):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content type.")

    return _encrypt_filename(file.filename)

# def process_uploaded_file(file_path: Path):
#     texts, images = DocumentProcessor.extract_text_and_images_from_file(str(file_path))
#     embeddings = EmbeddingBuilder.embed_documents([t["content"] for t in texts])
#     records = [
#         {"text": t["content"], "pageno": t["page"], "figurenos": []}
#         for t in texts
#     ]
#     PGVectorDB().insert_batch(records, embeddings)

#     if file_path.suffix == ".pdf":
#         texts, images = DocumentProcessor.extract_text_and_images_from_file(str(file_path))
#     elif file_path.suffix == ".jpg":
#             texts = []
#             images = DocumentProcessor.image_process(str(file_path))
#     else:
#         text = DocumentProcessor.extract_text_from_TXT(str(file_path))
#         texts = [{"content": text, "page": 1}]
#         images = []
# def _generate_server_filename(ext: str) -> str:
#     """Generate a unique server-side filename using UUID while preserving the extension."""
#     return f"{uuid.uuid4().hex}{ext}"


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> JSONResponse:
    """
    Upload a media file safely:
    - Validates filename extension and content-type
    - Streams the file to disk to avoid loading into memory
    - Enforces a maximum upload size
    - Generates a unique server-side filename to prevent overwrites
    """
    server_filename = _validate_upload(file)
    # server_filename = _generate_server_filename(ext)
    file_path = UPLOAD_DIR / server_filename

    total = 0
    try:
        with open(file_path, "wb") as out_f:
            while True:
                to_read = min(CHUNK_SIZE, MAX_UPLOAD_SIZE_BYTES - total)
                if to_read <= 0:
                    break
                chunk = await file.read(to_read)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_SIZE_BYTES:
                    # Remove partially written file and raise
                    try:
                        out_f.close()
                        file_path.unlink()
                    except FileNotFoundError:
                        pass
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Max {MAX_UPLOAD_SIZE_MB}MB.",
                    )
                out_f.write(chunk)
    finally:
        await file.close()
    await process_uploaded_file(file_path)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "filename": server_filename,
            "original_filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": total,
        },
    )

@app.get("/uploaded_file")
async def get_uploaded_files():
    files=[]
    try:
        for f in UPLOAD_DIR.iterdir():
            if f.is_file() and f.exists():
                files.append(f.name)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"file": str(files[0])})
    except FileNotFoundError:
        pass
    raise HTTPException(status_code=404, detail="File not found")

@app.delete("/delete_file")
async def remove_file():
    try:
        files = [f for f in UPLOAD_DIR.iterdir() if f.exists()]
        for file in files:
            if file.is_file():
                file.unlink()
            elif file.is_dir():
                shutil.rmtree(file)
        db.delete_db()
        print("All files deleted and database cleared.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "All files deleted and database cleared."},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @app.delete("/delete_files")
# def delete_file():
#     for f in UPLOAD_DIR.iterdir():
#         if f.name == filename and f.is_file():
#             file_path = UPLOAD_DIR / filename
#             os.remove(file_path)
#             return JSONResponse(status_code=status.HTTP_200_OK, content={"file": file_path})
#     raise HTTPException(status_code=404, detail="File not found")

# @app.delete("/uploaded_files/{filename}")
# def delete_file(filename: str):
#     for f in UPLOAD_DIR.iterdir():
#         if f.name == filename and f.is_file():
#             file_path = UPLOAD_DIR / filename
#             os.remove(file_path)
#             return JSONResponse(status_code=status.HTTP_200_OK, content={"file": file_path})
#     raise HTTPException(status_code=404, detail="File not found")

@app.post("/ask")
async def ask_question(req: QueryRequest) -> JSONResponse:
    """Proxy a question to the RAG system without blocking the event loop."""
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty.")

    result = await query_rag_system(question)
    return JSONResponse(status_code=status.HTTP_200_OK, content=result)

# app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")

if __name__ == "__main__":
    uvicorn.run(app, port=8000)
