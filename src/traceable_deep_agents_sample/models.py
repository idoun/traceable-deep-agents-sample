from datetime import date

from pydantic import BaseModel, Field


class ArticleScore(BaseModel):
    interest_score: float = 0
    project_score: float = 0
    novelty_score: float = 0
    actionability_score: float = 0
    credibility_score: float = 0
    community_score: float = 0
    final_score: float = 0
    score_reason: str = ""
    recommended_action: str = ""


class Article(BaseModel):
    slug: str
    title: str
    issue_date: date
    source_url: str = ""
    short_summary: str
    impact_summary: str = ""
    action_items: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    radar_category: str = "Other"
    radar_status: str = "Assess"
    score: ArticleScore = Field(default_factory=ArticleScore)
    body: str = ""


class SearchResult(BaseModel):
    slug: str
    title: str
    issue_date: date
    summary: str
    tags: list[str]
    final_score: float
    source_url: str
    matched_terms: list[str] = Field(default_factory=list)
    match_score: float = 0


class Source(BaseModel):
    source_id: str
    slug: str
    title: str
    issue_date: date
    url: str
    excerpt: str
    relevance_score: float = 0


class AgentResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    run_id: str
    thread_id: str
    trace_path: str

