"""Tier 2: LLM-based query router fallback using user's own API key."""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LLMRouter:
    """Tier 2: Uses user's LLM API for ambiguous query classification.
    
    Supports OpenAI-compatible APIs (OpenAI, Anthropic via proxy, Ollama, LM Studio).
    Only used when Tier 1 (rule-based) returns low confidence.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        max_tokens: int = 150,
        timeout: float = 5.0,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._client = None

    def is_available(self) -> bool:
        """Check if LLM routing is available (has API key)."""
        return bool(self.api_key and self.api_key.strip())

    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
            return self._client
        except ImportError:
            logger.warning("openai package not installed — LLM routing unavailable")
            return None
        except Exception as e:
            logger.warning(f"Failed to create LLM client: {e}")
            return None

    def classify(self, query: str) -> Optional["QueryClassification"]:
        """Classify a query using the user's LLM.
        
        Returns QueryClassification or None if LLM is unavailable.
        """
        if not self.is_available():
            return None

        client = self._get_client()
        if client is None:
            return None

        try:
            from src.agent_swarm.router.rule_based import QueryCategory, QueryClassification

            prompt = f"""Classify this search query into exactly one category:

Query: "{query}"

Categories:
- needs_web: Requires current/live web data (news, prices, weather, latest info)
- needs_knowledge: Can be answered from general knowledge (definitions, history, explanations)
- needs_calculation: Requires math/computation
- needs_code: About writing/generating code

Respond with ONLY a JSON object:
{{"category": "needs_web", "confidence": 0.9, "reason": "requires current data"}}"""

            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=0.1,
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from response (handle markdown code blocks)
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            result = json.loads(content.strip())

            category_str = result.get("category", "ambiguous")
            try:
                category = QueryCategory(category_str)
            except ValueError:
                category = QueryCategory.AMBIGUOUS

            return QueryClassification(
                category=category,
                confidence=float(result.get("confidence", 0.5)),
                reason=result.get("reason", "llm_classification"),
                source="llm_fallback",
            )

        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON for query classification")
            return None
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            return None
