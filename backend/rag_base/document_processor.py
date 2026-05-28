from __future__ import annotations
from pathlib import Path
from docx2pdf import convert
from typing import List, Tuple, Dict, Any
import numpy as np
from PIL import Image
import io
import pymupdf  # PyMuPDF

def bbox_overlap_area(a: tuple, b: tuple) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0 = max(ax0, bx0); iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1); iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    return (ix1 - ix0) * (iy1 - iy0)

def is_native_table(drawing_bbox: tuple, text_blocks: list) -> bool:
    dx0, dy0, dx1, dy1 = drawing_bbox
    drawing_area = (dx1 - dx0) * (dy1 - dy0)
    if drawing_area == 0:
        return False
    for block in text_blocks:
        block_bbox = (
            block["bbox"][0], block["bbox"][1],
            block["bbox"][2], block["bbox"][3]
        )
        overlap = bbox_overlap_area(drawing_bbox, block_bbox)
        # If more than 30% of the drawing area contains text → native table
        if overlap / drawing_area > 0.3:
            return True
    return False

def classify_visual_block(crop_bytes: bytes, bbox: tuple, paths: list) -> str:
        """
        Lightweight heuristic to route a cropped image region.
        Returns: 'chart' | 'general'
        Priority: vector primitive count (reliable) → pixel heuristics (fallback)
        """
        # Primary: if drawing paths exist in this region, count primitives
        # Many primitives = chart/diagram, zero = embedded raster image
        if paths and bbox:
            x0, y0, x1, y1 = bbox
            primitives_in_region = sum(
                1 for p in paths
                if p["rect"].x0 >= x0 and p["rect"].y0 >= y0
                and p["rect"].x1 <= x1 and p["rect"].y1 <= y1
            )
            if primitives_in_region > 10:
                return "chart"
            if primitives_in_region == 0:
                return "general"
        
        # img = Image.open(io.BytesIO(crop_bytes)).
        img = Image.open(io.BytesIO(crop_bytes)).convert("RGB")
        arr = np.array(img)
        h, w = arr.shape[:2]

        # Heuristic 1: aspect ratio typical of charts (wide and short)
        aspect = w / h
        
        # Heuristic 2: color diversity — charts tend to have distinct color bands
        # while photos have high pixel-level variance
        resized = np.array(img.resize((64, 64)))
        unique_colors = len(np.unique(resized.reshape(-1, 3), axis=0))

        # Heuristic 3: high horizontal uniformity = axis lines / grid lines
        row_stds = arr.std(axis=1).mean()   # low = many uniform horizontal bands

        if aspect > 1.0 and unique_colors < 800 and row_stds < 60:
            return "chart"
        return "general"

