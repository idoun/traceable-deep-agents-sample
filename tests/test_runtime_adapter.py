from traceable_deep_agents_sample.config import Settings
from traceable_deep_agents_sample.deep_path import DeepPathResult
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
    assert step_types.index("route_selected") < step_types.index("skill_catalog_filtered")
    assert step_types.index("skill_catalog_filtered") < step_types.index("tool_binding_resolved")
    assert step_types.index("tool_binding_resolved") < step_types.index("policy_decision")
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
    assert "Deep Agents path is disabled" in route.output_json["fallback_reason"]
    skill = next(step for step in trace.steps if step.type == "skill_loaded")
    assert skill.output_json["skill_id"] == "tech-trend-briefing"
    assert run.status == "completed"


def test_runtime_adapter_uses_deep_path_when_enabled():
    runner = _FakeDeepPathRunner()
    adapter = TraceableRuntimeAdapter(settings=Settings(deep_path_enabled=True), deep_path_runner=runner)

    run = adapter.run(RuntimeRunCreateRequest(input="AI agent 뉴스를 비교하고 리스크와 전망을 분석해줘", tenant_id="org:deep"))
    trace = adapter.get_trace(run.run_id)

    assert trace is not None
    assert run.output_text == "Deep path answer"
    assert run.stats.model == "fake-deep-model"
    assert runner.calls[0]["tenant_id"] == "org:deep"
    assert runner.calls[0]["skill_ids"] == ["tech-trend-briefing"]
    step_types = [step.type for step in trace.steps]
    assert "deep_agent_started" in step_types
    assert "model_call_started" in step_types
    assert "model_call_completed" in step_types
    assert "deep_tool_call_started" in step_types
    assert "deep_tool_call_completed" in step_types
    assert "deep_agent_completed" in step_types
    assert "light_plan_created" not in step_types
    route = next(step for step in trace.steps if step.type == "route_selected")
    assert route.output_json["selected_route"] == "deep"


def test_runtime_adapter_routes_exclusion_filter_request_to_deep_when_enabled():
    runner = _FakeDeepPathRunner()
    adapter = TraceableRuntimeAdapter(settings=Settings(deep_path_enabled=True), deep_path_runner=runner)

    run = adapter.run(RuntimeRunCreateRequest(input="어제 기사중 AI가 아닌 기사만 조회해줄래", tenant_id="org:deep"))
    trace = adapter.get_trace(run.run_id)

    assert trace is not None
    assert run.output_text == "Deep path answer"
    assert runner.calls[0]["input"] == "어제 기사중 AI가 아닌 기사만 조회해줄래"
    complexity = next(step for step in trace.steps if step.type == "complexity_classified")
    route = next(step for step in trace.steps if step.type == "route_selected")
    step_types = [step.type for step in trace.steps]
    assert complexity.output_json["route"] == "deep"
    assert "requires semantic filtering or exclusion" in complexity.output_json["reasons"]
    assert complexity.output_json["signals"] == {"semantic_filter": ["아닌"]}
    assert route.output_json["requested_route"] == "deep"
    assert route.output_json["selected_route"] == "deep"
    assert "deep_agent_started" in step_types
    assert "light_plan_created" not in step_types


def test_runtime_adapter_falls_back_to_light_when_deep_path_fails():
    adapter = TraceableRuntimeAdapter(settings=Settings(deep_path_enabled=True), deep_path_runner=_FailingDeepPathRunner())

    run = adapter.run(RuntimeRunCreateRequest(input="AI agent 뉴스를 비교하고 리스크와 전망을 분석해줘"))
    trace = adapter.get_trace(run.run_id)

    assert trace is not None
    assert run.status == "completed"
    assert run.stats.model == "deterministic-fixture"
    step_types = [step.type for step in trace.steps]
    assert "deep_agent_failed" in step_types
    assert "light_plan_created" in step_types
    failed = next(step for step in trace.steps if step.type == "deep_agent_failed")
    assert failed.status == "failed"
    assert "fake deep path failure" in failed.error


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
    skill = next(step for step in trace.steps if step.type == "skill_loaded")
    assert skill.output_json["skill_id"] == "daily-news-freshness"
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


