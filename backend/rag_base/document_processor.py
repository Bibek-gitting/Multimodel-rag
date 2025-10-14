from pathlib import Path
import base64
import fitz
import docx
import io
from PIL import Image

class DocumentProcessor:
    @staticmethod
    def extract_text_from_docx(file_path):
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

    @staticmethod
    def extract_text_and_images_from_pdf(file_path):
        doc = fitz.open(file_path)
        text_chunks = []
        images = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if isinstance(text, str) and text.strip():
                text_chunks.append({
                    "content": text.strip(),
                    "page": page_num + 1
                })

            for img in page.get_images(full=True):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                images.append({
                    "data": image_base64,
                    "page": page_num + 1
                })
        return text_chunks, images
