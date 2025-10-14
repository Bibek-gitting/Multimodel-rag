import os
import torch
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

class QwenModelHandler:
    def __init__(self, model_name="Qwen/Qwen2-VL-2B-Instruct", cache_dir="../models", offline_mode=True):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.offline_mode = offline_mode

    def download_model_for_offline_use(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        print(f"📥 Downloading {self.model_name} to {self.cache_dir}...")
        processor = AutoProcessor.from_pretrained(self.model_name, cache_dir=self.cache_dir)
        model = Qwen2VLForConditionalGeneration.from_pretrained(self.model_name, torch_dtype=torch.bfloat16, device_map="auto", cache_dir=self.cache_dir)
        print(f"✅ Model downloaded and cached at: {self.cache_dir}")
        return model, processor

    def load_model_from_cache(self):
        if self.offline_mode:
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            os.environ['HF_DATASETS_OFFLINE'] = '1'
        dtype = torch.float16
        processor = AutoProcessor.from_pretrained(self.model_name, cache_dir=self.cache_dir, local_files_only=self.offline_mode)
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.model_name, trust_remote_code=True, torch_dtype=dtype,
            device_map="auto", cache_dir=self.cache_dir, local_files_only=self.offline_mode
        )
        model.eval()
        print("✅ Model loaded successfully from local cache!")
        return model, processor
