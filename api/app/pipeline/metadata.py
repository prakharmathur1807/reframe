"""Metadata generation stage — titles, hooks, hashtags, descriptions per clip.

Fully local: uses heuristics + keyword extraction — no external APIs.
"""

from __future__ import annotations

import re
from collections import Counter

from .context import JobContext

STAGE = "metadata"

_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "it", "is", "was", "are", "i", "you", "we", "they",
    "this", "that", "have", "had", "be", "been", "do", "did", "will",
    "would", "could", "should", "my", "your", "his", "her", "its",
}

_HASHTAG_MAP = {
    "ai": "#AI", "learn": "#Learning", "money": "#Finance",
    "health": "#Health", "workout": "#Fitness", "success": "#Success",
    "business": "#Business", "life": "#LifeAdvice", "tips": "#Tips",
    "hack": "#LifeHack", "food": "#Food", "travel": "#Travel",
    "tech": "#Tech", "coding": "#Coding", "startup": "#Startup",
}


def run(ctx: JobContext) -> None:
    clips: list[dict] = ctx.artifacts.get("clip_candidates", [])
    transcript: str = ctx.artifacts.get("transcript_text", "")

    for clip in clips:
        text = clip.get("text", "")
        clip["metadata"] = _generate(text, clip)

    # Global video metadata
    ctx.artifacts["video_metadata"] = _generate_global(transcript)
    ctx.artifacts["metadata_done"] = True


def _generate(text: str, clip: dict) -> dict:
    keywords = _extract_keywords(text, top=8)
    hashtags = _extract_hashtags(text, keywords)

    score = clip.get("viral_score", 50)
    if score >= 80:
        cta = "You need to see this 👀"
    elif score >= 60:
        cta = "Watch till the end 🔥"
    else:
        cta = "Drop your thoughts below 💬"

    yt_title = _yt_title(clip.get("title", ""), score)
    reel_caption = f"{clip.get('hook', text[:80])} {cta}\n\n{' '.join(hashtags[:8])}"
    description = (
        f"{text[:200]}…\n\n"
        f"📌 Keywords: {', '.join(keywords[:5])}\n"
        f"🔥 Viral Score: {score}/100\n\n"
        f"{' '.join(hashtags)}"
    )

    return {
        "youtube_title": yt_title,
        "reel_caption": reel_caption,
        "hashtags": hashtags,
        "seo_keywords": keywords,
        "description": description,
        "cta": cta,
    }


def _generate_global(transcript: str) -> dict:
    keywords = _extract_keywords(transcript, top=15)
    hashtags = _extract_hashtags(transcript, keywords)
    return {
        "seo_keywords": keywords,
        "hashtags": hashtags,
        "suggested_topics": keywords[:5],
    }


def _extract_keywords(text: str, top: int = 8) -> list[str]:
    words = re.findall(r"\b[a-z]{4,}\b", text.lower())
    filtered = [w for w in words if w not in _STOP_WORDS]
    freq = Counter(filtered)
    return [w for w, _ in freq.most_common(top)]


def _extract_hashtags(text: str, keywords: list[str]) -> list[str]:
    tags: list[str] = []
    t = text.lower()
    for kw, tag in _HASHTAG_MAP.items():
        if kw in t and tag not in tags:
            tags.append(tag)
    for kw in keywords[:5]:
        tag = "#" + kw.capitalize()
        if tag not in tags:
            tags.append(tag)
    tags += ["#Shorts", "#Reels", "#TikTok", "#ViralVideo", "#ContentCreator"]
    return list(dict.fromkeys(tags))[:15]


def _yt_title(base: str, score: int) -> str:
    if not base:
        return "Watch This Now 🔥"
    prefixes = {
        80: ["🚨 ", "⚡ ", "🔥 "],
        60: ["✅ ", "👉 ", "💡 "],
        0: ["", "📌 "],
    }
    prefix = ""
    for threshold, options in sorted(prefixes.items(), reverse=True):
        if score >= threshold:
            prefix = options[score % len(options)]
            break
    title = base[:55]
    return f"{prefix}{title}"
