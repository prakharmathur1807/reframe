"""Match a video transcript against current trending topics."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .providers import TrendItem


@dataclass
class TrendMatch:
    keyword: str
    category: str
    trend_score: int
    relevance_pct: int
    hashtags: list[str]


def match_transcript(
    transcript: str,
    trends: list[TrendItem],
    top_n: int = 5,
) -> list[TrendMatch]:
    if not transcript or not trends:
        return []

    t_lower = transcript.lower()
    t_words = set(re.findall(r"\b\w{3,}\b", t_lower))

    matches: list[TrendMatch] = []
    for trend in trends:
        kw_words = set(re.findall(r"\b\w{3,}\b", trend.keyword.lower()))
        if not kw_words:
            continue
        overlap = len(kw_words & t_words)
        relevance = min(int(overlap / len(kw_words) * 100), 100)
        if relevance > 0:
            matches.append(TrendMatch(
                keyword=trend.keyword,
                category=trend.category,
                trend_score=trend.score,
                relevance_pct=relevance,
                hashtags=trend.hashtags,
            ))

    matches.sort(key=lambda m: -(m.relevance_pct * 0.6 + m.trend_score * 0.4))
    return matches[:top_n]
