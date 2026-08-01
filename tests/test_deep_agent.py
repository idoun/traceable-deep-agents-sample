from langchain_core.language_models.fake_chat_models import FakeListChatModel

from traceable_deep_agents_sample.config import Settings
from traceable_deep_agents_sample.deep_agent import _build_store
from traceable_deep_agents_sample.deep_agent import build_deep_agent
from traceable_deep_agents_sample.deep_agent import resolve_deep_agent_model
from traceable_deep_agents_sample.knowledge.fixture_store import FixtureArticleStore
from traceable_deep_agents_sample.knowledge.technews_api_store import TechNewsApiStore


def test_build_deep_agent_with_fake_model():
    agent = build_deep_agent(model=FakeListChatModel(responses=["ok"]))

    assert agent is not None


def test_build_store_uses_fixture_by_default():
    store = _build_store(Settings())

    assert isinstance(store, FixtureArticleStore)


def test_build_store_uses_technews_backend():
    settings = Settings(
        knowledge_backend="technews",
        technews_api_base_url="https://technews.example",
        technews_auth_token="token",
    )

    store = _build_store(settings)

    assert isinstance(store, TechNewsApiStore)
    assert store.base_url == "https://technews.example"
    assert store.auth_token == "token"


def test_resolve_deep_agent_model_uses_runtime_style_openai_provider():
    settings = Settings(llm_provider="openai", llm_model="gpt-5.5")

    model = resolve_deep_agent_model(settings)

    assert model == "openai:gpt-5.5"


def test_resolve_deep_agent_model_keeps_direct_model_override():
    settings = Settings(model="openai:gpt-4.1-mini", llm_provider="gemini")

    model = resolve_deep_agent_model(settings)

    assert model == "openai:gpt-4.1-mini"


def test_resolve_deep_agent_model_builds_gemini_chat_model(monkeypatch):
    captured = {}

    class FakeGeminiModel:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    # Patch the loader instead of importing Google's client in the unit test;
    # this keeps the test focused on our runtime-compatible config mapping.
    monkeypatch.setattr(
        "traceable_deep_agents_sample.deep_agent._load_chat_google_generative_ai",
        lambda: FakeGeminiModel,
    )
    settings = Settings(
        llm_provider="gemini",
        gemini_model="gemini-test",
        gemini_api_key="secret",
    )

    model = resolve_deep_agent_model(settings)

    assert isinstance(model, FakeGeminiModel)
    assert captured == {"api_key": "secret", "model": "gemini-test", "temperature": 0}


def test_resolve_deep_agent_model_requires_gemini_credentials():
    settings = Settings(llm_provider="gemini", gemini_model="gemini-test", gemini_api_key="")

    try:
        resolve_deep_agent_model(settings)
    except ValueError as exc:
        assert "GEMINI_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected missing Gemini credentials to fail")
