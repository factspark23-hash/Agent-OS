"""Agent profile definitions - MiroFish-inspired personas adapted for web search."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchProfile:
    """Definition of a search agent profile."""
    key: str
    name: str
    expertise: str
    description: str
    preferred_sources: list[str]
    search_depth: str  # quick, medium, thorough
    query_style: str  # factual_direct, specific_targeted, technical_precise, exploratory_detailed, broad_exploratory
    keywords: list[str]
    priority: int = 0


SEARCH_PROFILES: dict[str, SearchProfile] = {
    "news_hound": SearchProfile(
        key="news_hound",
        name="News Hound",
        expertise="current_events",
        description="Specializes in finding latest news, breaking stories, and current events from reputable news sources.",
        preferred_sources=["reuters.com", "apnews.com", "bbc.com", "cnn.com", "ndtv.com", "timesofindia.indiatimes.com"],
        search_depth="quick",
        query_style="factual_direct",
        keywords=["news", "latest", "breaking", "update", "headline", "today", "current events", "developing"],
        priority=8,
    ),
    "deep_researcher": SearchProfile(
        key="deep_researcher",
        name="Deep Researcher",
        expertise="academic_technical",
        description="Excels at in-depth research, finding academic papers, technical documentation, and comprehensive analyses.",
        preferred_sources=["scholar.google.com", "arxiv.org", "researchgate.net", "medium.com", "wikipedia.org"],
        search_depth="thorough",
        query_style="exploratory_detailed",
        keywords=["research", "study", "analysis", "paper", "academic", "detailed", "comprehensive", "in-depth"],
        priority=5,
    ),
    "price_checker": SearchProfile(
        key="price_checker",
        name="Price Checker",
        expertise="commerce_pricing",
        description="Finds current prices, deals, comparisons, and reviews for products and services.",
        preferred_sources=["amazon.com", "flipkart.com", "price.com", "shopping.google.com", "ebay.com"],
        search_depth="quick",
        query_style="specific_targeted",
        keywords=["price", "cost", "buy", "cheap", "discount", "deal", "offer", "review", "compare", "vs"],
        priority=9,
    ),
    "tech_scanner": SearchProfile(
        key="tech_scanner",
        name="Tech Scanner",
        expertise="technology_software",
        description="Scans tech blogs, documentation, GitHub, and Stack Overflow for technical information and solutions.",
        preferred_sources=["github.com", "stackoverflow.com", "docs.python.org", "developer.mozilla.org", "dev.to"],
        search_depth="medium",
        query_style="technical_precise",
        keywords=["tech", "software", "programming", "api", "code", "github", "bug", "debug", "install", "python", "javascript"],
        priority=7,
    ),
    "generalist": SearchProfile(
        key="generalist",
        name="Generalist",
        expertise="general",
        description="Versatile search agent that handles a wide range of queries with balanced coverage across multiple sources.",
        preferred_sources=["wikipedia.org", "reuters.com"],
        search_depth="medium",
        query_style="broad_exploratory",
        keywords=[],
        priority=1,
    ),
}


def get_profile(key: str) -> Optional[SearchProfile]:
    """Get a search profile by key."""
    return SEARCH_PROFILES.get(key)


def get_profiles_for_query(query: str) -> list[SearchProfile]:
    """Get matching profiles for a query based on keyword matching."""
    query_lower = query.lower()
    matched = []

    for profile in SEARCH_PROFILES.values():
        if profile.key == "generalist":
            continue
        for keyword in profile.keywords:
            if keyword in query_lower:
                matched.append(profile)
                break

    matched.sort(key=lambda p: p.priority, reverse=True)

    if not matched:
        matched.append(SEARCH_PROFILES["generalist"])

    return matched


def get_all_profile_keys() -> list[str]:
    """Get all available profile keys."""
    return list(SEARCH_PROFILES.keys())
