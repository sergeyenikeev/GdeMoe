"""
Image/text embeddings via OpenCLIP.
Lazy import torch/open_clip to avoid startup crashes if deps are missing.
"""
from functools import lru_cache

import numpy as np


@lru_cache(maxsize=1)
def _load_clip():
    try:
        import torch
        import open_clip
    except ImportError as exc:  # noqa: BLE001
        raise ImportError("open_clip/torch not installed") from exc

    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k"
    )
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    return model, preprocess, tokenizer, device


def image_embedding(pil_image) -> np.ndarray:
    import torch

    model, preprocess, _, device = _load_clip()
    img = preprocess(pil_image).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = model.encode_image(img)
        emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb.cpu().numpy().astype("float32")[0]


def text_embedding(text: str) -> np.ndarray:
    import torch

    model, _, tokenizer, device = _load_clip()
    tokens = tokenizer([text]).to(device)
    with torch.no_grad():
        emb = model.encode_text(tokens)
        emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb.cpu().numpy().astype("float32")[0]
