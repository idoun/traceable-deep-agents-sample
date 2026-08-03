from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal


Route = Literal["light", "deep"]


@dataclass(frozen=True)
class ComplexityDecision:
    """Deterministic routing decision for the adaptive agent entrypoint."""

    route: Route
    score: float
    reasons: list[str]
    signals: dict[str, list[str]]


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
        "how can",
        "how could",
        "how does",
        "how should",
        "how will",
        "how would",
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
        "not",
        "except",
        "exclude",
        "without",
    )

    def classify(self, user_input: str) -> ComplexityDecision:
        normalized = " ".join(user_input.lower().split())
        reasons: list[str] = []
        signals: dict[str, list[str]] = {}
        score = 0.0

        synthesis_markers = _matching_markers(normalized, self._SYNTHESIS_MARKERS)
        if synthesis_markers:
            score += min(0.65, 0.5 + len(synthesis_markers) * 0.08)
            signals["synthesis"] = synthesis_markers
            reasons.append("requires synthesis, comparison, or judgment")

        multi_step_markers = _matching_markers(normalized, self._MULTI_STEP_MARKERS)
        if multi_step_markers:
            score += min(0.65, 0.5 + len(multi_step_markers) * 0.08)
            signals["multi_step"] = multi_step_markers
            reasons.append("asks for evidence expansion or report-style output")

        filter_markers = _matching_markers(normalized, self._FILTER_MARKERS)
        if filter_markers:
            score += min(0.65, 0.5 + len(filter_markers) * 0.08)
            signals["semantic_filter"] = filter_markers
            reasons.append("requires semantic filtering or exclusion")

        if len(normalized) >= 80:
            score += 0.15
            signals["length"] = [">=80"]
            reasons.append("long request likely needs planning")

        simple_markers = _matching_markers(normalized, self._SIMPLE_MARKERS)
        if simple_markers and not synthesis_markers and not multi_step_markers and not filter_markers:
            score -= min(0.3, len(simple_markers) * 0.08)
            signals["simple_lookup"] = simple_markers
            reasons.append("single-step news lookup can use the light path")

        score = max(0.0, min(1.0, round(score, 2)))
        if score >= 0.5:
            return ComplexityDecision(
                route="deep",
                score=score,
                reasons=reasons or ["deep route threshold reached"],
                signals=signals,
            )
        return ComplexityDecision(route="light", score=score, reasons=reasons or ["simple request"], signals=signals)


def _matching_markers(text: str, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if _matches_marker(text, marker)]


def _matches_marker(text: str, marker: str) -> bool:
    if marker.isascii():
        # English markers need token boundaries so "how" does not match "show".
        return re.search(rf"(?<![a-z0-9_]){re.escape(marker)}(?![a-z0-9_])", text) is not None
    return marker in text
