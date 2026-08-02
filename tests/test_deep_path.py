import json
from collections import UserDict

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from traceable_deep_agents_sample.config import Settings
from traceable_deep_agents_sample.deep_path import DeepPathRunner
from traceable_deep_agents_sample.runtime_contract import RuntimeRunCreateRequest
from traceable_deep_agents_sample.tool_binding import ToolBinding


def test_deep_path_runner_invokes_agent_with_scoped_runtime_context():
    captured = {}

    class FakeAgent:
        def invoke(self, payload, config=None):
            captured.update(payload)
            [callback] = config["callbacks"]
            callback.on_tool_start({"name": "search_tech_news"}, '{"query": "AI agent"}')
            callback.on_tool_end({"total_results": 1})
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
    assert [event["step_type"] for event in result.trace_events] == ["deep_tool_call_started", "deep_tool_call_completed"]


def test_deep_path_runner_normalizes_mapping_tool_only_response():
    class FakeAgent:
        def invoke(self, payload, config=None):
            del payload, config
            return UserDict(
                {
                    "messages": [
                        HumanMessage(content="AI agent 관련 뉴스들을 비교해줘"),
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "search_tech_news",
                                    "args": {"query": "AI agent", "limit": 5},
                                    "id": "tool-call-1",
                                }
                            ],
                        ),
                        ToolMessage(
                            content=json.dumps(
                                {
                                    "total_results": 1,
                                    "results": [
                                        {
                                            "title": "Agent runtime observability",
                                            "summary": "Traceable runtime design note",
                                        }
                                    ],
                                }
                            ),
                            tool_call_id="tool-call-1",
                        ),
                    ]
                }
            )

    runner = DeepPathRunner(settings=Settings(), agent_factory=lambda settings: FakeAgent())

    result = runner.run(
        payload=RuntimeRunCreateRequest(input="AI agent 관련 뉴스들을 비교해줘"),
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

    assert "HumanMessage(" not in result.answer
    assert "AIMessage(" not in result.answer
    assert "ToolMessage(" not in result.answer
    assert "최종 assistant 답변을 반환하지 않았습니다" in result.answer
    assert "- Agent runtime observability: Traceable runtime design note" in result.answer
    assert result.raw_output == {"keys": ["messages"]}


def test_deep_path_runner_extracts_gemini_text_blocks_from_final_ai_message():
    class FakeAgent:
        def invoke(self, payload, config=None):
            del payload, config
            return UserDict(
                {
                    "messages": [
                        HumanMessage(content="AI agent 관련 뉴스들을 비교해줘"),
                        AIMessage(content=[{"type": "text", "text": "최종 종합 답변입니다."}]),
                    ]
                }
            )

    runner = DeepPathRunner(
        settings=Settings(llm_provider="gemini", gemini_model="gemini-test"),
        agent_factory=lambda settings: FakeAgent(),
    )

    result = runner.run(
        payload=RuntimeRunCreateRequest(input="AI agent 관련 뉴스들을 비교해줘"),
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

    assert result.answer == "최종 종합 답변입니다."
    assert runner.provider == "gemini"
    assert runner.model == "gemini-test"


def test_deep_path_runner_retries_tool_only_response_for_final_synthesis():
    captured_payloads = []

    class FakeAgent:
        def invoke(self, payload, config=None):
            del config
            captured_payloads.append(payload)
            if len(captured_payloads) == 1:
                return UserDict(
                    {
                        "messages": [
                            HumanMessage(content="AI agent 관련 뉴스들을 비교해줘"),
                            AIMessage(
                                content="",
                                tool_calls=[
                                    {
                                        "name": "search_tech_news",
                                        "args": {"query": "AI agent", "limit": 5},
                                        "id": "tool-call-1",
                                    }
                                ],
                            ),
                            ToolMessage(
                                content=json.dumps(
                                    {
                                        "results": [
                                            {
                                                "title": "Agent investment outlook",
                                                "summary": "Agents are moving into production workflows.",
                                            }
                                        ]
                                    }
                                ),
                                tool_call_id="tool-call-1",
                            ),
                        ]
                    }
                )
            return UserDict({"messages": [AIMessage(content=[{"type": "text", "text": "최종 투자 분석 답변"}])]})

    runner = DeepPathRunner(settings=Settings(), agent_factory=lambda settings: FakeAgent())

    result = runner.run(
        payload=RuntimeRunCreateRequest(input="AI agent 관련 뉴스들을 비교해줘"),
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

    assert result.answer == "최종 투자 분석 답변"
    assert len(captured_payloads) == 2
    retry_messages = captured_payloads[1]["messages"]
    assert retry_messages[-1]["role"] == "user"
    assert "최종 답변" in retry_messages[-1]["content"]
    assert "최종 assistant 답변을 반환하지 않았습니다" not in result.answer
