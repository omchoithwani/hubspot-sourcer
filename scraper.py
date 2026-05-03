"""
DuckDuckGo HTML scraper — two-pass company discovery.

Pass 1: Search DDG with the user's query plus site-exclusions for the
        noisiest aggregators. Results from non-blacklisted domains go
        straight to the output. Results from aggregator / list pages are
        queued for pass 2.

Pass 2: Visit each queued page (e.g. "Top 20 fintech startups in NYC"),
        pull every outbound link, and extract company domains from them.

This means we get actual company homepages even when DDG's top results
are directories and list articles.
"""

import random
import time
from urllib.parse import urlparse, unquote, parse_qs

import requests
import tldextract
from bs4 import BeautifulSoup

DDG_URL = "https://html.duckduckgo.com/html/"
SEARCH_TIMEOUT = 20
PASS2_TIMEOUT = 12
MAX_PASS2_PAGES = 6  # how many aggregator pages we'll visit per run

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

# Domains that are directories, platforms, social networks, or news sites.
# Results from these domains are queued for pass-2 link extraction rather
# than used directly.
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

# These are excluded directly in the DDG query string to reduce aggregator
# results appearing in pass 1 in the first place.
_DDG_EXCLUDE = [
    "linkedin.com", "crunchbase.com", "yelp.com",
    "glassdoor.com", "bloomberg.com", "reddit.com",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrape_domains(query: str) -> list:
    """
    Return a deduplicated list of root company domains relevant to *query*.
    Uses a two-pass strategy: DDG search then outbound-link extraction from
    aggregator/list pages found in the results.
    """
    time.sleep(random.uniform(2, 4))

    enriched = query + " " + " ".join(f"-site:{s}" for s in _DDG_EXCLUDE)
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://duckduckgo.com/",
    }

    try:
        resp = requests.get(
            DDG_URL,
            params={"q": enriched, "kl": "us-en"},
            headers=headers,
            timeout=SEARCH_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return []

    company_domains, aggregator_urls = _parse_search_results(resp.text)

    # Pass 2: visit aggregator / list pages and harvest company links
    for url in aggregator_urls[:MAX_PASS2_PAGES]:
        time.sleep(random.uniform(1, 2))
        company_domains.extend(_extract_company_links(url))

    return _deduplicate(company_domains)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_search_results(html: str):
    """
    Split DDG results into:
      - company_domains : root domains of non-blacklisted results
      - aggregator_urls : full URLs of blacklisted results (queued for pass 2)
    """
    soup = BeautifulSoup(html, "html.parser")
    company_domains = []
    aggregator_urls = []

    for tag in soup.select("a.result__a"):
        href = tag.get("href", "")
        url = _decode_ddg_href(href)
        if not url:
            continue
        domain = _to_root_domain(url)
        if not domain:
            continue
        if domain in _BLACKLIST:
            aggregator_urls.append(url)
        else:
            company_domains.append(domain)

    # Fallback: use visible URL spans when result__a gives nothing
    if not company_domains and not aggregator_urls:
        for tag in soup.select("span.result__url, a.result__url"):
            text = tag.get_text(strip=True)
            domain = _to_root_domain(text)
            if domain:
                if domain in _BLACKLIST:
                    pass  # can't visit without a full URL
                else:
                    company_domains.append(domain)

    return company_domains, aggregator_urls


def _extract_company_links(url: str) -> list:
    """
    Fetch *url* (an aggregator page or list article) and return all outbound
    company domains linked from it.
    """
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": random.choice(USER_AGENTS)},
            timeout=PASS2_TIMEOUT,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            return []
    except requests.RequestException:
        return []

    page_domain = _to_root_domain(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    domains = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            continue
        domain = _to_root_domain(href)
        if domain and domain != page_domain and domain not in _BLACKLIST:
            domains.append(domain)

    return domains


def _decode_ddg_href(href: str) -> str:
    """Extract the real destination URL from a DuckDuckGo redirect href."""
    if not href:
        return ""
    if "uddg=" in href:
        qs = parse_qs(urlparse(href).query)
        return unquote(qs.get("uddg", [""])[0])
    if href.startswith("http"):
        return href
    return ""


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


def _deduplicate(domains: list) -> list:
    seen = set()
    unique = []
    for d in domains:
        if d not in seen:
            seen.add(d)
            unique.append(d)
    return unique
