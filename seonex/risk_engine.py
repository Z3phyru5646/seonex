from __future__ import annotations

import re

from .intent_classifier import intent_similarity
from .recommendation_engine import recommend

DEFAULT_KEYWORD_WEIGHT = 0.5
DEFAULT_SEMANTIC_WEIGHT = 0.5
DEFAULT_WEIGHTS = {"keyword": 0.25, "semantic": 0.30, "intent": 0.15, "title": 0.10, "heading": 0.10, "content": 0.10}


def validate_weights(keyword_weight: float, semantic_weight: float) -> None:
    if keyword_weight < 0 or semantic_weight < 0 or abs(keyword_weight + semantic_weight - 1.0) > 1e-9:
        raise ValueError("Keyword and semantic weights must be non-negative and sum to 1.")


def combined_score(keyword_similarity: float, semantic_similarity: float, keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
                   semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT) -> float:
    validate_weights(keyword_weight, semantic_weight)
    return round(max(0.0, min(1.0, keyword_weight * keyword_similarity + semantic_weight * semantic_similarity)), 10)


def validate_hybrid_weights(weights: dict[str, float]) -> None:
    if set(weights) != set(DEFAULT_WEIGHTS) or any(value < 0 for value in weights.values()) or abs(sum(weights.values()) - 1) > 1e-9:
        raise ValueError("Hybrid weights must contain keyword, semantic, intent, title, heading and content, and sum to 1.")


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", (value or "").lower()))


def _overlap(first: str, second: str) -> float:
    left, right = _tokens(first), _tokens(second)
    return len(left & right) / len(left | right) if left or right else 0.0


def build_conflicts(pages: list[dict], keyword_pairs: list[dict], semantic_matrix, semantic_error: str | None,
                    keyword_weight: float = DEFAULT_KEYWORD_WEIGHT, semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT,
                    weights: dict[str, float] | None = None) -> list[dict]:
    weights = weights or DEFAULT_WEIGHTS
    validate_hybrid_weights(weights)
    conflicts = []
    for pair in keyword_pairs:
        first, second = pages[pair["i"]], pages[pair["j"]]
        semantic = float(semantic_matrix[pair["i"], pair["j"]]) if not semantic_error else None
        intent_score, intent_relationship = intent_similarity(first.get("intent", "Unknown/Needs Review"), second.get("intent", "Unknown/Needs Review"))
        signals = {"keyword": pair["keyword_similarity"], "semantic": semantic, "intent": intent_score,
                   "title": _overlap(first.get("title", ""), second.get("title", "")),
                   "heading": _overlap(f"{first.get('h1', '')} {first.get('h2', '')}", f"{second.get('h1', '')} {second.get('h2', '')}"),
                   "content": _overlap(first.get("text", ""), second.get("text", ""))}
        available_weights = {name: weight for name, weight in weights.items() if signals[name] is not None}
        divisor = sum(available_weights.values())
        score = sum(signals[name] * weight / divisor for name, weight in available_weights.items())
        item = {
            "page_a": pages[pair["i"]]["url"], "page_b": pages[pair["j"]]["url"],
            "title_a": first.get("title", ""), "title_b": second.get("title", ""),
            "keyword_similarity": signals["keyword"], "semantic_similarity": semantic, "intent_similarity": intent_score,
            "title_similarity": signals["title"], "heading_similarity": signals["heading"], "content_overlap": signals["content"],
            "intent_a": first.get("intent", "Unknown/Needs Review"), "intent_b": second.get("intent", "Unknown/Needs Review"),
            "intent_relationship": intent_relationship, "combined_score": round(score, 10), "shared_terms": ", ".join(pair["shared_terms"]),
            "semantic_available": not bool(semantic_error),
            "analysis_mode": "hybrid" if not semantic_error else "hybrid_without_semantic",
        }
        item.update(recommend(item))
        conflicts.append(item)
    return sorted(conflicts, key=lambda item: item["combined_score"], reverse=True)

