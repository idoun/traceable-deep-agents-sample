from langchain_core.language_models.fake_chat_models import FakeListChatModel

from traceable_deep_agents_sample.config import Settings
from traceable_deep_agents_sample.deep_agent import _build_store
from traceable_deep_agents_sample.deep_agent import build_deep_agent
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
