
import torch, gc, os
from transformers import AutoModel, AutoTokenizer


MODEL_PATH = "./models/MiniCPM-V-2_6"
# quant_config = BitsAndBytesConfig(
#     load_in_4bit=True,   # 🔥 safer than 8-bit for T4
#     bnb_4bit_compute_dtype=torch.float16
# )
import torch.nn as nn

# 🔥 Patch all nn.Module to have this attribute
if not hasattr(nn.Module, "all_tied_weights_keys"):
    nn.Module.all_tied_weights_keys = {}



model = None
tokenizer = None
def load_model():
    global model, tokenizer

    if model is not None and tokenizer is not None:
        return model, tokenizer
    
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. "
            "Please download MiniCPM-V-2_6 manually first."
        )

    gc.collect()
    torch.cuda.empty_cache()

    model = AutoModel.from_pretrained(
        MODEL_PATH,
        trust_remote_code=True,
        local_files_only=True,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa"
    )

    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATH,
        trust_remote_code=True
    )

    print("Model loaded successfully ✅")
    return model, tokenizer