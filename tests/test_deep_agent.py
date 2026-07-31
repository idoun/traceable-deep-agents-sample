from langchain_core.language_models.fake_chat_models import FakeListChatModel

from traceable_deep_agents_sample.deep_agent import build_deep_agent


def test_build_deep_agent_with_fake_model():
    agent = build_deep_agent(model=FakeListChatModel(responses=["ok"]))

    assert agent is not None
