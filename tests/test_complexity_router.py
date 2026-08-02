import pytest

from traceable_deep_agents_sample.complexity_router import ComplexityRouter


ROUTE_CASES = [
    pytest.param(
        "simple_latest_news",
        "오늘 뉴스중에 AI 내용 알려줘",
        "light",
        "single-step news lookup can use the light path",
        id="light-simple-latest-news",
    ),
    pytest.param(
        "deep_synthesis",
        "AI agent 관련 뉴스들을 비교하고 투자 관점의 리스크와 전망을 분석해줘",
        "deep",
        "requires synthesis, comparison, or judgment",
        id="deep-synthesis-comparison-risk",
    ),
    pytest.param(
        "deep_evidence_report",
        "AI agent 관련 근거와 출처를 자세히 보고서처럼 정리해줘",
        "deep",
        "asks for evidence expansion or report-style output",
        id="deep-evidence-report",
    ),
    pytest.param(
        "deep_semantic_exclusion",
        "어제 기사중 AI가 아닌 기사만 조회해줄래",
        "deep",
        "requires semantic filtering or exclusion",
        id="deep-semantic-exclusion",
    ),
]


@pytest.mark.parametrize("case_id, utterance, expected_route, expected_reason", ROUTE_CASES)
def test_complexity_router_route_matrix(case_id, utterance, expected_route, expected_reason):
    del case_id

    decision = ComplexityRouter().classify(utterance)

    assert decision.route == expected_route
    if expected_route == "deep":
        assert decision.score >= 0.5
    else:
        assert decision.score < 0.5
    assert expected_reason in decision.reasons
