import json

from traceable_deep_agents_sample.agent import run_fixture_agent
from traceable_deep_agents_sample.config import Settings


def test_trace_file_contains_core_events(tmp_path):
    settings = Settings(trace_dir=tmp_path / "traces")

    response = run_fixture_agent("LangGraph Agent", settings=settings)

    events = [json.loads(line)["event_type"] for line in open(response.trace_path, encoding="utf-8")]
    assert "run.started" in events
    assert "retrieval.completed" in events
    assert "answer.completed" in events
    assert "run.completed" in events

