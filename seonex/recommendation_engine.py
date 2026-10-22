"""Evidence-led suggestions; never modifies pages or URLs."""
from __future__ import annotations


def recommend(conflict: dict, high_threshold: float = 0.72, medium_threshold: float = 0.45) -> dict:
    score = conflict["combined_score"]
    intent = conflict.get("intent_relationship", "Unknown intent relationship")
    same_intent = intent == "Same intent"
    title_heading_overlap = (conflict.get("title_similarity", 0) + conflict.get("heading_similarity", 0)) / 2
    if score >= high_threshold and same_intent and title_heading_overlap >= 0.45:
        return {
            "action": "CONSOLIDATE",
            "reason": "High measured overlap, the same intent, and similar titles/headings indicate potentially redundant coverage.",
            "human_review": "Human review required: choose a preferred URL and compare unique sections before making any redirect or merge decision.",
        }
    if score >= medium_threshold and intent in {"Same intent", "Related intent"}:
        return {
            "action": "DIFFERENTIATE",
            "reason": "The pages have meaningful similarity but may retain distinct value or audience needs.",
            "human_review": "Clarify primary intent, title, H1, and unique sections; do not merge solely from this score.",
        }
    return {
        "action": "KEEP",
        "reason": "Measured overlap is limited or the pages serve different/uncertain intents.",
        "human_review": "Keep both pages unless a content review identifies a clearer user-need overlap.",
    }
