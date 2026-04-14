"""Agent Pool Manager - orchestrates parallel search across multiple agents."""

import asyncio
import time
import logging
import concurrent.futures
from typing import Optional

from src.agent_swarm.agents.base import SearchAgent, AgentResult, AgentStatus
from src.agent_swarm.agents.profiles import SearchProfile, SEARCH_PROFILES, get_profile, get_profiles_for_query
from src.agent_swarm.agents.strategies import create_search_plan

logger = logging.getLogger(__name__)


class AgentPool:
    """Manages a pool of search agents for parallel web search.
    
    Inspired by MiroFish's concurrent.futures pattern for parallel execution.
    Each agent searches independently, results are aggregated at the end.
    """

    def __init__(self, max_workers: int = 5, search_timeout: float = 30.0):
        self.max_workers = max_workers
        self.search_timeout = search_timeout
        self._agents: dict[str, SearchAgent] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """Create SearchAgent instances from all defined profiles."""
        for key, profile in SEARCH_PROFILES.items():
            self._agents[key] = SearchAgent(
                name=profile.name,
                profile_name=profile.key,
                expertise=profile.expertise,
                preferred_sources=profile.preferred_sources,
                search_depth=profile.search_depth,
                query_style=profile.query_style,
            )

    def get_agent(self, profile_key: str) -> Optional[SearchAgent]:
        """Get a search agent by profile key."""
        return self._agents.get(profile_key)

    async def search_parallel(
        self,
        query: str,
        agent_profiles: list[str],
        search_backend,
        max_results: int = 10,
    ) -> list[AgentResult]:
        """Execute parallel search across multiple agents."""
        start_time = time.time()

        agents = []
        for key in agent_profiles:
            agent = self._agents.get(key)
            if agent:
                agents.append(agent)
            else:
                logger.warning(f"Unknown agent profile: {key}, skipping")

        if not agents:
            agents = [self._agents["generalist"]]
            logger.info("No valid agent profiles, using generalist")

        logger.info(f"Starting parallel search with {len(agents)} agents: {[a.name for a in agents]}")

        tasks = []
        for agent in agents:
            task = asyncio.create_task(
                self._search_with_timeout(agent, query, search_backend)
            )
            tasks.append(task)

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.search_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Parallel search timed out after {self.search_timeout}s")
            results = []

        agent_results = []
        for result in results:
            if isinstance(result, AgentResult):
                agent_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Agent search error: {result}")

        total_time = time.time() - start_time
        logger.info(
            f"Parallel search completed: {len(agent_results)} results in {total_time:.2f}s "
            f"using {len(agents)} agents"
        )

        return agent_results

    async def _search_with_timeout(
        self, agent: SearchAgent, query: str, search_backend
    ) -> AgentResult:
        """Execute a single agent search with timeout."""
        try:
            result = await asyncio.wait_for(
                agent.search(query, search_backend),
                timeout=self.search_timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Agent '{agent.name}' timed out")
            return AgentResult(
                agent_name=agent.name,
                agent_profile=agent.profile_name,
                query=query,
                status=AgentStatus.FAILED,
                error="timeout",
            )
        except Exception as e:
            logger.error(f"Agent '{agent.name}' error: {e}")
            return AgentResult(
                agent_name=agent.name,
                agent_profile=agent.profile_name,
                query=query,
                status=AgentStatus.FAILED,
                error=str(e),
            )

    def search_parallel_sync(
        self,
        query: str,
        agent_profiles: list[str],
        search_backend,
        max_results: int = 10,
    ) -> list[AgentResult]:
        """Synchronous wrapper for parallel search."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.search_parallel(query, agent_profiles, search_backend, max_results)
                    )
                    return future.result(timeout=self.search_timeout + 5)
            else:
                return loop.run_until_complete(
                    self.search_parallel(query, agent_profiles, search_backend, max_results)
                )
        except RuntimeError:
            return asyncio.run(
                self.search_parallel(query, agent_profiles, search_backend, max_results)
            )

    def get_status(self) -> dict:
        """Get current status of all agents in the pool."""
        return {
            "max_workers": self.max_workers,
            "agents": {
                key: {
                    "name": agent.name,
                    "profile": agent.profile_name,
                    "status": agent.status.value,
                    "expertise": agent.expertise,
                }
                for key, agent in self._agents.items()
            },
        }

    def reset_agents(self):
        """Reset all agent statuses to IDLE."""
        for agent in self._agents.values():
            agent.status = AgentStatus.IDLE
            agent._last_result = None

    def close(self):
        """Clean up pool resources."""
        self.reset_agents()
        logger.debug("AgentPool closed")
