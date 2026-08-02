from traceable_deep_agents_sample.config import Settings
from traceable_deep_agents_sample.deep_path import DeepPathRunner
from traceable_deep_agents_sample.runtime_contract import RuntimeRunCreateRequest
from traceable_deep_agents_sample.tool_binding import ToolBinding


def test_deep_path_runner_invokes_agent_with_scoped_runtime_context():
    captured = {}

    class FakeAgent:
        def invoke(self, payload):
            captured.update(payload)
            return {"messages": [{"role": "assistant", "content": "Scoped deep answer"}]}

    runner = DeepPathRunner(settings=Settings(), agent_factory=lambda settings: FakeAgent())

    result = runner.run(
        payload=RuntimeRunCreateRequest(input="AI agent 전망 분석", tenant_id="org:test"),
        context_mesh={"tenant": {"id": "org:test"}},
        selected_skills=[],
        tool_binding=ToolBinding(
            tool_name="search_tech_news",
            binding_id="org:test:technews.read",
            tenant_id="org:test",
            allowed_scopes=("read:issues",),
            credential_ref_hash="sha256:test",
        ),
    )

    message = captured["messages"][0]["content"]
    assert result.answer == "Scoped deep answer"
    assert "tenant_id: org:test" in message
    assert "allowed_tool_binding: org:test:technews.read" in message
    assert "allowed_scopes: read:issues" in message
