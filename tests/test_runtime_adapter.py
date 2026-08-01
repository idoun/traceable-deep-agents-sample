from traceable_deep_agents_sample.runtime_adapter import TraceableRuntimeAdapter
from traceable_deep_agents_sample.runtime_contract import RuntimeRunCreateRequest


def test_runtime_adapter_returns_traceable_runtime_shape():
    adapter = TraceableRuntimeAdapter()

    run = adapter.run(RuntimeRunCreateRequest(input="AI Agent tracing"))
    trace = adapter.get_trace(run.run_id)

    assert trace is not None
    assert run.trace_url == f"/v1/runs/{run.run_id}/trace"
    assert trace.run.status == "completed"
    assert trace.steps[0].type == "run_started"
    assert trace.steps[-1].type == "run_completed"


def test_runtime_adapter_builds_default_context_mesh():
    adapter = TraceableRuntimeAdapter()

    run = adapter.run(RuntimeRunCreateRequest(input="AI Agent tracing"))
    trace = adapter.get_trace(run.run_id)

    assert trace is not None
    assert run.tenant_id == "tenant:default"
    context_mesh = next(step for step in trace.steps if step.type == "context_mesh_built")
    assert context_mesh.output_json["tenant"] == {"id": "tenant:default", "source": "default"}


def test_runtime_adapter_propagates_tenant_context_mesh():
    adapter = TraceableRuntimeAdapter()

    run = adapter.run(
        RuntimeRunCreateRequest(
            input="AI Agent tracing",
            tenant_id="org:test",
            workspace_id="workspace:test",
            user_id="user:test",
            session_id="session:test",
        )
    )
    trace = adapter.get_trace(run.run_id)

    assert trace is not None
    assert run.tenant_id == "org:test"
    assert run.workspace_id == "workspace:test"
    assert run.user_id == "user:test"
    context_mesh = next(step for step in trace.steps if step.type == "context_mesh_built")
    assert context_mesh.output_json["tenant"] == {"id": "org:test", "source": "request"}
    assert "tenant/org:test/session/session:test/summary" in context_mesh.output_json["memory"]["namespaces"]


def test_runtime_adapter_records_policy_before_tool_call():
    adapter = TraceableRuntimeAdapter()

    run = adapter.run(RuntimeRunCreateRequest(input="LangGraph Agent"))
    trace = adapter.get_trace(run.run_id)

    step_types = [step.type for step in trace.steps]
    assert step_types.index("complexity_classified") < step_types.index("route_selected")
    assert step_types.index("route_selected") < step_types.index("light_plan_created")
    assert step_types.index("policy_decision") < step_types.index("tool_call_started")
    assert "tool_call_completed" in step_types
    assert "final_answer" in step_types


def test_runtime_adapter_traces_deep_candidate_with_light_fallback():
    adapter = TraceableRuntimeAdapter()

    run = adapter.run(RuntimeRunCreateRequest(input="AI agent 뉴스를 비교하고 리스크와 전망을 분석해줘"))
    trace = adapter.get_trace(run.run_id)

    assert trace is not None
    complexity = next(step for step in trace.steps if step.type == "complexity_classified")
    route = next(step for step in trace.steps if step.type == "route_selected")
    assert complexity.output_json["route"] == "deep"
    assert route.output_json["requested_route"] == "deep"
    assert route.output_json["selected_route"] == "light"
    assert "Deep Agents execution is not yet wired" in route.output_json["fallback_reason"]
    assert run.status == "completed"


def test_runtime_adapter_reuses_frozen_tool_result():
    adapter = TraceableRuntimeAdapter()

    original = adapter.run(RuntimeRunCreateRequest(input="AI Agent tracing"))
    original_trace = adapter.get_trace(original.run_id)
    assert original_trace is not None
    completed = next(step for step in original_trace.steps if step.type == "tool_call_completed")

    replay = adapter.run(
        RuntimeRunCreateRequest(
            input="AI Agent tracing",
            replay={
                "of_run_id": original.run_id,
                "tool_mode": "frozen",
                "frozen_tool_results": [
                    {
                        "tool_name": "search_tech_news",
                        "tool_input": {"query": "AI Agent tracing", "limit": 3},
                        "result": completed.output_json,
                    }
                ],
            },
        )
    )
    replay_trace = adapter.get_trace(replay.run_id)

    assert replay.replay_of_run_id == original.run_id
    assert replay.replay_tool_mode == "frozen"
    assert replay_trace is not None
    replay_completed = next(step for step in replay_trace.steps if step.type == "tool_call_completed")
    assert replay_completed.output_json["tool_mode"] == "frozen"


def test_runtime_adapter_uses_latest_tool_for_today_news():
    adapter = TraceableRuntimeAdapter()

    run = adapter.run(RuntimeRunCreateRequest(input="오늘 뉴스중에 AI 내용 알려줘"))
    trace = adapter.get_trace(run.run_id)

    assert trace is not None
    started = next(step for step in trace.steps if step.type == "tool_call_started")
    assert started.input_json["tool_name"] == "get_latest_tech_news"
    assert "오늘 뉴스는 아직 문서 수집이 완료되지 않았을 수 있습니다" in (run.output_text or "")
    assert "전날 기준 GeekNews 요약" in (run.output_text or "")


def test_runtime_adapter_redacts_sensitive_context():
    adapter = TraceableRuntimeAdapter()

    run = adapter.run(
        RuntimeRunCreateRequest(
            input="AI Agent",
            client_context={"authorization": "Bearer secret", "nested": {"api_key": "secret"}},
        )
    )
    trace = adapter.get_trace(run.run_id)
    payload = [step.model_dump(mode="json") for step in trace.steps]

    assert "secret" not in str(payload)
    assert "[REDACTED]" in str(payload)
