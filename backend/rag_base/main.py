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
    """
    Run a RAG query. Initializes the pipeline on first call.
    Can be imported and called from anywhere in your app.
    """
    if _rag_pipeline is None:
        initialize_rag_pipeline()
    return _rag_pipeline.query(question) # type: ignore

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--download":
        CLIPEmbeddingHandler()  # Downloads CLIP to cache
        QwenModelHandler().download_model_for_offline_use()
        sys.exit(0)

    # Run single query from CLI
    initialize_rag_pipeline()
    question = "What is happening in Hyderabad?"
    response = query_rag_system(question)
    print("📄 Answer:\n", response["answer"])
