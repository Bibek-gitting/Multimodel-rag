from langchain_community.vectorstores import FAISS
from langchain_experimental.text_splitter import SemanticChunker
from langchain.schema.document import Document
from pathlib import Path
from PIL import Image
import numpy as np
import io
import base64
from rag_base.document_processor import DocumentProcessor

class IndexBuilder:
    def __init__(self, embedding_handler):
        self.embedding_handler = embedding_handler
        self.chunker = SemanticChunker(embedding_handler)

    def build_vector_index(self, source_dir):
        docs = []
        vectors = []

        for file in Path(source_dir).iterdir():
            ext = file.suffix.lower()

            if ext == ".pdf":
                texts, images = DocumentProcessor.extract_text_and_images_from_pdf(str(file))
                for text in texts:
                    chunks = self.chunker.split_text(text["content"])
                    if chunks:
                        vecs = self.embedding_handler.embed_texts(chunks)
                        docs.extend([Document(page_content=c, metadata={"source": str(file), "page": text["page"], "chunk_id": i}) for i, c in enumerate(chunks)])
                        vectors.extend(vecs)
                if images:
                    pil_images = [Image.open(io.BytesIO(base64.b64decode(img["data"]))).convert("RGB") for img in images]
                    vecs = self.embedding_handler.embed_images(pil_images)
                    if isinstance(vecs, np.ndarray) and vecs.ndim == 1:
                        vecs = [vecs.tolist()]
                    else:
                        vecs = [v.tolist() for v in vecs]
                    docs.extend([Document(page_content=f"Image from PDF page {img['page']}", metadata={"source": str(file), "page": img['page'], "type": "image"}) for img in images])
                    vectors.extend(vecs)

            elif ext == ".docx":
                text = DocumentProcessor.extract_text_from_docx(str(file))
                chunks = self.chunker.split_text(text)
                if chunks:
                    vecs = self.embedding_handler.embed_texts(chunks)
                    docs.extend([Document(page_content=c, metadata={"source": str(file), "chunk_id": i}) for i, c in enumerate(chunks)])
                    vectors.extend(vecs)

            elif ext in [".jpg", ".jpeg", ".png"]:
                image = Image.open(file).convert("RGB")
                # vec = self.embedding_handler.embed_images([image])[0]
                vec = self.embedding_handler.embed_images([image])
                if vec.ndim == 1:
                    vectors.append(vec.tolist())
                else:
                    vectors.extend([v.tolist() for v in vec])
                docs.append(Document(page_content="Standalone image", metadata={"source": str(file), "type": "image", "path": str(file)}))
                vectors.append(vec)

            elif ext == ".txt":
                with open(file, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                    chunks = self.chunker.split_text(text)
                    if chunks:
                        vecs = self.embedding_handler.embed_texts(chunks)
                        docs.extend([Document(page_content=c, metadata={"source": str(file), "chunk_id": i}) for i, c in enumerate(chunks)])
                        vectors.extend(vecs)

            else:
                print(f"❌ Skipped unsupported file: {file}")

        text_embedding_pairs = [(doc.page_content, vector) for doc, vector in zip(docs, vectors)]
        vectorstore = FAISS.from_embeddings(text_embeddings=text_embedding_pairs, metadatas=[doc.metadata for doc in docs], embedding=self.embedding_handler)
        print("✅ FAISS index built and saved.")
        return vectorstore
