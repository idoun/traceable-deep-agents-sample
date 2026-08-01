from collections.abc import Callable
from pathlib import Path
from typing import Any

from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, create_deep_agent, register_harness_profile
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import tool

from traceable_deep_agents_sample.config import Settings
from traceable_deep_agents_sample.knowledge.fixture_store import FixtureArticleStore
from traceable_deep_agents_sample.knowledge.technews_api_store import TechNewsApiStore
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
    selected_model = model or resolve_deep_agent_model(settings)
    tools = _build_langchain_tools(settings)
    if isinstance(selected_model, str):
        _register_read_only_profile(selected_model)
    return create_deep_agent(
        model=selected_model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        name=settings.agent_id,
    )


def resolve_deep_agent_model(settings: Settings) -> str | BaseChatModel:
    """Resolve the model surface using the same provider vocabulary as the runtime.

    Deep Agents accepts provider-prefixed LangChain model strings for OpenAI.
    Gemini needs a concrete LangChain chat model so its API key can be passed
    without putting secrets into the public model string or runtime traces.
    """

    if settings.model:
        return settings.model

    provider = settings.llm_provider.strip().lower() or "openai"
    if provider == "openai":
        return f"openai:{settings.llm_model}"
    if provider == "gemini":
        return _build_gemini_model(settings)
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def _build_gemini_model(settings: Settings) -> BaseChatModel:
    model_name = settings.gemini_model or settings.llm_model
    api_key = settings.gemini_api_key
    if not model_name or not api_key:
        missing = []
        if not model_name:
            missing.append("GEMINI_MODEL or TECH_RADAR_GEMINI_MODEL")
        if not api_key:
            missing.append("GEMINI_API_KEY, GOOGLE_API_KEY, or TECH_RADAR_GEMINI_API_KEY")
        raise ValueError(f"Missing Gemini configuration: {', '.join(missing)}")

    ChatGoogleGenerativeAI = _load_chat_google_generative_ai()
    return ChatGoogleGenerativeAI(api_key=api_key, model=model_name, temperature=0)


def _load_chat_google_generative_ai():
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:
        raise ValueError("Install langchain-google-genai to use TECH_RADAR_LLM_PROVIDER=gemini") from exc
    return ChatGoogleGenerativeAI


def _register_read_only_profile(model_spec: str) -> None:
    register_harness_profile(
        model_spec,
        HarnessProfile(
            excluded_tools=READ_ONLY_EXCLUDED_TOOLS,
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        ),
    )


def _build_langchain_tools(settings: Settings) -> list[Callable[..., Any]]:
    toolset = TechRadarTools(_build_store(settings))

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


def _build_store(settings: Settings) -> FixtureArticleStore | TechNewsApiStore:
    if settings.knowledge_backend == "fixture":
        return FixtureArticleStore(Path(settings.data_path))
    if settings.knowledge_backend == "technews":
        return TechNewsApiStore(
            base_url=settings.technews_api_base_url,
            timeout=settings.technews_request_timeout,
            auth_token=settings.technews_auth_token,
            session_cookie=settings.technews_session_cookie,
        )
    raise ValueError(f"Unsupported knowledge backend: {settings.knowledge_backend}")
