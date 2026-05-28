from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re

class DocPrepareChinking:
    @staticmethod
    def get_chunks(texts: List[Dict[str, Any]]|None, images: List[Dict[str, Any]|None]|None) -> List[Dict[str, str]]:
        valid_texts = [t for t in (texts or []) if t] if texts is not None else []
        valid_images = [i for i in (images or []) if i is not None] if images is not None else []
        if not valid_texts and not valid_images:
            return []
        merged_chunks = []
        all_pages = {t['page'] for t in valid_texts if isinstance(t, dict)} | {i['page'] for i in valid_images if isinstance(i, dict)}
        for page_no in sorted(all_pages):
            page_content = ""
            
            # Add PDF text in order
            page_texts = [t for t in valid_texts if isinstance(t, dict) and t['page'] == page_no]
            for t in page_texts:
                page_content += t.get('content', "").strip() + "\n"
            
            # Add image OCR + captions in order
            page_images = sorted([i for i in valid_images if isinstance(i, dict) and i['page'] == page_no], key=lambda x: x['figureno'])
            for i in page_images:
                ocr_text = i.get("ocr_text", "").strip()
                caption = i.get("caption", "").strip()
                figure_no = i.get("figureno", "unknown")
                
                # Merge OCR + caption + figure number
                image_text = f"[Figure {figure_no}] contains:\n"
                if ocr_text:
                    image_text += ocr_text + "\n"
                if caption:
                    image_text += f"[Image Caption] tells: {caption}\n"
                
                page_content += image_text

            if not page_content.strip():
                continue
            # Split merged page content into chunks
            chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=150).split_text(page_content)
            for chunk in chunks:
                figurenos = [int(match) for match in re.findall(r'\[Figure (\d+)\]', chunk)]
                merged_chunks.append({
                    "text": chunk,
                    "pageno": page_no,
                    "figurenos": figurenos
                })
        return merged_chunks
    