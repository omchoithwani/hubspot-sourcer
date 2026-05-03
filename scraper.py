"""
DuckDuckGo HTML scraper.
Hits html.duckduckgo.com, parses result URLs, strips each to root domain.
Rotates user agents and waits 2-4 s per request to stay polite.
Filters out known non-company domains (social, news, directories, platforms).
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

# Domains that are directories, platforms, social networks, or news sites —
# never actual target companies.
_BLACKLIST = {
    # Social / professional networks
    "linkedin.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "tiktok.com", "pinterest.com", "snapchat.com",
    # Search / big tech
    "google.com", "bing.com", "yahoo.com", "apple.com",
    "microsoft.com", "amazon.com", "amazonaws.com",
    # Developer platforms
    "github.com", "gitlab.com", "stackoverflow.com", "bitbucket.org",
    # Video / media
    "youtube.com", "vimeo.com", "twitch.tv",
    # Content / blogging platforms
    "medium.com", "substack.com", "wordpress.com", "wordpress.org",
    "blogger.com", "tumblr.com", "ghost.io",
    # News / editorial
    "techcrunch.com", "forbes.com", "bloomberg.com", "reuters.com",
    "wsj.com", "nytimes.com", "businessinsider.com", "theguardian.com",
    "inc.com", "entrepreneur.com", "venturebeat.com", "wired.com",
    # Company directories / databases
    "crunchbase.com", "yelp.com", "glassdoor.com", "indeed.com",
    "angel.co", "angellist.com", "pitchbook.com", "dnb.com",
    "zoominfo.com", "apollo.io", "clearbit.com", "owler.com",
    "manta.com", "yellowpages.com", "bbb.org",
    # Review / comparison sites
    "g2.com", "capterra.com", "getapp.com", "trustpilot.com",
    "trustradius.com", "softwareadvice.com", "producthunt.com",
    # Website builder / hosting platforms
    "wix.com", "squarespace.com", "godaddy.com", "shopify.com",
    "webflow.com", "weebly.com",
    # Tech intelligence / analytics
    "builtwith.com", "similarweb.com", "semrush.com", "ahrefs.com",
    "mywot.com", "netify.ai", "wappalyzer.com",
    # HubSpot itself
    "hubspot.com",
    # Misc
    "reddit.com", "quora.com", "wikipedia.org",
}


def scrape_domains(query: str) -> list:
    """
    Search DuckDuckGo for *query* and return a deduplicated list of root domains
    found in the results (e.g. 'example.com').
    Blacklisted and generic platform domains are excluded automatically.
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


def _parse_domains(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    domains = []

    # Primary: visible URL spans
    for tag in soup.select("span.result__url, a.result__url"):
        text = tag.get_text(strip=True)
        domain = _to_root_domain(text)
        if domain and domain not in _BLACKLIST:
            domains.append(domain)

    # Fallback: decode uddg redirect param from result links
    if not domains:
        for tag in soup.select("a.result__a"):
            href = tag.get("href", "")
            if "uddg=" in href:
                qs = parse_qs(urlparse(href).query)
                raw_url = unquote(qs.get("uddg", [""])[0])
                domain = _to_root_domain(raw_url)
                if domain and domain not in _BLACKLIST:
                    domains.append(domain)

    # Deduplicate while preserving order
    seen = set()
    unique = []
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
