from pathlib import Path

from traceable_deep_agents_sample.knowledge.fixture_store import FixtureArticleStore
from traceable_deep_agents_sample.tools import TechRadarTools


def test_search_finds_agent_articles():
    tools = TechRadarTools(FixtureArticleStore(Path("data/sample_articles.jsonl")))

    result = tools.search_tech_news("AI Agent tracing", limit=3)

    assert result["total_results"] >= 1
    assert result["results"][0]["slug"] == "agent-runtime-observability"


def test_get_article_detail():
    tools = TechRadarTools(FixtureArticleStore(Path("data/sample_articles.jsonl")))

    article = tools.get_tech_news_article("deep-agents-harness")

    assert article is not None
    assert article["title"] == "Deep Agents Harness Packages Planning and Subagents"

