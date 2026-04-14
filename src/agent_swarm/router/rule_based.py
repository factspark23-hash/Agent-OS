"""Tier 1: Rule-based query router using regex patterns and keyword matching."""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class QueryCategory(str, Enum):
    """Query classification categories."""
    NEEDS_WEB = "needs_web"
    NEEDS_KNOWLEDGE = "needs_knowledge"
    NEEDS_CALCULATION = "needs_calculation"
    NEEDS_CODE = "needs_code"
    AMBIGUOUS = "ambiguous"


@dataclass
class QueryClassification:
    """Result of query classification."""
    category: QueryCategory
    confidence: float
    reason: str
    source: str = "rule_based"
    suggested_agents: list[str] = field(default_factory=list)
    search_queries: list[str] = field(default_factory=list)


# Web search patterns - high confidence triggers
WEB_PATTERNS = [
    (r"(?i)\b(latest|recent|current|today|now)\b.{0,20}\b(news|update|price|weather|stock|score|result|release|version)\b", 0.95),
    (r"(?i)\b(news|update|price|weather|stock|score|result|release|version)\b.{0,20}\b(latest|recent|current|today|now)\b", 0.93),
    (r"(?i)\b(this\s+(week|month|year))\b.*\b(news|update|release|event)\b", 0.90),
    (r"(?i)\b(2024|2025|2026)\b.*\b(release|launch|announce|update)\b", 0.88),
    (r"(?i)\b(live|real.?time|realtime)\b", 0.92),
    (r"(?i)\b(stock\s+price|exchange\s+rate|market\s+(cap|price))\b", 0.93),
    (r"(?i)\b(weather|temperature|forecast)\b.*\b(today|now|current|tomorrow)\b", 0.94),
    (r"(?i)\b(score|standings|results?)\b.*\b(game|match|sports|nba|nfl|premier)\b", 0.90),
    (r"(?i)\b(find|search|look\s+up|google|lookup)\b", 0.85),
    (r"(?i)\b(where\s+(to|can|is))\b.*\b(buy|find|download|watch|read)\b", 0.85),
    (r"(?i)\b(how\s+much|what\s+(is\s+the\s+)?price|cost\s+of)\b", 0.88),
    (r"(?i)\b(price|cost|rate)\b.{0,15}\b(compare|comparison|vs|check|of)\b", 0.87),
    (r"(?i)\b(compare|comparison|vs|versus|difference\s+between)\b", 0.80),
    (r"(?i)\b(who\s+(is|are|was))\b.*\b(now|currently|today|ceo|president|owner)\b", 0.87),
    (r"(?i)\b(what\s+(is|are))\b.*\b(new|latest|current|best|top)\b", 0.82),
    (r"(?i)\b(best|top|recommended)\b.*\b(2024|2025|2026|this\s+year)\b", 0.86),
    (r"(?i)\b(release|launch|version|update)\b.{0,20}\b(date|time|schedule|when|latest)\b", 0.87),
    (r"(?i)\b(date|time|when)\b.{0,20}\b(release|launch|version|update)\b", 0.86),
    (r"(?i)\b(near\s+me|nearby|closest)\b", 0.91),
    (r"(?i)\b(hours|open|closed|schedule)\b.*\b(today|now|sunday|monday)\b", 0.89),
    (r"(?i)\b(breaking|developing|urgent|just\s+in)\b", 0.96),
    (r"(?i)\b(outage|down|incident|alert)\b", 0.90),
    (r"(?i)\b(how\s+to\s+(install|setup|configure|deploy|use))\b", 0.82),
    (r"(?i)\b(tutorial|guide|walkthrough|example)\b", 0.78),
    (r"(?i)\b(documentation|docs|api\s+reference)\b", 0.77),
    (r"(?i)\b(download|install|setup)\b.{0,15}\b(latest|version|new|python|node|rust)\b", 0.84),
    (r"(?i)\b(python|javascript|java|typescript|rust|golang|ruby|php)\b.{0,20}\b(install|setup|tutorial|guide|learn)\b", 0.81),
    (r"(?i)\b(news|update|release|announce|launch)\b", 0.75),
    (r"(?i)\b(price|cost|rate|fee)\b", 0.73),
    (r"(?i)\b(download|install|tutorial)\b", 0.72),
]

KNOWLEDGE_PATTERNS = [
    (r"(?i)\b(what\s+is|define|definition\s+of|meaning\s+of|explain)\b", 0.80),
    (r"(?i)\b(how\s+(does|do|to))\b(?!.+\b(now|today|current)\b)", 0.75),
    (r"(?i)\b(why\s+(is|does|do|are|did))\b", 0.70),
    (r"(?i)\b(history\s+of|origin\s+of|who\s+invented|when\s+was.*invented)\b", 0.78),
    (r"(?i)\b(translate|synonym|antonym)\b", 0.85),
    (r"(?i)\b(formula\s+for|equation\s+for)\b", 0.82),
]

CALCULATION_PATTERNS = [
    (r"(?i)\b(calculate|compute|solve|convert)\b", 0.90),
    (r"(?i)\b(\d+)\s*[\+\-\*\/\^]\s*(\d+)", 0.95),
    (r"(?i)\b(sqrt|log|sin|cos|tan|factorial)\b", 0.88),
    (r"(?i)\b(percentage\s+of|percent\s+change)\b", 0.85),
    (r"(?i)\b(convert)\b.*\b(to|into|in)\b.*\b(celsius|fahrenheit|km|miles|kg|lbs|dollars|euros|rupees)\b", 0.90),
]

