from __future__ import annotations

from bs4 import BeautifulSoup


def extract_page_features(html: str, url: str) -> dict:
    """Extract human-visible SEO fields from an HTML response."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    canonical_tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(" ", strip=True)
    h1 = [item.get_text(" ", strip=True) for item in soup.find_all("h1")]
    h2 = [item.get_text(" ", strip=True) for item in soup.find_all("h2")]
    return {
        "url": url,
        "title": title,
        "meta_description": description_tag.get("content", "").strip() if description_tag else "",
        "h1": " | ".join(h1),
        "h2": " | ".join(h2),
        "text": text,
        "word_count": len(text.split()),
        "canonical": canonical_tag.get("href", "").strip() if canonical_tag else "",
    }

