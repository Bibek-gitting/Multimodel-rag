import os
import torch
import numpy as np
from transformers import CLIPModel, CLIPImageProcessor, CLIPTokenizer
from langchain.embeddings.base import Embeddings
from PIL import Image

class CLIPEmbeddingHandler(Embeddings):
    def __init__(self, cache_dir="./models", offline_mode=True):
        if offline_mode:
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
        base_path = r"E:\multirag\Multimodel-rag\models\models--openai--clip-vit-base-patch32\snapshots"
        snapshot_dirs = os.listdir(base_path)
        model_path = os.path.join(base_path, snapshot_dirs[0])

        self.model = CLIPModel.from_pretrained(model_path, cache_dir=cache_dir, local_files_only=offline_mode)
        self.image_processor = CLIPImageProcessor.from_pretrained(model_path, cache_dir=cache_dir, local_files_only=offline_mode)
        self.tokenizer = CLIPTokenizer.from_pretrained(model_path, cache_dir=cache_dir, local_files_only=offline_mode)

    def embed_texts(self, texts):
        inputs = self.tokenizer(text=texts, return_tensors="pt", padding=True, truncation=True, max_length=77)
        with torch.no_grad():
            features = self.model.get_text_features(**inputs)
            features = features / features.norm(dim=-1, keepdim=True)
        return features.squeeze().numpy()

    def embed_images(self, images):
        inputs = self.image_processor(images=images, return_tensors="pt")
        with torch.no_grad():
            features = self.model.get_image_features(**inputs)
            features = features / features.norm(dim=-1, keepdim=True)
        return features.squeeze().numpy()

    def embed_documents(self, texts):
        features = self.embed_texts(texts)
        if features.ndim == 1:
            return [features.tolist()]
        return [f.tolist() for f in features]

    def embed_query(self, text):
        features = self.embed_texts([text])
        if features.ndim == 1:
            return features.tolist()
        return features[0].tolist()
