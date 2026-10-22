from __future__ import annotations

import re
import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", (value or "").lower())).strip()


def compute_keyword_similarity(pages: list[dict]) -> tuple[np.ndarray, list[dict], TfidfVectorizer | None]:
    documents = [clean_text(f"{p.get('title', '')} {p.get('h1', '')} {p.get('h2', '')} {p.get('text', '')}") for p in pages]
    if len(documents) < 2 or not any(documents):
        return np.zeros((len(pages), len(pages))), [], None
    vectorizer = TfidfVectorizer(stop_words=list(ENGLISH_STOP_WORDS), ngram_range=(1, 2), max_features=4000)
    try:
        matrix = vectorizer.fit_transform(documents)
    except ValueError:
        return np.zeros((len(pages), len(pages))), [], None
    similarity = cosine_similarity(matrix)
    names = np.array(vectorizer.get_feature_names_out())
    pairs = []
    for first in range(len(pages)):
        for second in range(first + 1, len(pages)):
            overlap = matrix[first].multiply(matrix[second]).toarray()[0]
            term_indexes = overlap.argsort()[::-1][:6]
            terms = [names[index] for index in term_indexes if overlap[index] > 0]
            pairs.append({"i": first, "j": second, "keyword_similarity": float(similarity[first, second]), "shared_terms": terms})
    return similarity, pairs, vectorizer

