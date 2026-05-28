import os
import importlib.util
from pathlib import Path
import httpx

if os.getenv("HF_HUB_ENABLE_HF_TRANSFER") == "1" and importlib.util.find_spec("hf_transfer") is None:
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

from sentence_transformers import SentenceTransformer
from numpy import ndarray
from dotenv import load_dotenv
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_MODELS_DIR = Path(os.getenv("LOCAL_MODELS_DIR", PROJECT_ROOT / "models"))
DEFAULT_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")
BGE_LOCAL_MODEL_PATH = LOCAL_MODELS_DIR / "bge-small-en-v1.5"


def _load_embedding_model(model_name: str | Path = DEFAULT_MODEL_NAME) -> SentenceTransformer:
    model_source = BGE_LOCAL_MODEL_PATH if BGE_LOCAL_MODEL_PATH.exists() else model_name
    model = SentenceTransformer(str(model_source))
    if not BGE_LOCAL_MODEL_PATH.exists():
        LOCAL_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model.save(str(BGE_LOCAL_MODEL_PATH))
    return model


class EmbeddingBuilder:
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model = _load_embedding_model(model_name)

    def embed_texts(self, chunks: list, batch_size=12) -> ndarray:
        texts=[chunk.get('text') for chunk in chunks]
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=True
        )
        return embeddings #[len(chunks), 384]

    def embed_query(self, query: str) -> ndarray:
        embeddings = self.model.encode(
            [query],
            batch_size=1,
            normalize_embeddings=True,
        )
        return embeddings[0] #[384]

    async def reranker(self, query: str, candidates: list[str], top_k=5):
        async with httpx.AsyncClient() as client:
                response = await client.post(
                url="https://openrouter.ai/api/v1/rerank",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "cohere/rerank-4-fast",
                    "query": query,
                    "documents": candidates,
                    "top_n": top_k
                })
        return response.json() 
