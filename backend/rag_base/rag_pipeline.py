from typing import List, Tuple, Optional
from rag_base.embedding_builder import EmbeddingBuilder
from rag_base.pgvector_config import db
from rag_base.call_llm import CallLlm
from pathlib import Path
import fitz
import re
import os
from PIL import Image
import torch

class RAGPipeline:
    def __init__(self):
        try:
            self.db = db
            self.EB = EmbeddingBuilder()
            self.chat_history = []
        except Exception as e:
            print(f"❌ Failed to initialize RAG pipeline: {e}")

    def create_prompt(self, context: str, question: str) -> str:
        return (
            "You are an intelligent assistant grounded in retrieved documents.\n\n"
            "Retrieved Context:\n{context}\n\n"
            "User Question: {question}\n\n"
            "Instructions:\n"
            "- Answer concisely based only on the retrieved context above.\n"
            "- After every factual statement, cite the source using the page number, e.g. (page=1), (page=3).\n"
            "- If the information comes from an image or figure, cite it as [fig_1], [fig_2], etc. alongside the chunk citation.\n"
            "- If the answer is not present in the context, respond with: \"Not found in context\".\n"
            "- Do not use prior knowledge outside the retrieved context.\n"
            "- Format and well structure your answer in a way that the cited sources can be easily extracted by the frontend for display because the whole answer will be passed to the frontend as string.\n"
        ).format(context=context, question=question)

    def format_context_with_sources(self, retrieved_docs: list) -> str:
        """
        Format retrieved documents for multimodal RAG.
        Produces clean, token-efficient context with consistent chunk labels
        that match the citation format expected by the prompt.
        """
        contexts = []
        for idx, doc in enumerate(retrieved_docs):
            # Unpack doc: (id, content, source_id, page, image_ids, score)
            doc_id, content, source_id, page, image_ids, score = doc

            # Build label consistent with prompt citation format
            label = f"[context_{idx + 1}] (id={doc_id}, page={page}, score={score:.2f})"

            # Handle image references if present
            if image_ids:
                fig_refs = ", ".join(
                    f"[fig_{i+1}]" for i, _ in enumerate(image_ids)
                )
                label += f" figures={fig_refs}"
            contexts.append(f"{label}:\n{content.strip()}")
        return "\n\n".join(contexts)

    def generated_answer_with_citations(self, got:bool, answer:str, retrieved_docs: list) -> dict[str, str]:
        """
        Post-process the generated answer to include source citations in a structured format.
        Returns a dict with the answer and a list of cited sources for frontend display.
        """
        if not got:
            return {"answer": answer, "cited_sources": "Empty"}
        id_to_doc = {doc[0]: doc for doc in retrieved_docs}
        cited_ids = set(int(m.group(1))for m in re.finditer(r'\bid=(\d+)\b', answer))
        cited_sources = []
        for doc_id in sorted(cited_ids):
            doc = id_to_doc.get(doc_id)
            if doc is None:
                continue  # model hallucinated a non-existent id
            doc_id, content, source_id, page, image_ids, score = doc
            cited_sources.append(f"page_{page}, figures_{','.join(str(i) for i in image_ids) if image_ids else 'none'}")
            # cited_sources.append({
            #     "chunk_id": doc_id,
            #     "source_page_number": page,
            #     "source_image_figurenos": image_ids if image_ids else [],
            # })
        return {
            "answer": answer,
            "cited_sources": " | ".join(cited_sources)
        }
    
    async def query(self, question: str)-> dict[str, str]:
        emb_query = self.EB.embed_query(question)
        retrived_docs = self.db.search(emb_query, question)
        reranked_response = await self.EB.reranker(question, [c[1] for c in retrived_docs])
        
        # Map reranked results back to original document metadata
        # reranked_response has structure: {"results": [{"index": int, "relevance_score": float}, ...]}
        reranked_indices = [result["index"] for result in reranked_response.get("results", [])]
        reranked_chunks = [retrived_docs[idx] for idx in reranked_indices if idx < len(retrived_docs)]
        
        context = self.format_context_with_sources(reranked_chunks)
        prompt= self.create_prompt(context, question)
        answer = CallLlm(question, prompt, self.chat_history)
        
        out = answer.select_model()
        if not out:
            return {"answer": "Model unavailable. Please try again later.", "cited_sources": "Empty"}
        self.chat_history = out[-6:]
        result = out[-1].get("content", "No answer generated")
        return self.generated_answer_with_citations(True, result, reranked_chunks)
