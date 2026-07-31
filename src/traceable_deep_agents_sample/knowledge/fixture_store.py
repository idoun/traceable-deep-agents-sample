import json
import re
from pathlib import Path

from traceable_deep_agents_sample.models import Article, SearchResult


class FixtureArticleStore:
    def __init__(self, path: Path):
        self.path = path
        self._articles: list[Article] | None = None

    def list_articles(self) -> list[Article]:
        if self._articles is None:
            rows = []
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(Article.model_validate(json.loads(line)))
            self._articles = sorted(rows, key=lambda item: item.issue_date, reverse=True)
        return list(self._articles)

    def get_article(self, slug: str) -> Article | None:
        return next((article for article in self.list_articles() if article.slug == slug), None)

    def latest(self, limit: int = 5, tags: list[str] | None = None, minimum_score: float | None = None) -> list[SearchResult]:
        return [
            self._to_result(article, [])
            for article in self._filter_articles(self.list_articles(), tags, minimum_score)
        ][:limit]

    def search(
        self,
        query: str,
        limit: int = 5,
        tags: list[str] | None = None,
        minimum_score: float | None = None,
    ) -> list[SearchResult]:
        terms = _terms(query)
        if not terms:
            return []

        results: list[SearchResult] = []
        for article in self._filter_articles(self.list_articles(), tags, minimum_score):
            haystack = " ".join(
                [
                    article.title,
                    article.short_summary,
                    article.impact_summary,
                    " ".join(article.tags),
                    article.score.recommended_action,
                    article.body,
                ]
            ).lower()
            matched = [term for term in terms if term in haystack]
            if not matched:
                continue
            result = self._to_result(article, matched)
            result.match_score = len(matched) * 10 + article.score.final_score
            results.append(result)

        results.sort(key=lambda item: (item.match_score, item.issue_date), reverse=True)
        return results[:limit]

    def _filter_articles(
        self,
        articles: list[Article],
        tags: list[str] | None,
        minimum_score: float | None,
    ) -> list[Article]:
        required_tags = {tag.lower() for tag in tags or []}
        filtered = []
        for article in articles:
            article_tags = {tag.lower() for tag in article.tags}
            if required_tags and not required_tags.intersection(article_tags):
                continue
            if minimum_score is not None and article.score.final_score < minimum_score:
                continue
            filtered.append(article)
        return filtered

    def _to_result(self, article: Article, matched_terms: list[str]) -> SearchResult:
        return SearchResult(
            slug=article.slug,
            title=article.title,
            issue_date=article.issue_date,
            summary=article.short_summary,
            tags=article.tags,
            final_score=article.score.final_score,
            source_url=article.source_url,
            matched_terms=matched_terms,
            match_score=article.score.final_score,
        )


def _terms(query: str) -> list[str]:
    terms = []
    for token in re.split(r"\s+", query.lower().strip()):
        if token and token not in terms:
            terms.append(token)
    return terms

