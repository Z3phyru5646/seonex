import pytest
from seonex.crawler import WebsiteCrawler, _resolves_to_private_address, normalize_url
from seonex.seo_extractor import extract_page_features


def test_normalize_url_removes_fragments_and_tracking():
    assert normalize_url("HTTPS://Example.com/path/?utm_source=x&b=2#part") == "https://example.com/path?b=2"


def test_local_requires_explicit_demo_mode():
    try:
        WebsiteCrawler("http://localhost:8000")
    except ValueError:
        pass
    else:
        assert False


def test_private_resolution_is_detected(monkeypatch):
    monkeypatch.setattr("seonex.crawler.socket.getaddrinfo", lambda *_: [(None, None, None, None, ("127.0.0.1", 0))])
    assert _resolves_to_private_address("example.test")


def test_extractor_handles_missing_metadata():
    page = extract_page_features("<html><body><main><h1>Hello</h1><p>Useful words</p></main></body></html>", "https://example.com")
    assert page["title"] == ""
    assert page["h1"] == "Hello"
    # Main visible text includes the H1 as well as the paragraph.
    assert page["word_count"] == 3
