from __future__ import annotations

import ipaddress
import socket
import time
from collections import deque
from dataclasses import dataclass, field
from urllib import robotparser
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from .seo_extractor import extract_page_features


USER_AGENT = "SEONEX/0.1 (+authorized SEO diagnostics)"


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(sorted((key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
                            if not key.lower().startswith("utm_")))
    return urlunparse((scheme, host + port, path, "", query, ""))


def _is_private_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_private or ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _resolves_to_private_address(host: str) -> bool:
    """Reject external hostnames that resolve to private or loopback addresses."""
    try:
        addresses = {entry[4][0] for entry in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve host: {host}") from exc
    for address in addresses:
        parsed = ipaddress.ip_address(address)
        if parsed.is_private or parsed.is_loopback or parsed.is_link_local or parsed.is_reserved:
            return True
    return False


@dataclass
class CrawlResult:
    pages: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    log: list[str] = field(default_factory=list)


class WebsiteCrawler:
    """Small, deliberately polite crawler restricted to one authorised origin."""

    def __init__(self, base_url: str, max_pages: int = 20, timeout: int = 10, delay: float = 0.15,
                 allow_local_demo: bool = False, progress_callback=None):
        self.base_url = normalize_url(base_url)
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Enter a complete http:// or https:// URL.")
        host = parsed.hostname or ""
        if (_is_private_host(host) or _resolves_to_private_address(host)) and not allow_local_demo:
            raise ValueError("Private/local addresses are allowed only in explicit local-demo mode.")
        self.origin = (parsed.scheme, parsed.netloc.lower())
        self.max_pages, self.timeout, self.delay = max(1, int(max_pages)), timeout, delay
        self.progress_callback = progress_callback
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme == self.origin[0] and parsed.netloc.lower() == self.origin[1]

    def _robots(self) -> robotparser.RobotFileParser:
        robots = robotparser.RobotFileParser()
        robots.set_url(urljoin(self.base_url + "/", "/robots.txt"))
        try:
            robots.read()
        except Exception:
            pass  # A missing robots file is not an instruction to block all crawling.
        return robots

    def crawl(self) -> CrawlResult:
        result, visited, queue = CrawlResult(), set(), deque([(self.base_url, 0)])
        robots = self._robots()
        while queue and len(result.pages) < self.max_pages:
            raw_url, depth = queue.popleft()
            url = normalize_url(raw_url)
            if url in visited or not self._allowed(url):
                continue
            visited.add(url)
            if not robots.can_fetch(USER_AGENT, url):
                result.log.append(f"Skipped by robots.txt: {url}")
                continue
            try:
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                final_url = normalize_url(response.url)
                if not self._allowed(final_url):
                    raise requests.RequestException("Redirect left the authorised domain")
                if response.status_code >= 400:
                    raise requests.HTTPError(f"HTTP {response.status_code}")
                content_type = response.headers.get("content-type", "")
                if "html" not in content_type.lower():
                    result.log.append(f"Skipped non-HTML: {url}")
                    continue
                page = extract_page_features(response.text, final_url)
                page["status"] = response.status_code
                page["internal_links"] = []
                soup = BeautifulSoup(response.text, "html.parser")
                for anchor in soup.find_all("a", href=True):
                    link = normalize_url(urljoin(final_url, anchor["href"]))
                    if self._allowed(link):
                        page["internal_links"].append(link)
                        if link not in visited:
                            queue.append((link, depth + 1))
                page["internal_links"] = sorted(set(page["internal_links"]))
                result.pages.append(page)
                result.log.append(f"Crawled {len(result.pages)}/{self.max_pages}: {final_url}")
            except (requests.RequestException, ValueError) as exc:
                result.errors.append({"url": url, "error": str(exc)})
                result.log.append(f"Failed: {url} — {exc}")
            if self.progress_callback:
                self.progress_callback(len(result.pages), self.max_pages, result.log[-1])
            time.sleep(self.delay)
        return result

