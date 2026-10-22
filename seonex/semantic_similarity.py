from __future__ import annotations

import hashlib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

_MODEL = None
_MODEL_ERROR = None
_CACHE: dict[str, np.ndarray] = {}


def _representative_text(page: dict) -> str:
    text = f"{page.get('title', '')}. {page.get('h1', '')}. {page.get('text', '')}".strip()
    return text[:5000]


def model_status() -> tuple[bool, str]:
    return _MODEL is not None, _MODEL_ERROR or "Model ready"


def compute_semantic_similarity(pages: list[dict]) -> tuple[np.ndarray, str | None]:
    global _MODEL, _MODEL_ERROR
    count = len(pages)
    if count < 2:
        return np.zeros((count, count)), None
    try:
        if _MODEL is None:
            from sentence_transformers import SentenceTransformer
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        texts = [_representative_text(page) for page in pages]
        embeddings = []
        missing, missing_positions = [], []
        for position, text in enumerate(texts):
            key = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if key in _CACHE:
                embeddings.append(_CACHE[key])
            else:
                embeddings.append(None)
                missing.append(text or " ")
                missing_positions.append(position)
        if missing:
            generated = _MODEL.encode(missing, normalize_embeddings=True, show_progress_bar=False)
            for pos, vector, text in zip(missing_positions, generated, missing):
                key = hashlib.sha256(text.encode("utf-8")).hexdigest()
                _CACHE[key] = vector
                embeddings[pos] = vector
        return cosine_similarity(np.asarray(embeddings)), None
    except Exception as exc:  # surfaced explicitly in UI; no hidden replacement
        _MODEL_ERROR = str(exc)
        return np.zeros((count, count)), f"Semantic model unavailable: {exc}"

