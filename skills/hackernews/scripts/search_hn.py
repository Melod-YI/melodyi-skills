"""Search Hacker News for a story matching the given URL.

Uses the Algolia HN Search API to find stories whose URL field
matches the input (after normalization).

Usage:
    python search_hn.py <url>
    python search_hn.py <url> --verbose
"""

import argparse
import logging
import sys
from urllib.parse import urlparse, quote

import requests

logger = logging.getLogger("hn_search")

ALGOLIA_API_URL = "https://hn.algolia.com/api/v1/search"
HN_ITEM_URL = "https://news.ycombinator.com/item?id={id}"
HTTP_TIMEOUT = 15


def normalize_url(raw_url: str) -> str:
    """Normalize a URL for comparison: strip protocol, www prefix, trailing slashes;
    lowercase the hostname; preserve path case, query, and fragment."""
    try:
        parsed = urlparse(raw_url)
    except Exception:
        return raw_url

    host = (parsed.hostname or parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]

    path = parsed.path.rstrip("/") or "/"

    result = host + path
    if parsed.query:
        result += "?" + parsed.query
    if parsed.fragment:
        result += "#" + parsed.fragment
    return result


def search_hn(url: str) -> str | None:
    """Search HN for a story matching *url*. Returns the HN discussion URL or None."""
    query_url = (
        f"{ALGOLIA_API_URL}"
        f"?query={quote(url, safe='')}"
        f"&tags=story"
        f"&restrictSearchableAttributes=url"
    )
    logger.info("Requesting %s", query_url)

    resp = requests.get(query_url, timeout=HTTP_TIMEOUT)
    logger.info("Response status: %s", resp.status_code)

    if resp.status_code == 429:
        print("Error: HN API rate limited (429)", file=sys.stderr)
        sys.exit(1)

    if resp.status_code != 200:
        logger.error("Request failed: %s %s", resp.status_code, resp.text[:200])
        print(f"Error: API returned status {resp.status_code}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    hits = data.get("hits", [])
    logger.info("Got %d hits", len(hits))

    if not hits:
        return None

    normalized_input = normalize_url(url)
    logger.info("Normalized input: %s", normalized_input)

    for hit in hits:
        hit_url = hit.get("url", "")
        normalized_hit = normalize_url(hit_url)
        logger.info("  candidate objectID=%s url=%s normalized=%s",
                     hit.get("objectID"), hit_url, normalized_hit)
        if normalized_hit == normalized_input:
            return HN_ITEM_URL.format(id=hit["objectID"])

    logger.info("No exact match found")
    return None


def main():
    parser = argparse.ArgumentParser(description="Search Hacker News for a story matching a URL")
    parser.add_argument("url", help="Article URL to search for")
    parser.add_argument("--verbose", action="store_true", help="Enable diagnostic logs on stderr")
    args = parser.parse_args()

    if args.verbose:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    result = search_hn(args.url)
    if result:
        print(result)
    else:
        print("无匹配")


if __name__ == "__main__":
    main()
