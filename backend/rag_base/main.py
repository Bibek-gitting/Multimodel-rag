<<<<<<< HEAD
from __future__ import annotations

import sys
import threading
from pathlib import Path

from rag_base.document_processor import DocumentProcessor
from rag_base.doc_prepare_chinking import DocPrepareChinking
from rag_base.embedding_builder import EmbeddingBuilder
from rag_base.pgvector_config import db
from rag_base.ocr_call import OcrCall
from rag_base.rag_pipeline import RAGPipeline

# Global variable to store the initialized pipeline and a lock for thread safety
_rag_pipeline: RAGPipeline | None = None
_init_lock = threading.Lock()


def _source_dir_default() -> str:
    base_dir = Path(__file__).resolve().parent.parent  # backend/
    # uploaded_media_files is at backend/uploaded_media_files
    return str(base_dir / "uploaded_media_files")

async def process_uploaded_file(file_path: Path):
    texts, images = None, None
    EB = EmbeddingBuilder()
    if file_path.suffix == ".pdf" or file_path.suffix == ".docx":
        texts, image = DocumentProcessor.extract_text_and_images_from_file(str(file_path))
        images = await OcrCall().get_response_from_ocr(image)
    elif file_path.suffix == ".jpg" or file_path.suffix == ".png" or file_path.suffix == ".jpeg":
        image = DocumentProcessor.image_process(str(file_path))
        images = await OcrCall().get_response_from_ocr(image)
        # texts = []
    else:
        text = DocumentProcessor.extract_text_from_TXT(str(file_path))
        texts = [{"content": text, "page": 1}]
        # images = []
    chunks = DocPrepareChinking.get_chunks(texts, images)
    embeddings = EB.embed_texts(chunks)
    records = [
        {"text": t["text"], "pageno": t["pageno"], "figurenos": t["figurenos"]}
        for t in chunks
    ]
    db.insert_batch(records, embeddings, str(file_path))

def initialize_rag_pipeline(source_directory: str | None = None):
    """
    Initializes the embedding handler, vector store, model handler,
    and RAG pipeline. Should be called once during app startup.
    Thread-safe guarding prevents double-initialization.
    """
    global _rag_pipeline

    with _init_lock:
        if _rag_pipeline is not None:
            return _rag_pipeline

        print("🔧 Initializing RAG pipeline...")
        src_dir = source_directory or _source_dir_default()
        _rag_pipeline = RAGPipeline()
        print("✅ RAG pipeline initialized.")


async def query_rag_system(question: str):
=======
import sys
from rag_base.clip_embedding import CLIPEmbeddingHandler
from rag_base.index_builder import IndexBuilder
from rag_base.qwen_model_handler import QwenModelHandler
from rag_base.rag_pipeline import RAGPipeline

# Global variable to store the initialized pipeline
_rag_pipeline = None

def initialize_rag_pipeline(source_directory="./uploaded_media_files"):
    """
    Initializes the embedding handler, vector store, model handler,
    and RAG pipeline. Should be called once during app startup.
    """
    global _rag_pipeline

    if _rag_pipeline is None:
        print("🔧 Initializing RAG pipeline...")
        embedding_handler = CLIPEmbeddingHandler()
        index_builder = IndexBuilder(embedding_handler)
        vectorstore = index_builder.build_vector_index(source_directory)
        model_handler = QwenModelHandler()
        _rag_pipeline = RAGPipeline(vectorstore, model_handler)
        print("✅ RAG pipeline initialized.")
    return _rag_pipeline

def query_rag_system(question: str):
>>>>>>> 54ae8ae9ba589115b7514afd06d6ce90aa47ace8
    """
    Run a RAG query. Initializes the pipeline on first call.
    Can be imported and called from anywhere in your app.
    """
<<<<<<< HEAD
    global _rag_pipeline
    if _rag_pipeline is None:
        initialize_rag_pipeline()
    assert _rag_pipeline is not None 
    return await _rag_pipeline.query(question)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--download":
        # CLIPEmbeddingHandler()  # Ensure CLIP is locally available
        # QwenModelHandler().download_model_for_offline_use()
=======
    if _rag_pipeline is None:
        initialize_rag_pipeline()
    return _rag_pipeline.query(question) # type: ignore

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--download":
        CLIPEmbeddingHandler()  # Downloads CLIP to cache
        QwenModelHandler().download_model_for_offline_use()
>>>>>>> 54ae8ae9ba589115b7514afd06d6ce90aa47ace8
        sys.exit(0)

    # Run single query from CLI
    initialize_rag_pipeline()
    question = "What is happening in Hyderabad?"
    response = query_rag_system(question)
<<<<<<< HEAD
    # print("📄 Answer:\n", response.get("answer"))
=======
    print("📄 Answer:\n", response["answer"])
>>>>>>> 54ae8ae9ba589115b7514afd06d6ce90aa47ace8
