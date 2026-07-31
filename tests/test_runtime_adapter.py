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


def test_runtime_adapter_records_policy_before_tool_call():
    adapter = TraceableRuntimeAdapter()

    run = adapter.run(RuntimeRunCreateRequest(input="LangGraph Agent"))
    trace = adapter.get_trace(run.run_id)

    step_types = [step.type for step in trace.steps]
    assert step_types.index("policy_decision") < step_types.index("tool_call_started")
    assert "tool_call_completed" in step_types
    assert "final_answer" in step_types


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

