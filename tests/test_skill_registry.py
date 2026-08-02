from traceable_deep_agents_sample.complexity_router import ComplexityRouter
from traceable_deep_agents_sample.skill_registry import SkillRegistry


def test_skill_registry_lists_portable_skill_folders():
    registry = SkillRegistry()

    assert registry.list_skill_ids() == ["daily-news-freshness", "tech-trend-briefing"]


def test_skill_registry_selects_freshness_skill_for_today_news():
    decision = ComplexityRouter().classify("오늘 뉴스중에 AI 내용 알려줘")

    skills = SkillRegistry().select(user_input="오늘 뉴스중에 AI 내용 알려줘", decision=decision)

    assert [skill.skill_id for skill in skills] == ["daily-news-freshness"]
    assert skills[0].hash.startswith("sha256:")
    assert skills[0].version == "2026-08-02"


def test_skill_registry_selects_trend_skill_for_deep_candidate():
    query = "AI agent 뉴스를 비교하고 리스크와 전망을 분석해줘"
    decision = ComplexityRouter().classify(query)

    skills = SkillRegistry().select(user_input=query, decision=decision)

    assert [skill.skill_id for skill in skills] == ["tech-trend-briefing"]
