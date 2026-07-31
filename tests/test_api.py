from fastapi.testclient import TestClient

from traceable_deep_agents_sample.api import create_app


def test_agent_server_run_and_trace_endpoints():
    client = TestClient(create_app())

    run_response = client.post("/v1/runs", json={"input": "AI Agent tracing", "agent_id": "tech-radar"})

    assert run_response.status_code == 201
    run = run_response.json()
    assert run["status"] == "completed"
    assert run["trace_url"] == f"/v1/runs/{run['run_id']}/trace"

    trace_response = client.get(run["trace_url"])
    assert trace_response.status_code == 200
    trace = trace_response.json()
    step_types = [step["type"] for step in trace["steps"]]
    assert step_types.index("policy_decision") < step_types.index("tool_call_started")
    assert "final_answer" in step_types


def test_agent_server_trace_not_found():
    client = TestClient(create_app())

    response = client.get("/v1/runs/run_missing/trace")

    assert response.status_code == 404
