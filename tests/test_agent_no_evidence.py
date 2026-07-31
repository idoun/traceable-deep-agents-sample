from traceable_deep_agents_sample.agent import NO_EVIDENCE, run_fixture_agent
from traceable_deep_agents_sample.config import Settings


def test_no_evidence_answer(tmp_path):
    settings = Settings(trace_dir=tmp_path / "traces")

    response = run_fixture_agent("양자 양말 제조 뉴스", settings=settings)

    assert response.answer == NO_EVIDENCE
    assert response.sources == []

