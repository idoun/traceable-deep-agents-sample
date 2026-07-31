from collections.abc import Callable
from pathlib import Path
from typing import Any

from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, create_deep_agent, register_harness_profile
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import tool

from traceable_deep_agents_sample.config import Settings
from traceable_deep_agents_sample.knowledge.fixture_store import FixtureArticleStore
from traceable_deep_agents_sample.prompts import SYSTEM_PROMPT
from traceable_deep_agents_sample.tools import TechRadarTools

READ_ONLY_EXCLUDED_TOOLS = frozenset(
    {
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "glob",
        "grep",
        "execute",
        "task",
    }
)


def build_deep_agent(
    settings: Settings | None = None,
    model: str | BaseChatModel | None = None,
) -> Any:
    """Build the Deep Agents graph with read-only Tech Radar tools."""

    settings = settings or Settings()
    selected_model = model or settings.model
    tools = _build_langchain_tools(settings)
    if isinstance(selected_model, str):
        _register_read_only_profile(selected_model)
    return create_deep_agent(
        model=selected_model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        name=settings.agent_id,
    )


def _register_read_only_profile(model_spec: str) -> None:
    register_harness_profile(
        model_spec,
        HarnessProfile(
            excluded_tools=READ_ONLY_EXCLUDED_TOOLS,
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        ),
    )


def _build_langchain_tools(settings: Settings) -> list[Callable[..., Any]]:
    toolset = TechRadarTools(FixtureArticleStore(Path(settings.data_path)))

    @tool
    def search_tech_news(query: str, limit: int = 5) -> dict:
        """Search Tech Radar articles by keyword using read-only evidence data."""

        return toolset.search_tech_news(query=query, limit=limit)

    @tool
    def get_tech_news_article(slug: str) -> dict | None:
        """Fetch a Tech Radar article detail by slug."""

        return toolset.get_tech_news_article(slug=slug)

    @tool
    def get_latest_tech_news(limit: int = 5) -> dict:
        """Fetch the latest Tech Radar article summaries."""

        return toolset.get_latest_tech_news(limit=limit)

    return [search_tech_news, get_tech_news_article, get_latest_tech_news]
