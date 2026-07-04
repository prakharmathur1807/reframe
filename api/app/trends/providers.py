"""Trends provider — fetch current trending topics from public RSS feeds.

Sources (all publicly accessible, no auth required):
  - Google Trends RSS (daily trends)
  - YouTube trending RSS (top videos)

Results are cached in memory for 30 minutes to avoid hammering the feeds.
"""

from __future__ import annotations

import logging
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

logger = logging.getLogger("reframe.trends")

CACHE_TTL = 1800  # 30 minutes


@dataclass
class TrendItem:
    keyword: str
    category: str
    score: int          # 0-100 relative score
    hashtags: list[str] = field(default_factory=list)


_cache: dict[str, tuple[float, list[TrendItem]]] = {}


def get_trends(country: str = "US") -> list[TrendItem]:
    now = time.time()
    if country in _cache and now - _cache[country][0] < CACHE_TTL:
        return _cache[country][1]

    items: list[TrendItem] = []
    items.extend(_fetch_google_trends(country))
    items.extend(_fetch_youtube_trending())

    # Score by position (first = most trending)
    for i, item in enumerate(items):
        item.score = max(10, 100 - i * 3)

    _cache[country] = (now, items[:40])
    return items[:40]


def _fetch_google_trends(country: str = "US") -> list[TrendItem]:
    url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={country}"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        root = ET.fromstring(raw)
        items: list[TrendItem] = []
        for item in root.iter("item"):
            title_el = item.find("title")
            if title_el is None or not title_el.text:
                continue
            keyword = title_el.text.strip()
            ht_text = item.findtext("{https://trends.google.com/trends/trendingsearches/daily}approx_traffic") or ""
            items.append(TrendItem(
                keyword=keyword,
                category="Trending Search",
                score=80,
                hashtags=[f"#{re.sub(r'[^a-zA-Z0-9]', '', keyword)}"],
            ))
        return items[:20]
    except Exception as exc:
        logger.debug("Google Trends fetch failed: %s", exc)
        return []


def _fetch_youtube_trending() -> list[TrendItem]:
    # YouTube trending feed (publicly accessible)
    url = "https://www.youtube.com/feeds/videos.xml?chart=SC&hl=en&gl=US"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(raw)
        items: list[TrendItem] = []
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            if title_el is None or not title_el.text:
                continue
            keyword = title_el.text.strip()
            items.append(TrendItem(
                keyword=keyword,
                category="YouTube Trending",
                score=70,
                hashtags=["#YouTube", "#Trending"],
            ))
        return items[:20]
    except Exception as exc:
        logger.debug("YouTube trending fetch failed: %s", exc)
        return []
