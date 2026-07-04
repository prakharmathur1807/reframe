"""Trends endpoint — serve trending topics and transcript matching."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..trends.providers import get_trends
from ..trends.matcher import match_transcript

router = APIRouter(tags=["trends"])


class TranscriptMatchRequest(BaseModel):
    transcript: str
    country: str = "US"


@router.get("/trends")
async def trends(country: str = "US") -> dict:
    items = get_trends(country)
    return {
        "trends": [
            {
                "keyword": t.keyword,
                "category": t.category,
                "score": t.score,
                "hashtags": t.hashtags,
            }
            for t in items
        ],
        "count": len(items),
    }


@router.post("/trends/match")
async def match(body: TranscriptMatchRequest) -> dict:
    trends_list = get_trends(body.country)
    matches = match_transcript(body.transcript, trends_list)
    return {
        "matches": [
            {
                "keyword": m.keyword,
                "category": m.category,
                "trendScore": m.trend_score,
                "relevancePct": m.relevance_pct,
                "hashtags": m.hashtags,
            }
            for m in matches
        ],
        "hasMatches": len(matches) > 0,
    }
