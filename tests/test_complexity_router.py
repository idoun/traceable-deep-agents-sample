import pytest

from traceable_deep_agents_sample.complexity_router import ComplexityRouter


ROUTE_CASES = [
    pytest.param(
        "simple_latest_news",
        "오늘 뉴스중에 AI 내용 알려줘",
        "light",
        "single-step news lookup can use the light path",
        "simple_lookup",
        id="light-simple-latest-news",
    ),
    pytest.param(
        "deep_synthesis",
        "AI agent 관련 뉴스들을 비교하고 투자 관점의 리스크와 전망을 분석해줘",
        "deep",
        "requires synthesis, comparison, or judgment",
        "synthesis",
        id="deep-synthesis-comparison-risk",
    ),
    pytest.param(
        "deep_evidence_report",
        "AI agent 관련 근거와 출처를 자세히 보고서처럼 정리해줘",
        "deep",
        "asks for evidence expansion or report-style output",
        "multi_step",
        id="deep-evidence-report",
    ),
    pytest.param(
        "deep_semantic_exclusion",
        "어제 기사중 AI가 아닌 기사만 조회해줄래",
        "deep",
        "requires semantic filtering or exclusion",
        "semantic_filter",
        id="deep-semantic-exclusion",
    ),
    pytest.param(
        "deep_single_comparison_marker",
        "AI agent와 LangGraph 비교해줘",
        "deep",
        "requires synthesis, comparison, or judgment",
        "synthesis",
        id="deep-single-comparison-marker",
    ),
    pytest.param(
        "deep_english_vs_marker",
        "Compare latest AI news vs yesterday",
        "deep",
        "requires synthesis, comparison, or judgment",
        "synthesis",
        id="deep-english-vs-marker",
    ),
    pytest.param(
        "deep_forecast",
        "이번 주 AI 뉴스 흐름과 전망을 정리해줘",
        "deep",
        "requires synthesis, comparison, or judgment",
        "synthesis",
        id="deep-forecast",
    ),
    pytest.param(
        "deep_strategy_priority",
        "우리 제품 전략에 영향이 큰 뉴스 우선순위를 뽑아줘",
        "deep",
        "requires synthesis, comparison, or judgment",
        "synthesis",
        id="deep-strategy-priority",
    ),
    pytest.param(
        "deep_semantic_exclusion_with_synthesis_term",
        "AI 관련 기사에서 투자 이야기는 빼고 정리해줘",
        "deep",
        "requires semantic filtering or exclusion",
        "semantic_filter",
        id="deep-semantic-exclusion-with-synthesis-term",
    ),
    pytest.param(
        "deep_english_risk",
        "Analyze AI agent platform risks for investors",
        "deep",
        "requires synthesis, comparison, or judgment",
        "synthesis",
        id="deep-english-risk",
    ),
    pytest.param(
        "deep_english_evidence",
        "Give me evidence and sources for AI agent adoption trends",
        "deep",
        "asks for evidence expansion or report-style output",
        "multi_step",
        id="deep-english-evidence",
    ),
    pytest.param(
        "deep_english_how_should",
        "How should we prioritize these AI infrastructure trends?",
        "deep",
        "requires synthesis, comparison, or judgment",
        "synthesis",
        id="deep-english-how-should",
    ),
]


@pytest.mark.parametrize("case_id, utterance, expected_route, expected_reason, expected_signal", ROUTE_CASES)
def test_complexity_router_route_matrix(case_id, utterance, expected_route, expected_reason, expected_signal):
    del case_id

    decision = ComplexityRouter().classify(utterance)

    assert decision.route == expected_route
    if expected_route == "deep":
        assert decision.score >= 0.5
    else:
        assert decision.score < 0.5
    assert expected_reason in decision.reasons
    assert expected_signal in decision.signals


FALSE_POSITIVE_CASES = [
    pytest.param("최신 뉴스만 알려줘", id="korean-only-latest-news"),
    pytest.param("AI 뉴스 3개만 찾아줘", id="korean-count-limited-news"),
    pytest.param("news only", id="english-only-news"),
    pytest.param("show me latest news", id="english-show-does-not-match-how"),
    pytest.param("how many AI articles today?", id="english-how-many-count-request"),
    pytest.param("show recent articles about LangSmith", id="english-show-recent-articles"),
    pytest.param("find notebook-related AI tooling news", id="english-notebook-does-not-match-not"),
]


@pytest.mark.parametrize("utterance", FALSE_POSITIVE_CASES)
def test_complexity_router_keeps_selection_requests_on_light_path(utterance):
    decision = ComplexityRouter().classify(utterance)

    assert decision.route == "light"
    assert "semantic_filter" not in decision.signals


def test_complexity_router_does_not_match_english_marker_inside_another_word():
    decision = ComplexityRouter().classify("show me latest news")

    assert decision.route == "light"
    assert "synthesis" not in decision.signals
