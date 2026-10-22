from __future__ import annotations


def explain_conflict(conflict: dict) -> str:
    keyword = conflict["keyword_similarity"] * 100
    if not conflict["semantic_available"]:
        return (f"Keyword overlap is {keyword:.0f}%. Semantic analysis was unavailable, so this is a keyword-only review signal — "
                "not evidence of cannibalization. Check whether both pages answer the same search need.")
    semantic = (conflict["semantic_similarity"] or 0) * 100
    evidence = "substantial" if keyword >= 25 and semantic >= 45 else "some"
    return (f"These pages show {evidence} measured overlap: {keyword:.0f}% keyword similarity and {semantic:.0f}% semantic similarity. "
            "They may target related topics. Review search intent before changing or merging either page; this diagnostic score is not a Google ranking signal.")

