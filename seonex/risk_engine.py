from __future__ import annotations

DEFAULT_KEYWORD_WEIGHT = 0.5
DEFAULT_SEMANTIC_WEIGHT = 0.5


def validate_weights(keyword_weight: float, semantic_weight: float) -> None:
    if keyword_weight < 0 or semantic_weight < 0 or abs(keyword_weight + semantic_weight - 1.0) > 1e-9:
        raise ValueError("Keyword and semantic weights must be non-negative and sum to 1.")


def combined_score(keyword_similarity: float, semantic_similarity: float, keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
                   semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT) -> float:
    validate_weights(keyword_weight, semantic_weight)
    return round(max(0.0, min(1.0, keyword_weight * keyword_similarity + semantic_weight * semantic_similarity)), 10)


def build_conflicts(pages: list[dict], keyword_pairs: list[dict], semantic_matrix, semantic_error: str | None,
                    keyword_weight: float = DEFAULT_KEYWORD_WEIGHT, semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT) -> list[dict]:
    conflicts = []
    for pair in keyword_pairs:
        semantic = float(semantic_matrix[pair["i"], pair["j"]]) if not semantic_error else None
        score = combined_score(pair["keyword_similarity"], semantic or 0, keyword_weight, semantic_weight) if not semantic_error else pair["keyword_similarity"]
        conflicts.append({
            "page_a": pages[pair["i"]]["url"], "page_b": pages[pair["j"]]["url"],
            "title_a": pages[pair["i"]].get("title", ""), "title_b": pages[pair["j"]].get("title", ""),
            "keyword_similarity": pair["keyword_similarity"], "semantic_similarity": semantic,
            "combined_score": score, "shared_terms": ", ".join(pair["shared_terms"]),
            "semantic_available": not bool(semantic_error),
            "analysis_mode": "hybrid" if not semantic_error else "keyword_only",
        })
    return sorted(conflicts, key=lambda item: item["combined_score"], reverse=True)

