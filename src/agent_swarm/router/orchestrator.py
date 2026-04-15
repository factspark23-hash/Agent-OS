"""Query Router Orchestrator - coordinates the 3-tier routing system."""

import logging
from typing import Optional

from src.agent_swarm.router.rule_based import RuleBasedRouter, QueryClassification, QueryCategory
from src.agent_swarm.router.llm_fallback import LLMRouter
from src.agent_swarm.router.conservative import ConservativeRouter

logger = logging.getLogger(__name__)


class QueryRouter:
    """3-tier hybrid query router.
    
    Tier 1: Rule-based (fast, free, zero latency)
    Tier 2: User's LLM (fallback when rules are ambiguous)
    Tier 3: Conservative default (always web search)
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        enable_llm_fallback: bool = True,
        llm_api_key: Optional[str] = None,
        llm_base_url: str = "https://api.openai.com/v1",
        llm_model: str = "gpt-4o-mini",
        llm_max_tokens: int = 150,
        llm_timeout: float = 5.0,
    ):
        self.confidence_threshold = confidence_threshold
        self.enable_llm_fallback = enable_llm_fallback

        self.tier1 = RuleBasedRouter(confidence_threshold=confidence_threshold)
        self.tier2 = LLMRouter(
            api_key=llm_api_key,
            base_url=llm_base_url,
            model=llm_model,
            max_tokens=llm_max_tokens,
            timeout=llm_timeout,
        ) if enable_llm_fallback else None
        self.tier3 = ConservativeRouter()

    def route(self, query: str) -> QueryClassification:
        """Route a query through the 3-tier system."""
        logger.info(f"Routing query: '{query[:50]}...'")

        # Tier 1: Rule-based (always runs, fast & free)
        tier1_result = self.tier1.classify(query)
        logger.debug(
            f"Tier 1 result: category={tier1_result.category.value}, "
            f"confidence={tier1_result.confidence:.2f}"
        )

        if tier1_result.confidence >= self.confidence_threshold:
            logger.info(f"Tier 1 classified as {tier1_result.category.value} (confidence: {tier1_result.confidence:.2f})")
            return tier1_result

        # Tier 2: LLM fallback (only if enabled and API key available)
        if self.tier2 and self.tier2.is_available():
            logger.info("Tier 1 uncertain, trying Tier 2 (LLM fallback)...")
            tier2_result = self.tier2.classify(query)

            if tier2_result and tier2_result.confidence >= self.confidence_threshold:
                logger.info(f"Tier 2 classified as {tier2_result.category.value} (confidence: {tier2_result.confidence:.2f})")
                return tier2_result

            if tier2_result:
                logger.debug(f"Tier 2 uncertain: confidence={tier2_result.confidence:.2f}")

        # Tier 3: Conservative default (always returns NEEDS_WEB)
        logger.info("Tiers 1 & 2 uncertain, falling back to Tier 3 (conservative)")
        tier3_result = self.tier3.classify(query)
        return tier3_result

    def update_llm_config(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Update LLM configuration at runtime."""
        if self.tier2 is None:
            self.tier2 = LLMRouter()

        if api_key is not None:
            self.tier2.api_key = api_key
            self.tier2._client = None
        if base_url is not None:
            self.tier2.base_url = base_url
            self.tier2._client = None
        if model is not None:
            self.tier2.model = model
            self.tier2._client = None


__all__ = ["QueryRouter", "QueryClassification", "QueryCategory"]
