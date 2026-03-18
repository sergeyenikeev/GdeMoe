"""Эмбеддинги изображений и текста через OpenCLIP.

Импорт тяжёлых зависимостей делаем лениво, чтобы backend мог стартовать даже
в окружениях, где CLIP не установлен и доступен только фолбэк-пайплайн.
"""
from functools import lru_cache

import numpy as np


@lru_cache(maxsize=1)
def _load_clip():
    """Лениво поднимает OpenCLIP-модель и сопутствующие объекты."""
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
    """Возвращает нормализованный эмбеддинг изображения.

    Args:
        pil_image (Image.Image): Изображение PIL в любом формате.

    Returns:
        np.ndarray: Вектор из float32 длины 512, нормализованный по L2.
    """
    import torch

    model, preprocess, _, device = _load_clip()
    img = preprocess(pil_image).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = model.encode_image(img)
        emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb.cpu().numpy().astype("float32")[0]


def text_embedding(text: str) -> np.ndarray:
    """Возвращает нормализованный эмбеддинг текстовой строки.

    Args:
        text (str): Исходная строка.

    Returns:
        np.ndarray: Вектор из float32 длины 512, нормализованный по L2.
    """
    import torch

    model, _, tokenizer, device = _load_clip()
    tokens = tokenizer([text]).to(device)
    with torch.no_grad():
        emb = model.encode_text(tokens)
        emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb.cpu().numpy().astype("float32")[0]
