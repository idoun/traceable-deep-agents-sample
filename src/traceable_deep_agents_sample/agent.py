from pathlib import Path
from uuid import uuid4

from traceable_deep_agents_sample.config import Settings
from traceable_deep_agents_sample.knowledge.fixture_store import FixtureArticleStore
from traceable_deep_agents_sample.models import AgentResponse, Source
from traceable_deep_agents_sample.tools import TechRadarTools
from traceable_deep_agents_sample.tracing import JsonlTraceSink, TraceEvent

NO_EVIDENCE = "현재 수집된 Tech Radar 데이터에서는 충분한 근거를 찾지 못했습니다."


def run_fixture_agent(question: str, settings: Settings | None = None, thread_id: str | None = None) -> AgentResponse:
    settings = settings or Settings()
    run_id = str(uuid4())
    thread_id = thread_id or str(uuid4())
    sink = JsonlTraceSink(settings.trace_dir, run_id)
    tools = TechRadarTools(FixtureArticleStore(Path(settings.data_path)))

    sink.write(TraceEvent(event_type="run.started", run_id=run_id, thread_id=thread_id, payload={"question": question}))
    sink.write(TraceEvent(event_type="retrieval.started", run_id=run_id, thread_id=thread_id, payload={"query": question}))
    search = tools.search_tech_news(question, limit=3)
    sink.write(
        TraceEvent(
            event_type="retrieval.completed",
            run_id=run_id,
            thread_id=thread_id,
            payload={"total_results": search["total_results"]},
        )
    )

    if not search["results"]:
        answer = NO_EVIDENCE
        sources: list[Source] = []
    else:
        articles = [tools.get_tech_news_article(item["slug"]) for item in search["results"]]
        sources = [
            Source(
                source_id=f"tech-radar:{article['slug']}",
                slug=article["slug"],
                title=article["title"],
                issue_date=article["issue_date"],
                url=article["source_url"],
                excerpt=article["short_summary"],
                relevance_score=search["results"][index]["match_score"],
            )
            for index, article in enumerate(article for article in articles if article)
        ]
        bullets = "\n".join(f"- {source.title}: {source.excerpt}" for source in sources)
        answer = f"수집된 Tech Radar 데이터에서 관련 근거를 찾았습니다.\n\n{bullets}"

    sink.write(
        TraceEvent(
            event_type="answer.completed",
            run_id=run_id,
            thread_id=thread_id,
            payload={"source_count": len(sources)},
        )
    )
    sink.write(TraceEvent(event_type="run.completed", run_id=run_id, thread_id=thread_id))
    return AgentResponse(
        answer=answer,
        sources=sources,
        run_id=run_id,
        thread_id=thread_id,
        trace_path=str(sink.path),
    )

