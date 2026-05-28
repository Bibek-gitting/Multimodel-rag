<<<<<<< HEAD
from typing import List, Tuple, Optional
from rag_base.embedding_builder import EmbeddingBuilder
from rag_base.pgvector_config import db
from rag_base.call_llm import CallLlm
from pathlib import Path
import fitz
import re
=======
from langchain.prompts import PromptTemplate
from qwen_vl_utils import process_vision_info
from pathlib import Path
from langchain.schema import Document
from FlagEmbedding import FlagReranker
import fitz
import io
>>>>>>> 54ae8ae9ba589115b7514afd06d6ce90aa47ace8
import os
from PIL import Image
import torch

class RAGPipeline:
<<<<<<< HEAD
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
=======
    def __init__(self, vectorstore, model_handler,):
        self.vectorstore = vectorstore
        self.model_handler = model_handler
        self.model, self.processor = model_handler.load_model_from_cache()

        # Load reranker (bge-reranker-base)
        self.reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)

    def _rerank_chunks(self, question, documents):
        """Rerank retrieved documents based on query using BGE reranker."""
        reranked = []
        for doc in documents:
            score = self.reranker.compute_score([question, doc.page_content], normalize=True)
            reranked.append((doc, float(score[0]))) # type: ignore
        return sorted(reranked, key=lambda x: x[1], reverse=True)

    def create_prompt(self):
        template = """You are an intelligent assistant grounded in retrived documents.
        Retrieved Context:
        {context}
        User Question: {question}
        Answer (with [ID] citations):"""
        return PromptTemplate(template=template, input_variables=["context", "question"])
        # **Rules:**
        # 1. ALWAYS cite using [1], [2], or [IMG-1] where each number corresponds to a source in the retrieved list.
        # 2. When citing from a PDF, specify page numbers if known (e.g., [1: p.40-42]).
        # 3. If multiple sources support your claim, cite all relevant IDs.
        # 4. Do not fabricate citations or information.
        # 5. If insufficient data, explicitly say so.
        # 6. Use the images when relevant for answering visual questions.
    def format_context_with_sources(self, retrieved_docs):
        """
        Format retrieved documents for multimodal RAG.
        - Adds numeric tags [1], [2], [IMG-1], etc.
        - Keeps metadata for backend/frontend alignment.
        """
        context_parts = []
        text_counter = 1
        img_counter = 1

        # Assuming retrieved_docs is currently list of str
        # retrieved_docs = [Document(page_content="", metadata={"source": path}) if isinstance(path, str) else path for path in retrieved_docs]

        for doc in retrieved_docs:
            # Ensure doc is Document object
            if isinstance(doc, str):
                # fallback if doc is string (rare)
                doc = Document(page_content=doc, metadata={"source": "Unknown", "type": "text"})
            doc_type = doc.metadata.get("type", "text")
            # source_path = doc.metadata.get("source", "Unknown")
            # file_name = Path(source_path).name
            source = Path(doc.metadata.get("source", "Unknown")).name
            file_ext = Path(source).suffix.lower()
            # content = doc.page_content.strip() if doc.page_content else "[No textual content]"
            page = doc.metadata.get("page", None)

            if doc_type == "text":
                tag = f"[{text_counter}]"
                chunk = doc.page_content.strip()
                location = f", page: {page}" if page else "unknown page"
                context_parts.append(
                    f"{tag} {chunk}\n(Source: {source}, {location})"
                )
                text_counter += 1

            elif doc_type == "image" or file_ext in [".png", ".jpg", ".jpeg"]:
                tag = f"[IMG-{img_counter}]"
                context_parts.append(f"{tag} Image reference from {source} (page {page if page else 'unknown'})")
                img_counter += 1

            else:
                tag = f"[{text_counter}]"
                chunk = doc.page_content.strip()
                context_parts.append(f"{tag} {chunk}\n(Source: {source})")
                text_counter += 1

        return "\n\n".join(context_parts)

    def query(self, question, top_k=10):
        model = self.model
        processor = self.processor
        # Determine if it's a visual-only question
        is_visual_question = any(q in question.lower() for q in ["what is in the image", "what is in the picture", "describe this image"])

        retriever = self.vectorstore.as_retriever(search_kwargs={"k": top_k})
        print(f"\n🔍 Query: {question}")
        print("⏳ Retrieving relevant documents (text + images)...")
        initial_docs = retriever.invoke(question)

        # Rerank retrieved chunks
        print("🔄 Re-ranking retrieved chunks by relevance...")
        reranked = self._rerank_chunks(question, initial_docs)
        # 'reranked' is a list of tuples: (doc, score)
        retrieved_docs = [doc for doc in reranked[:top_k]]
        retrieved_docs = [doc[0] for doc in retrieved_docs]
        for i, (doc, score) in enumerate(reranked[:top_k]):
            print(f"  #{i+1}: {score:.4f} — {doc.metadata.get('source')}")

        if is_visual_question:
            retrieved_docs = [doc for doc in retrieved_docs if doc.metadata.get("type") == "image"]

        if not retrieved_docs:
            return {
                "query": question,
                "answer": "[No relevant documents found for the query]",
                "citations": []
            }
        text_contexts = []
        image_contexts = []

        for doc in retrieved_docs:
            doc_type = doc.metadata.get("type", "text")
            source_path = doc.metadata.get("source", "")
            page_num = doc.metadata.get("page", None)

            if doc_type == "image":
                pil_img = None
                try:
                    if os.path.exists(source_path):
                        if source_path.lower().endswith((".jpg", ".jpeg", ".png")):
                            pil_img = Image.open(source_path).convert("RGB")
                        elif source_path.lower().endswith(".pdf") and page_num:
                            pdf_doc = fitz.open(source_path)
                            page = pdf_doc[page_num - 1]
                            img_list = page.get_images(full=True)
                            if img_list:
                                xref = img_list[0][0]
                                base_img = pdf_doc.extract_image(xref)
                                pil_img = Image.open(io.BytesIO(base_img["image"])).convert("RGB")
                            pdf_doc.close()
                        if pil_img is not None:
                            image_contexts.append({
                                "image": pil_img,
                                "metadata": doc.metadata
                            })
                except Exception as e:
                    print(f"⚠️ Could not load image from {source_path}: {e}")
            else:
                text_contexts.append(doc.page_content.strip())

        text_docs = [doc for doc in retrieved_docs if doc.metadata.get("type") != "image"]
        context_text = self.format_context_with_sources(text_docs)
        if context_text is None:
            context_text = ""

        if image_contexts:
            context_text += "\n\n**Images Retrieved (model will analyze these):**\n"
            for idx, img_ctx in enumerate(image_contexts, 1):
                context_text += f"{idx}. Image from {img_ctx['metadata']['source']} (page {img_ctx['metadata'].get('page')})\n"

        prompt_template = self.create_prompt()
        formatted_prompt = prompt_template.format(context=context_text, question=question)

        print("📋 Formatted Prompt:\n", formatted_prompt)
        messages = [{"role": "user", "content": []}]
        for img_ctx in image_contexts:
            messages[0]["content"].append({
                "type": "image",
                "image": img_ctx["image"]
            })

        messages[0]["content"].append({
            "type": "text",
            "text": formatted_prompt
        })

        text_input = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages) # type: ignore
        print("Text input for model:", text_input.strip())
        print("Number of image inputs:", len(image_inputs) if image_inputs else 0)

        if not text_input.strip():
            print("⚠️ No valid text prompt was generated. Skipping model call.")
            return {"query": question, "answer": "[ERROR] No valid prompt generated", "citations": []}
        if image_contexts and image_inputs:
            inputs = processor(text=[text_input], images=image_inputs, videos=video_inputs, return_tensors="pt", padding=True).to(model.device)
        else:
            inputs = processor(text=[text_input], return_tensors="pt", padding=True)

        print("🤖 Generating answer with vision model...")
        try:
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=128,
                    temperature=0.3,
                    top_p=0.95,
                    do_sample=True
                )
        except Exception as e:
            print(f"❌ Model failed to generate response: {e}")
            return {"query": question, "answer": "[ERROR] Model inference failed", "citations": []}
        print("outputs:", outputs)
        generated_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(inputs.input_ids, outputs)
        ]
        print("Image inputs:", image_inputs)
        print("Text input tokens:", inputs.input_ids)
        print("Generated IDs:", generated_ids)

        answer = processor.batch_decode(generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        print("📝 Raw model answer:", answer)
        if not answer or not "".join(answer).strip():
            print("⚠️ Model returned an empty response!")
            return {"query": question, "answer": "[No meaningful answer returned]", "citations": []}
        return {
            "query": question,
            "answer": " ".join(answer).strip(),
            "citations": [
                {
                    "id": idx + 1 if doc.metadata.get("type", "text") != "image" else f"IMG-{idx + 1}",
                    "type": doc.metadata.get("type", "text"),
                    "source": doc.metadata.get("source"),
                    "page": doc.metadata.get("page"),
                    **(
                        {"preview": f"./{doc.metadata.get('source')}"}
                        if doc.metadata.get("type") == "image"
                        else {}
                    )
                }
                for idx, doc in enumerate(retrieved_docs)
            ]
        }
>>>>>>> 54ae8ae9ba589115b7514afd06d6ce90aa47ace8
