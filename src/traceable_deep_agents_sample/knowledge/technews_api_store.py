"""Adapter for the real technews-publisher read API."""

from __future__ import annotations

import httpx

from traceable_deep_agents_sample.models import Article, ArticleScore, SearchResult


class TechNewsApiStore:
    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        auth_token: str = "",
        session_cookie: str = "",
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth_token = auth_token
        self.session_cookie = session_cookie
        self.transport = transport

    def search(
        self,
        query: str,
        limit: int = 5,
        tags: list[str] | None = None,
        minimum_score: float | None = None,
    ) -> list[SearchResult]:
        payload = self._get("/api/issues/search", params={"q": query})
        results = [_search_result_from_issue(item) for item in payload.get("items", [])]
        return _filter_results(results, tags=tags, minimum_score=minimum_score)[:limit]

    def latest(
        self,
        limit: int = 5,
        tags: list[str] | None = None,
        minimum_score: float | None = None,
    ) -> list[SearchResult]:
        payload = self._get("/api/issues/latest")
        # technews-publisher exposes a single latest issue endpoint today, so
        # filter locally to keep this store interchangeable with FixtureArticleStore.
        return _filter_results([_search_result_from_issue(payload)], tags=tags, minimum_score=minimum_score)[:limit]

    def get_article(self, slug: str) -> Article | None:
        response = self._get(f"/api/issues/{slug}")
        return _article_from_issue(response)

    async def get(self, path: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers(), transport=self.transport) as client:
            response = await client.get(f"{self.base_url}{path}")
            response.raise_for_status()
            return response.json()

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict:
        with httpx.Client(timeout=self.timeout, headers=self._headers(), transport=self.transport) as client:
            response = client.get(f"{self.base_url}{path}", params=params)
            response.raise_for_status()
            return response.json()

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if self.session_cookie:
            headers["Cookie"] = self.session_cookie
        return headers


def _article_from_issue(issue: dict) -> Article:
    score = issue.get("score") or {}
    return Article(
        slug=issue["slug"],
        title=issue["title"],
        issue_date=issue["issue_date"],
        source_url=issue.get("source_url") or "",
        short_summary=issue.get("short_summary") or issue.get("summary") or "",
        impact_summary=issue.get("impact_summary") or "",
        action_items=issue.get("action_items") or [],
        tags=issue.get("tags") or [],
        radar_category=issue.get("radar_category") or "Other",
        radar_status=issue.get("radar_status") or "Assess",
        score=ArticleScore(
            interest_score=score.get("interest_score", 0),
            project_score=score.get("project_score", 0),
            novelty_score=score.get("novelty_score", 0),
            actionability_score=score.get("actionability_score", 0),
            credibility_score=score.get("credibility_score", 0),
            community_score=score.get("community_score", 0),
            final_score=score.get("final_score", 0),
            score_reason=score.get("reason", ""),
            recommended_action=score.get("recommended_action", ""),
        ),
        body=issue.get("markdown") or "",
    )


def _search_result_from_issue(issue: dict) -> SearchResult:
    article = _article_from_issue(issue)
    return SearchResult(
        slug=article.slug,
        title=article.title,
        issue_date=article.issue_date,
        summary=article.short_summary,
        tags=article.tags,
        final_score=article.score.final_score,
        source_url=article.source_url,
        matched_terms=issue.get("matched_terms") or [],
        match_score=issue.get("match_score") or article.score.final_score,
    )


def _filter_results(
    results: list[SearchResult],
    *,
    tags: list[str] | None,
    minimum_score: float | None,
) -> list[SearchResult]:
    required_tags = {tag.lower() for tag in tags or []}
    filtered: list[SearchResult] = []
    for result in results:
        result_tags = {tag.lower() for tag in result.tags}
        if required_tags and not required_tags.intersection(result_tags):
            continue
        if minimum_score is not None and result.final_score < minimum_score:
            continue
        filtered.append(result)
    return filtered
