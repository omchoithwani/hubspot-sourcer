"""
DuckDuckGo HTML scraper.
Hits html.duckduckgo.com, parses result URLs, strips each to root domain.
Rotates user agents and waits 2-4 s per request to stay polite.
"""

import random
import time
from urllib.parse import urlparse, unquote, parse_qs

import requests
import tldextract
from bs4 import BeautifulSoup

DDG_URL = "https://html.duckduckgo.com/html/"
REQUEST_TIMEOUT = 20

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]


def scrape_domains(query: str) -> list[str]:
    """
    Search DuckDuckGo for *query* and return a deduplicated list of root domains
    found in the results (e.g. 'example.com', not 'https://www.example.com/page').
    Returns an empty list on any network or parse failure.
    """
    time.sleep(random.uniform(2, 4))

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://duckduckgo.com/",
    }

    try:
        resp = requests.get(
            DDG_URL,
            params={"q": query, "kl": "us-en"},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return []

    return _parse_domains(resp.text)


def _parse_domains(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    domains: list[str] = []

    # Primary: visible URL spans
    for tag in soup.select("span.result__url, a.result__url"):
        text = tag.get_text(strip=True)
        domain = _to_root_domain(text)
        if domain:
            domains.append(domain)

    # Fallback: decode uddg redirect param from result links
    if not domains:
        for tag in soup.select("a.result__a"):
            href = tag.get("href", "")
            if "uddg=" in href:
                qs = parse_qs(urlparse(href).query)
                raw_url = unquote(qs.get("uddg", [""])[0])
                domain = _to_root_domain(raw_url)
                if domain:
                    domains.append(domain)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for d in domains:
        if d not in seen:
            seen.add(d)
            unique.append(d)
    return unique


def _to_root_domain(url: str) -> str:
    """Strip a URL or bare hostname down to its registered root domain."""
    url = url.strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    ext = tldextract.extract(url)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return ""
