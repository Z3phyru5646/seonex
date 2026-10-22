import numpy as np
from seonex.keyword_similarity import compute_keyword_similarity
from seonex.risk_engine import combined_score, validate_weights


def test_related_text_is_more_similar_than_unrelated_text():
    pages = [
        {"title": "Event planning guide", "text": "plan an event with event venue and guest checklist", "h1": "Event planning"},
        {"title": "Plan your event", "text": "event planning checklist for venue guests and schedule", "h1": "Event guide"},
        {"title": "Contact us", "text": "send a message to our team", "h1": "Contact"},
    ]
    matrix, _, _ = compute_keyword_similarity(pages)
    assert matrix[0, 1] > matrix[0, 2]


def test_score_and_weight_validation():
    assert combined_score(0.4, 0.8) == 0.6
    try:
        validate_weights(0.8, 0.3)
    except ValueError:
        pass
    else:
        assert False

