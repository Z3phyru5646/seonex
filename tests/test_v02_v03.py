from seonex.intent_classifier import classify_intent, intent_similarity
from seonex.recommendation_engine import recommend
from seonex.snapshot_comparison import compare_snapshots


def test_intent_classifier_and_relationship_are_explainable():
    result = classify_intent({"title": "How to plan an event", "h1": "Event planning", "url": "/guide", "text": ""})
    assert result.label == "Informational"
    assert "how to" in result.evidence
    assert intent_similarity("Informational", "Comparison") == (0.65, "Related intent")


def test_recommendation_requires_evidence_for_consolidation():
    result = recommend({"combined_score": .81, "intent_relationship": "Same intent", "title_similarity": .7, "heading_similarity": .7})
    assert result["action"] == "CONSOLIDATE"
    assert "review" in result["human_review"].lower()


def test_snapshot_pair_matching_only_compares_shared_pairs():
    before = {"payload": {"conflicts": [{"page_a": "/a", "page_b": "/b", "combined_score": .8}, {"page_a": "/a", "page_b": "/c", "combined_score": .4}]}}
    after = {"payload": {"conflicts": [{"page_a": "/a", "page_b": "/b", "combined_score": .3}, {"page_a": "/a", "page_b": "/d", "combined_score": .4}]}}
    comparison = compare_snapshots(before, after)
    assert len(comparison) == 1
    assert comparison[0]["direction"] == "Decreased"
