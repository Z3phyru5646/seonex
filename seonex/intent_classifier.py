"""Transparent, replaceable search-intent rules for SEONEX."""
from __future__ import annotations

from dataclasses import dataclass


INTENTS = ("Informational", "Comparison", "Action/Transactional", "Navigational", "Unknown/Needs Review")


@dataclass(frozen=True)
class IntentResult:
    label: str
    evidence: tuple[str, ...]


RULES = (
    ("Comparison", (" vs ", "versus", "compare", "comparison", "which ")),
    ("Action/Transactional", ("register", "book", "buy", "contact", "sign up", "download", "get started")),
    ("Navigational", ("contact", "about us", "login", "location", "directions")),
    ("Informational", ("guide", "how to", "what is", "ideas", "tips", "planning", "learn")),
)


def classify_intent(page: dict, override: str | None = None) -> IntentResult:
    """Classify title, headings and URL using inspectable keyword evidence."""
    if override in INTENTS:
        return IntentResult(override, ("Manual reviewer override",))
    source = " ".join(str(page.get(field, "")) for field in ("url", "title", "h1", "h2", "text")).lower()
    for label, patterns in RULES:
        matched = tuple(pattern.strip() for pattern in patterns if pattern in source)
        if matched:
            return IntentResult(label, matched[:3])
    return IntentResult("Unknown/Needs Review", ("No transparent rule matched",))


def intent_similarity(first: str, second: str) -> tuple[float, str]:
    if first == second and first != "Unknown/Needs Review":
        return 1.0, "Same intent"
    if "Unknown/Needs Review" in {first, second}:
        return 0.35, "Unknown intent relationship"
    if {first, second} <= {"Informational", "Comparison"}:
        return 0.65, "Related intent"
    return 0.15, "Different intent"