def test_runtime_adapter_records_tenant_tool_binding_without_raw_secret_ref():
    adapter = TraceableRuntimeAdapter()

    run = adapter.run(RuntimeRunCreateRequest(input="AI Agent", tenant_id="org:test"))
    trace = adapter.get_trace(run.run_id)

    assert trace is not None
    binding = next(step for step in trace.steps if step.type == "tool_binding_resolved")
    assert binding.output_json["tenant_id"] == "org:test"
    assert binding.output_json["binding_id"] == "org:test:technews.read"
    assert binding.output_json["credential_ref"] == "[REDACTED]"
    assert binding.output_json["credential_ref_hash"].startswith("sha256:")
    assert "secret://tenant/org:test" not in trace.model_dump_json()


def test_runtime_adapter_keeps_context_mesh_and_tool_binding_tenant_isolated():
    adapter = TraceableRuntimeAdapter()

    alpha = adapter.run(
        RuntimeRunCreateRequest(
            input="오늘 뉴스중에 AI 내용 알려줘",
            tenant_id="org:alpha",
            workspace_id="workspace:alpha",
            user_id="user:alpha",
            session_id="session:alpha",
        )
    )
    beta = adapter.run(
        RuntimeRunCreateRequest(
            input="오늘 뉴스중에 AI 내용 알려줘",
            tenant_id="org:beta",
            workspace_id="workspace:beta",
            user_id="user:beta",
            session_id="session:beta",
        )
    )

    alpha_trace = adapter.get_trace(alpha.run_id)
    beta_trace = adapter.get_trace(beta.run_id)

    assert alpha_trace is not None
    assert beta_trace is not None
    _assert_trace_scoped_to_tenant(alpha_trace, expected="alpha", forbidden="beta")
    _assert_trace_scoped_to_tenant(beta_trace, expected="beta", forbidden="alpha")


def _assert_trace_scoped_to_tenant(trace, *, expected: str, forbidden: str):
    payload = trace.model_dump_json()
    assert f"org:{forbidden}" not in payload
    assert f"workspace:{forbidden}" not in payload
    assert f"user:{forbidden}" not in payload
    assert f"session:{forbidden}" not in payload

    context_mesh = next(step for step in trace.steps if step.type == "context_mesh_built")
    assert context_mesh.output_json["tenant"]["id"] == f"org:{expected}"
    assert all(namespace.startswith(f"tenant/org:{expected}/") for namespace in context_mesh.output_json["memory"]["namespaces"])

    skill_catalog = next(step for step in trace.steps if step.type == "skill_catalog_filtered")
    assert skill_catalog.input_json["tenant_id"] == f"org:{expected}"

    binding = next(step for step in trace.steps if step.type == "tool_binding_resolved")
    assert binding.output_json["tenant_id"] == f"org:{expected}"
    assert binding.output_json["binding_id"] == f"org:{expected}:technews.read"
    assert binding.output_json["credential_ref"] == "[REDACTED]"


class _FakeDeepPathRunner:
    provider = "fake"
    model = "fake-deep-model"

    def __init__(self):
        self.calls = []

    def run(self, *, payload, context_mesh, selected_skills, tool_binding):
        self.calls.append(
            {
                "input": payload.input,
                "tenant_id": context_mesh["tenant"]["id"],
                "skill_ids": [skill.skill_id for skill in selected_skills],
                "binding_id": tool_binding.binding_id,
            }
        )
        return DeepPathResult(
            answer="Deep path answer",
            raw_output={"source": "fake"},
            trace_events=[
                {
                    "step_type": "deep_tool_call_started",
                    "summary": "Fake deep tool started.",
                    "input_json": {"tool_name": "search_tech_news"},
                },
                {
                    "step_type": "deep_tool_call_completed",
                    "summary": "Fake deep tool completed.",
                    "output_json": {"output_type": "dict"},
                },
            ],
        )


class _FailingDeepPathRunner:
    provider = "fake"
    model = "failing-deep-model"

    def run(self, **kwargs):
        del kwargs
        raise RuntimeError("fake deep path failure")
