from traceable_deep_agents_sample.complexity_router import ComplexityRouter


def test_complexity_router_keeps_simple_news_lookup_light():
    decision = ComplexityRouter().classify("오늘 뉴스중에 AI 내용 알려줘")

    assert decision.route == "light"
    assert decision.score < 0.5
    assert "single-step news lookup can use the light path" in decision.reasons


def test_complexity_router_marks_synthesis_request_deep():
    decision = ComplexityRouter().classify("AI agent 관련 뉴스들을 비교하고 투자 관점의 리스크와 전망을 분석해줘")

    assert decision.route == "deep"
    assert decision.score >= 0.5
    assert "requires synthesis, comparison, or judgment" in decision.reasons
