from __future__ import annotations

from sklearn.metrics import precision_recall_fscore_support


def evaluate_binary_conflicts(conflicts: list[dict], labels: dict[str, str], pair_key, threshold: float = 0.5) -> dict | None:
    truth, predictions = [], []
    for item in conflicts:
        label = labels.get(pair_key(item["page_a"], item["page_b"]))
        if label is None:
            continue
        truth.append(label == "Conflict")
        predictions.append(item["combined_score"] >= threshold)
    if not truth:
        return None
    precision, recall, f1, _ = precision_recall_fscore_support(truth, predictions, average="binary", zero_division=0)
    return {"labeled_pairs": len(truth), "precision": precision, "recall": recall, "f1": f1}
