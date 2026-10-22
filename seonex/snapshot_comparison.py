from __future__ import annotations

from .storage import pair_key


def compare_snapshots(before: dict, after: dict) -> list[dict]:
    before_pairs = {pair_key(item["page_a"], item["page_b"]): item for item in before["payload"]["conflicts"]}
    after_pairs = {pair_key(item["page_a"], item["page_b"]): item for item in after["payload"]["conflicts"]}
    comparisons = []
    for key in sorted(before_pairs.keys() & after_pairs.keys()):
        old, new = before_pairs[key], after_pairs[key]
        change = new["combined_score"] - old["combined_score"]
        comparisons.append({"pair": key, "before_risk": old["combined_score"], "after_risk": new["combined_score"], "risk_change": change,
                            "direction": "Decreased" if change < -0.001 else "Increased" if change > 0.001 else "Unchanged"})
    return comparisons