def process_rasterized_page(page, page_num: int) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        For pages with no embedded raster images (vector/mixed),
        rasterize then intelligently route each visual region.
        """
        text_blocks = []

        # Get layout blocks from PyMuPDF — this works even on vector pages
        blocks = page.get_text("dict")["blocks"]
        
        visual_bboxes = []

        for block in blocks:
            if block["type"] == 1:    # image block (even if not extractable as xref)
                visual_bboxes.append(block["bbox"])
            else:
                text = " ".join(span["text"] for line in block["lines"] for span in line["spans"]).strip()
                if text:
                    text_blocks.append(text)

        # Also detect large non-text regions via page drawings
        # (covers vector charts which have no image blocks at all)
        paths = page.get_drawings()
        if paths:
            # Cluster drawing bboxes into regions
            all_rects = [p["rect"] for p in paths if p["rect"].width > 50 and p["rect"].height > 50]
            if all_rects:
                # Simple union bbox of all drawings as a candidate visual region
                x0 = min(r.x0 for r in all_rects)
                y0 = min(r.y0 for r in all_rects)
                x1 = max(r.x1 for r in all_rects)
                y1 = max(r.y1 for r in all_rects)
                area = (x1 - x0) * (y1 - y0)
                already_covered = any(abs(x0 - b[0]) < 10 and abs(y0 - b[1]) < 10 
                                    for b in visual_bboxes)  # simple check to avoid duplicates
                if area > 10000 and not already_covered:      # ignore tiny decorative lines
                    if is_native_table((x0, y0, x1, y1), blocks):
                        pass
                    else:
                        visual_bboxes.append((x0, y0, x1, y1))

        if not visual_bboxes:
            return text_blocks, []
        
        # Rasterize once, crop per region
        mat = pymupdf.Matrix(2, 2)
        full_pix = page.get_pixmap(matrix=mat, colorspace=pymupdf.csRGB)
        full_img = Image.open(io.BytesIO(full_pix.tobytes("png")))
        W, H = full_img.size
        scale_x = W / page.rect.width
        scale_y = H / page.rect.height

        image_blocks = []
        for i, bbox in enumerate(visual_bboxes):
            x0, y0, x1, y1 = bbox
            crop = full_img.crop((int(x0*scale_x), int(y0*scale_y), 
                                int(x1*scale_x), int(y1*scale_y)))
            buf = io.BytesIO()
            crop.save(buf, format="PNG")
            crop_bytes = buf.getvalue()

            image_blocks.append({
                "data": crop_bytes,
                "page": page_num,
                "figureno": i + 1,
                "visual_type": classify_visual_block(crop_bytes, bbox, paths)  # 'chart' or 'general'
            })

        return text_blocks, image_blocks

class DocumentProcessor:
    @staticmethod
    def extract_text_from_TXT(file_path: str) -> str:
        """Extract text content from a TXT file, skipping empty paragraphs."""
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                return content.replace("\n", '')
        except Exception as e:
            print(f"❌ Failed to extract text from DOCX {file_path}: {e}")
            return ""

    @staticmethod
    def extract_text_and_images_from_file(file_path: str) -> Tuple[List[Dict[str, Any|None]], List[Dict[str, Any|None]]]:
        """
        Extract text chunks and images from a PDF. Images are base64-encoded to avoid filesystem I/O here.

        Returns:
            (texts, images)
            texts: List[{"content": str, "page": int}]
            images: List[{"data": str (base64), "page": int, "figureno": int}]
        """
        if Path(file_path).suffix == '.docx':
            converted = Path(file_path).with_suffix('.pdf')
            convert(file_path, str(converted))
            file_path = str(converted)
        texts: List[Dict[str, Any|None]] = []
        images: List[Dict[str, Any|None]] = []
        try:
            with pymupdf.open(file_path) as file:
                for page_num in range(len(file)):
                    page = file[page_num]
                    # process_rasterized_page(page, page_num + 1)
                    # text = page.get_text("text")
                    # if isinstance(text, str) and text.strip():
                    #     texts.append({
                    #         "content": text.strip(),
                    #         "page": page_num + 1,
                    #     })

                    try:
                        img_list = page.get_images(full=True)
                        # printing number of images found in this page
                        if img_list:
                            print(f"[+] Found a total of {len(img_list)} raw images on page {page_num+1}")
                            for img_idx,img in enumerate(img_list):
                                base_image = file.extract_image(img[0])
                                image_bytes = base_image.get("image")
                                if image_bytes:
                                    images.append({
                                        "data": image_bytes,
                                        "page": page_num + 1,
                                        "figureno" : img_idx + 1,
                                        "visual_type": "raw"
                                    })
                        else:
                            text_dict, image_dict = process_rasterized_page(page, page_num + 1)
                            if text_dict:
                                for t in text_dict:
                                    if isinstance(t, str) and t.strip():
                                        texts.append({"content": t.strip(), "page": page_num + 1})
                            if image_dict:
                                images.extend(image_dict)
                    except Exception as e:
                        print(f"⚠️ Failed to extract image(s) from PDF page {page_num + 1} in {file_path}: {e}")
        except Exception as e:
            print(f"❌ Failed to open or parse PDF {file_path}: {e}")

        return texts, images
    
    @staticmethod
    def image_process(file_path: str) -> List[Dict[str,Any|None]]:
        try:
            with open(file_path, "rb") as image_file:
                image_bytes = image_file.read()
            return [{"data": image_bytes, "page": 1, "figureno": 1}]
        except Exception as e:
            print(f"❌ Failed to process image {file_path}: {e}")
            return []

    


    