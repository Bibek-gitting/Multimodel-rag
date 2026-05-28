import os
from load_model import load_model

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"  # skips network check
os.environ["FLAGS_log_level"] = "3"  # reduces log noise
ngrok_token = os.getenv("NGROK_AUTHTOKEN")
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_MAX_THREADS"] = "1"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "300"

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from paddleocr import PaddleOCRVL
from typing import Optional
from pyngrok import ngrok
from PIL import Image
import uvicorn
import io
import numpy as np
import nest_asyncio
import torch

from transformers import BitsAndBytesConfig, AutoModel, AutoTokenizer

app = FastAPI()
model, tokenizer = load_model()
ocr = PaddleOCRVL(pipeline_version="v1")
app.add_middleware(
    CORSMiddleware, 
    allow_origins=['*'], 
    allow_credentials=True, 
    allow_methods=['*'], 
    allow_headers=['*'],
)
ngrok.set_auth_token(ngrok_token)
port = 1234
ngrok_tunnel = ngrok.connect(port)
print('Public URL:', ngrok_tunnel.public_url)
nest_asyncio.apply()

@app.post("/ocr")
async def run_ocr(file: UploadFile = File(...), page: Optional[int] = Form(None), figureno: Optional[int] = Form(None), visual_type: Optional[str] = Form(None)):
    #visual_type = general / chart / raw
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    question = 'What is in the image?'
    msgs = [{'role': 'user', 'content': [image, question]}]
    res=""
    image_np = np.array(image)
    try:
        if visual_type =="raw" or visual_type == "general":
            #captioning
            with torch.inference_mode():
                res = model.chat(
                    image=None,
                    msgs=msgs,
                    tokenizer=tokenizer
                )

        result = ocr.predict(image_np)
    
        texts = []
        text=""
        
        for x in result:
            parsing_list = x.get("parsing_res_list",[])
            texts.append(parsing_list)
        for item in texts[0]:
            text += item.content.replace('\n', ' ') + " "
        print(text, res if res else "No caption for chart")
        return {k: v for k, v in {
            "ocr_text": text,
            "caption": res if res else "No caption for chart",
            "page": page,
            "figureno": figureno}.items() if v is not None
        }
    except Exception as e:
        print(f"OCR processing failed for page {page}, figure {figureno}: {e}")
        return {}

if __name__ == "__main__":
    uvicorn.run(app, port=port)