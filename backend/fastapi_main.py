from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path
from rag_base.main import query_rag_system
import uvicorn
import os

app = FastAPI()

# Enable CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request body model
class QueryRequest(BaseModel):
    question: str

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    folder = Path("uploaded_media_files")
    folder.mkdir(exist_ok=True)
    contents = await file.read()
    file_name = file.filename if file.filename is not None else "uploaded_media_files"
    if file.filename is None or not file.filename.endswith((".png", ".jpg", ".pdf", ".mp3", ".doc", ".docx")):
        return JSONResponse(status_code=400, content={"error": "Invalid file type"})
    file_path = folder / file_name
    with open(file_path, "wb") as f:
        f.write(contents)

    return {"filename": file.filename, "content_type": file.content_type}

@app.post("/ask")
async def ask_question(req: QueryRequest):
    result = query_rag_system(req.question)
    return result  # This will automatically be returned as JSON


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)