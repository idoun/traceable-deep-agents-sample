from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Route = Literal["light", "deep"]


@dataclass(frozen=True)
class ComplexityDecision:
    """Deterministic routing decision for the adaptive agent entrypoint."""

    route: Route
    score: float
    reasons: list[str]


class ComplexityRouter:
    """Cheap first-pass router for light vs. deep Tech Radar requests.

    The first version intentionally uses transparent rules instead of a model.
    It gives the trace a stable explanation for why the request stayed on the
    fast path or was considered a deep-reasoning candidate.
    """

    # Bootstrap v1 rules. Keep these transparent and testable while the runtime
    # grows toward tenant-configured routing policy and optional classifier use.
    _SYNTHESIS_MARKERS = (
        "비교",
        "전망",
        "전략",
        "우선순위",
        "리스크",
        "왜",
        "어떻게",
        "분석",
        "종합",
        "투자",
        "영향",
        "compare",
        "versus",
        "vs",
        "strategy",
        "risk",
        "why",
        "how",
        "analyze",
        "synthesize",
        "trend",
        "forecast",
        "priority",
        "impact",
    )
    _SIMPLE_MARKERS = (
        "오늘",
        "최신",
        "최근",
        "뉴스",
        "기사",
        "요약",
        "찾아",
        "알려줘",
        "today",
        "latest",
        "recent",
        "news",
        "article",
        "summary",
        "search",
    )
    # Multi-step markers are separate from synthesis markers so requests can be
    # routed deep for evidence expansion even when they do not ask for judgment.
    _MULTI_STEP_MARKERS = ("근거", "출처", "자세히", "보고서", "deep", "research", "evidence", "detail", "report")
    _FILTER_MARKERS = (
        "아닌",
        "제외",
        "빼고",
        "만",
        "not",
        "except",
        "exclude",
        "without",
        "only",
    )

    def classify(self, user_input: str) -> ComplexityDecision:
        normalized = " ".join(user_input.lower().split())
        reasons: list[str] = []
        score = 0.0

        synthesis_hits = _count_hits(normalized, self._SYNTHESIS_MARKERS)
        if synthesis_hits:
            score += min(0.55, 0.2 + synthesis_hits * 0.12)
            reasons.append("requires synthesis, comparison, or judgment")

        multi_step_hits = _count_hits(normalized, self._MULTI_STEP_MARKERS)
        if multi_step_hits:
            score += min(0.6, 0.2 + multi_step_hits * 0.12)
            reasons.append("asks for evidence expansion or report-style output")

        filter_hits = _count_hits(normalized, self._FILTER_MARKERS)
        if filter_hits:
            score += min(0.6, 0.25 + filter_hits * 0.15)
            reasons.append("requires semantic filtering or exclusion")

        if len(normalized) >= 80:
            score += 0.15
            reasons.append("long request likely needs planning")

        simple_hits = _count_hits(normalized, self._SIMPLE_MARKERS)
        if simple_hits and not synthesis_hits and not multi_step_hits and not filter_hits:
            score -= min(0.3, simple_hits * 0.08)
            reasons.append("single-step news lookup can use the light path")

        score = max(0.0, min(1.0, round(score, 2)))
        if score >= 0.5:
            return ComplexityDecision(route="deep", score=score, reasons=reasons or ["deep route threshold reached"])
        return ComplexityDecision(route="light", score=score, reasons=reasons or ["simple request"])


def _count_hits(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker in text)
