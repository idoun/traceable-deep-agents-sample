from traceable_deep_agents_sample.knowledge.fixture_store import FixtureArticleStore


class TechRadarTools:
    def __init__(self, store: FixtureArticleStore):
        self.store = store

    def search_tech_news(
        self,
        query: str,
        limit: int = 5,
        tags: list[str] | None = None,
        minimum_score: float | None = None,
    ) -> dict:
        results = self.store.search(query=query, limit=limit, tags=tags, minimum_score=minimum_score)
        return {
            "query": query,
            "filters": {"tags": tags or [], "minimum_score": minimum_score},
            "total_results": len(results),
            "results": [item.model_dump(mode="json") for item in results],
        }

    def get_tech_news_article(self, slug: str) -> dict | None:
        article = self.store.get_article(slug)
        return article.model_dump(mode="json") if article else None

    def get_latest_tech_news(
        self,
        limit: int = 5,
        tags: list[str] | None = None,
        minimum_score: float | None = None,
    ) -> dict:
        results = self.store.latest(limit=limit, tags=tags, minimum_score=minimum_score)
        return {
            "filters": {"tags": tags or [], "minimum_score": minimum_score},
            "total_results": len(results),
            "results": [item.model_dump(mode="json") for item in results],
        }

