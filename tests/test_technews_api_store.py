import httpx

from traceable_deep_agents_sample.knowledge.technews_api_store import TechNewsApiStore


def test_search_maps_technews_schema():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/issues/search"
        assert request.url.params["q"] == "LangGraph"
        return httpx.Response(
            200,
            json={
                "query": "LangGraph",
                "total": 1,
                "items": [
                    {
                        "slug": "langgraph-stateful-agents",
                        "title": "LangGraph Patterns",
                        "summary": "legacy",
                        "short_summary": "Stateful graph workflows",
                        "impact_summary": "Useful for durable agents",
                        "action_items": ["Compare checkpoints"],
                        "tags": ["LangGraph"],
                        "radar_category": "Developer Tools",
                        "radar_status": "Assess",
                        "score": {"final_score": 7.8, "reason": "Relevant", "recommended_action": "Prototype"},
                        "issue_date": "2026-07-27",
                        "matched_terms": ["langgraph"],
                        "match_score": 142.3,
                    }
                ],
            },
        )

    store = TechNewsApiStore("https://technews.example", transport=httpx.MockTransport(handler))

    results = store.search("LangGraph")

    assert len(results) == 1
    assert results[0].slug == "langgraph-stateful-agents"
    assert results[0].summary == "Stateful graph workflows"
    assert results[0].match_score == 142.3


def test_auth_headers_are_sent():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer token-123"
        assert request.headers["cookie"] == "session=abc"
        return httpx.Response(
            200,
            json={
                "slug": "latest",
                "title": "Latest",
                "summary": "Summary",
                "short_summary": "Summary",
                "issue_date": "2026-07-31",
                "score": {"final_score": 5},
            },
        )

    store = TechNewsApiStore(
        "https://technews.example",
        auth_token="token-123",
        session_cookie="session=abc",
        transport=httpx.MockTransport(handler),
    )

    assert store.latest()[0].slug == "latest"


def test_technews_store_accepts_tool_filter_arguments():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/issues/search"
        return httpx.Response(
            200,
            json={
                "query": "agent",
                "total": 2,
                "items": [
                    {
                        "slug": "keep",
                        "title": "Keep",
                        "short_summary": "Relevant",
                        "issue_date": "2026-07-31",
                        "tags": ["AI Agent"],
                        "score": {"final_score": 9},
                    },
                    {
                        "slug": "drop",
                        "title": "Drop",
                        "short_summary": "Filtered",
                        "issue_date": "2026-07-30",
                        "tags": ["Other"],
                        "score": {"final_score": 4},
                    },
                ],
            },
        )

    store = TechNewsApiStore("https://technews.example", transport=httpx.MockTransport(handler))

    results = store.search("agent", tags=["AI Agent"], minimum_score=8)

    assert [item.slug for item in results] == ["keep"]
