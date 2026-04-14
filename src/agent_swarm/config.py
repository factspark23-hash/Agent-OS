"""Agent Swarm configuration - integrated into Agent-OS config system."""

import os
import json
from typing import Optional
from pydantic import BaseModel, Field


class RouterConfig(BaseModel):
    """Query router configuration."""
    confidence_threshold: float = Field(default=0.7, description="Min confidence for rule-based routing")
    enable_llm_fallback: bool = Field(default=True, description="Enable Tier 2 LLM fallback")
    llm_api_key: Optional[str] = Field(default=None, description="User's LLM API key")
    llm_base_url: str = Field(default="https://api.openai.com/v1", description="LLM API base URL")
    llm_model: str = Field(default="gpt-4o-mini", description="LLM model name")
    llm_max_tokens: int = Field(default=150, description="Max tokens for LLM classification")
    llm_timeout: float = Field(default=5.0, description="LLM request timeout in seconds")


class SwarmAgentConfig(BaseModel):
    """Search agent configuration."""
    max_workers: int = Field(default=5, description="Max parallel agents")
    default_agents: list[str] = Field(default=["generalist"], description="Default agent profiles")
    search_timeout: float = Field(default=30.0, description="Search timeout per agent in seconds")
    max_retries: int = Field(default=2, description="Max retries for failed searches")


class SearchBackendConfig(BaseModel):
    """Search backend configuration."""
    agent_os_url: Optional[str] = Field(default=None, description="Agent-OS server URL")
    agent_os_api_key: Optional[str] = Field(default=None, description="Agent-OS API key")
    use_browser: bool = Field(default=False, description="Use Agent-OS browser backend")
    chrome_impersonate: str = Field(default="chrome146", description="curl_cffi impersonation target")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        description="User-Agent string"
    )


class SwarmOutputConfig(BaseModel):
    """Output configuration."""
    format: str = Field(default="json", description="Output format: json, markdown, or both")
    max_results: int = Field(default=10, description="Max results per query")
    deduplicate: bool = Field(default=True, description="Deduplicate results")
    min_relevance_score: float = Field(default=0.3, description="Min relevance score to include")


class SwarmConfig(BaseModel):
    """Main Agent Swarm configuration."""
    enabled: bool = Field(default=True, description="Enable/disable agent swarm")
    router: RouterConfig = Field(default_factory=RouterConfig)
    agents: SwarmAgentConfig = Field(default_factory=SwarmAgentConfig)
    search: SearchBackendConfig = Field(default_factory=SearchBackendConfig)
    output: SwarmOutputConfig = Field(default_factory=SwarmOutputConfig)

    @classmethod
    def from_env(cls) -> "SwarmConfig":
        """Load configuration from environment variables."""
        router_conf = RouterConfig(
            confidence_threshold=float(os.getenv("SWARM_ROUTER_THRESHOLD", "0.7")),
            enable_llm_fallback=os.getenv("SWARM_LLM_ENABLED", "true").lower() == "true",
            llm_api_key=os.getenv("SWARM_LLM_API_KEY"),
            llm_base_url=os.getenv("SWARM_LLM_BASE_URL", "https://api.openai.com/v1"),
            llm_model=os.getenv("SWARM_LLM_MODEL", "gpt-4o-mini"),
        )
        agent_conf = SwarmAgentConfig(
            max_workers=int(os.getenv("SWARM_MAX_WORKERS", "5")),
            default_agents=json.loads(os.getenv("SWARM_DEFAULT_AGENTS", '["generalist"]')),
        )
        search_conf = SearchBackendConfig(
            agent_os_url=os.getenv("SWARM_AGENT_OS_URL"),
            agent_os_api_key=os.getenv("SWARM_AGENT_OS_API_KEY"),
            use_browser=os.getenv("SWARM_USE_BROWSER", "false").lower() == "true",
        )
        output_conf = SwarmOutputConfig(
            format=os.getenv("SWARM_OUTPUT_FORMAT", "json"),
            max_results=int(os.getenv("SWARM_MAX_RESULTS", "10")),
        )
        return cls(
            enabled=os.getenv("SWARM_ENABLED", "true").lower() == "true",
            router=router_conf,
            agents=agent_conf,
            search=search_conf,
            output=output_conf,
        )


# Global config instance
swarm_config = SwarmConfig.from_env()


def get_config() -> SwarmConfig:
    """Get the global swarm configuration instance.
    
    Returns the singleton SwarmConfig loaded from environment variables.
    """
    return swarm_config