CODE_PATTERNS = [
    (r"(?i)\b(write|create|generate|build)\b.*\b(code|program|script|function|class|module)\b", 0.88),
    (r"(?i)\b(python|javascript|java|cpp|rust|typescript|golang|ruby)\b.*\b(code|example|snippet|program)\b", 0.85),
    (r"(?i)\b(debug|fix|refactor|optimize)\b.*\b(code|bug|error|issue)\b", 0.83),
    (r"(?i)\b(how\s+to\s+(implement|code|write|create))\b", 0.82),
    (r"(?i)\b(implement|code|write|create)\b.*\b(in\s+(python|javascript|java|cpp|rust|typescript|golang|ruby|c\+\+|c#))\b", 0.87),
]

CATEGORY_AGENTS = {
    QueryCategory.NEEDS_WEB: {
        "news": ["news_hound", "generalist"],
        "price": ["price_checker", "generalist"],
        "tech": ["tech_scanner", "deep_researcher"],
        "weather": ["generalist"],
        "sports": ["news_hound", "generalist"],
        "default": ["generalist", "deep_researcher"],
    },
    QueryCategory.NEEDS_KNOWLEDGE: [],
    QueryCategory.NEEDS_CALCULATION: [],
    QueryCategory.NEEDS_CODE: ["tech_scanner"],
}


class RuleBasedRouter:
    """Tier 1: Rule-based query classification using patterns and keywords."""

    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all regex patterns for performance."""
        self.compiled_web = [(re.compile(p), c) for p, c in WEB_PATTERNS]
        self.compiled_knowledge = [(re.compile(p), c) for p, c in KNOWLEDGE_PATTERNS]
        self.compiled_calculation = [(re.compile(p), c) for p, c in CALCULATION_PATTERNS]
        self.compiled_code = [(re.compile(p), c) for p, c in CODE_PATTERNS]

    def classify(self, query: str) -> QueryClassification:
        """Classify a query using rule-based pattern matching."""
        best_match = self._match_patterns(query, self.compiled_calculation, QueryCategory.NEEDS_CALCULATION)
        if best_match and best_match.confidence >= self.confidence_threshold:
            return best_match

        best_match = self._match_patterns(query, self.compiled_code, QueryCategory.NEEDS_CODE)
        if best_match and best_match.confidence >= self.confidence_threshold:
            best_match.suggested_agents = self._suggest_agents(query, QueryCategory.NEEDS_CODE)
            best_match.search_queries = self._generate_search_queries(query, QueryCategory.NEEDS_CODE)
            return best_match

        best_match = self._match_patterns(query, self.compiled_web, QueryCategory.NEEDS_WEB)
        if best_match and best_match.confidence >= self.confidence_threshold:
            best_match.suggested_agents = self._suggest_agents(query, QueryCategory.NEEDS_WEB)
            best_match.search_queries = self._generate_search_queries(query, QueryCategory.NEEDS_WEB)
            return best_match

        best_match = self._match_patterns(query, self.compiled_knowledge, QueryCategory.NEEDS_KNOWLEDGE)
        if best_match and best_match.confidence >= self.confidence_threshold:
            return best_match

        return QueryClassification(
            category=QueryCategory.AMBIGUOUS,
            confidence=0.0,
            reason="no_pattern_matched",
            source="rule_based",
        )

    def _match_patterns(self, query: str, patterns: list[tuple], category: QueryCategory) -> Optional[QueryClassification]:
        """Match query against a list of compiled patterns."""
        best_confidence = 0.0
        best_reason = ""

        for pattern, confidence in patterns:
            if pattern.search(query):
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_reason = f"pattern_matched:{pattern.pattern[:50]}"

        if best_confidence > 0:
            return QueryClassification(
                category=category,
                confidence=best_confidence,
                reason=best_reason,
                source="rule_based",
            )
        return None

    def _suggest_agents(self, query: str, category: QueryCategory) -> list[str]:
        """Suggest which agent profiles to use based on query content."""
        if category not in CATEGORY_AGENTS or not CATEGORY_AGENTS[category]:
            return ["generalist"]

        agents_map = CATEGORY_AGENTS[category]
        query_lower = query.lower()

        if category == QueryCategory.NEEDS_WEB:
            if any(kw in query_lower for kw in ["news", "update", "breaking", "headline"]):
                return agents_map.get("news", agents_map["default"])
            elif any(kw in query_lower for kw in ["price", "cost", "buy", "cheap", "discount", "deal"]):
                return agents_map.get("price", agents_map["default"])
            elif any(kw in query_lower for kw in ["tech", "software", "programming", "api", "github", "code", "python", "javascript", "install", "tutorial", "documentation"]):
                return agents_map.get("tech", agents_map["default"])
            elif any(kw in query_lower for kw in ["weather", "temperature", "rain", "forecast"]):
                return agents_map.get("weather", agents_map["default"])
            elif any(kw in query_lower for kw in ["score", "game", "match", "sports", "nba", "football"]):
                return agents_map.get("sports", agents_map["default"])
            return agents_map["default"]

        return agents_map if isinstance(agents_map, list) else ["generalist"]

    def _generate_search_queries(self, query: str, category: QueryCategory) -> list[str]:
        """Generate optimized search queries for each agent."""
        if category != QueryCategory.NEEDS_WEB:
            return [query]

        queries = [query]
        import datetime
        current_year = datetime.datetime.now().year
        if str(current_year) not in query and str(current_year - 1) not in query:
            queries.append(f"{query} {current_year}")

        query_lower = query.lower()
        if any(kw in query_lower for kw in ["news", "update", "release"]):
            if "latest" not in query_lower:
                queries.append(f"latest {query}")

        return queries
