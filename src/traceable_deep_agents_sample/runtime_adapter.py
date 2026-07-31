from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from traceable_deep_agents_sample.agent import NO_EVIDENCE
from traceable_deep_agents_sample.config import Settings
from traceable_deep_agents_sample.knowledge.fixture_store import FixtureArticleStore
from traceable_deep_agents_sample.runtime_contract import (
    RuntimeRunCreateRequest,
    RuntimeRunResponse,
    RuntimeRunStats,
    RuntimeStepRecord,
    RuntimeTraceResponse,
)
from traceable_deep_agents_sample.tools import TechRadarTools

MANIFEST_VERSION = "traceable-deep-agents-sample.v1"
RUNTIME_STEP_TYPES = {
    "run_started",
    "manifest_loaded",
    "prompt_composed",
    "policy_decision",
    "tool_call_started",
    "tool_call_completed",
    "tool_call_failed",
    "final_answer",
    "run_completed",
    "run_failed",
}


class TraceableRuntimeAdapter:
    """Local adapter that emits traceable-agent-runtime-shaped run traces."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self._traces: dict[str, RuntimeTraceResponse] = {}

    def run(self, payload: RuntimeRunCreateRequest) -> RuntimeRunResponse:
        started = perf_counter()
        run_id = f"run_{uuid4().hex}"
        created_at = _now()
        agent_id = payload.agent_id or self.settings.agent_id
        run = RuntimeRunResponse(
            run_id=run_id,
            session_id=payload.session_id,
            status="running",
            agent_id=agent_id,
            manifest_version=MANIFEST_VERSION,
            trace_url=f"/v1/runs/{run_id}/trace",
            created_at=created_at,
        )
        steps: list[RuntimeStepRecord] = []

        def record(step_type: str, summary: str, input_json=None, output_json=None, status: str = "completed", error: str | None = None):
            steps.append(
                _step(
                    run_id=run_id,
                    sequence=len(steps) + 1,
                    step_type=step_type,
                    summary=summary,
                    input_json=_redact(input_json or {}),
                    output_json=_redact(output_json or {}),
                    status=status,
                    error=error,
                )
            )

        try:
            record(
                "run_started",
                "Run accepted by TraceableRuntimeAdapter.",
                input_json={"agent_id": agent_id, "stream": payload.stream},
                output_json={"status": "started"},
            )
            record(
                "manifest_loaded",
                "Sample agent manifest loaded.",
                input_json={"requested_agent_id": payload.agent_id or self.settings.agent_id},
                output_json={
                    "id": self.settings.agent_id,
                    "name": self.settings.agent_name,
                    "manifest_version": MANIFEST_VERSION,
                    "tools": ["search_tech_news", "get_tech_news_article", "get_latest_tech_news"],
                    "policy": {"read_only": True, "max_tool_calls": 3},
                },
            )
            record(
                "prompt_composed",
                "Runtime-compatible prompt context prepared.",
                input_json={
                    "input_length": len(payload.input),
                    "has_session_instruction": bool(payload.session_instruction),
                    "has_client_context": bool(payload.client_context),
                    "client_context": payload.client_context,
                },
                output_json={"message_count": len(payload.messages) + 1},
            )
            record(
                "policy_decision",
                "Read-only search tool allowed.",
                input_json={"tool_name": "search_tech_news"},
                output_json={"decision": "allow", "reason": "tool is read-only and declared"},
            )

            tools = TechRadarTools(FixtureArticleStore(self.settings.data_path))
            record(
                "tool_call_started",
                "Tech Radar search started.",
                input_json={"tool_name": "search_tech_news", "tool_input": {"query": payload.input, "limit": 3}},
            )
            search_result = tools.search_tech_news(payload.input, limit=3)
            record(
                "tool_call_completed",
                "Tech Radar search completed.",
                output_json={
                    "tool_name": "search_tech_news",
                    "result_count": search_result["total_results"],
                    "slugs": [item["slug"] for item in search_result["results"]],
                },
            )

            answer = _answer_from_search(search_result)
            record(
                "final_answer",
                "Final answer prepared.",
                input_json={"source_count": search_result["total_results"]},
                output_json={"answer": answer},
            )
            record("run_completed", "Run completed successfully.", output_json={"status": "completed"})
            completed_at = _now()
            run = run.model_copy(
                update={
                    "status": "completed",
                    "output_text": answer,
                    "stats": RuntimeRunStats(
                        model="deterministic-fixture",
                        input_tokens=_count_words(payload.input),
                        output_tokens=_count_words(answer),
                        total_time_ms=round((perf_counter() - started) * 1000, 3),
                    ),
                    "completed_at": completed_at,
                }
            )
        except Exception as exc:
            message = str(exc).strip() or "Runtime adapter failed"
            record("run_failed", "Run failed.", status="failed", error=message)
            run = run.model_copy(update={"status": "failed", "error_message": message, "completed_at": _now()})

        trace = RuntimeTraceResponse(run=run, steps=steps)
        self._traces[run_id] = trace
        return run

    def get_trace(self, run_id: str) -> RuntimeTraceResponse | None:
        return self._traces.get(run_id)


def _answer_from_search(search_result: dict) -> str:
    if not search_result["results"]:
        return NO_EVIDENCE
    bullets = "\n".join(f"- {item['title']}: {item['summary']}" for item in search_result["results"])
    return f"수집된 Tech Radar 데이터에서 관련 근거를 찾았습니다.\n\n{bullets}"


def _step(
    *,
    run_id: str,
    sequence: int,
    step_type: str,
    summary: str,
    input_json: dict,
    output_json: dict,
    status: str = "completed",
    error: str | None = None,
) -> RuntimeStepRecord:
    if step_type not in RUNTIME_STEP_TYPES:
        raise ValueError(f"Unsupported runtime step type: {step_type}")
    now = _now()
    return RuntimeStepRecord(
        step_id=f"step_{uuid4().hex}",
        run_id=run_id,
        sequence=sequence,
        type=step_type,
        summary=summary,
        status=status,
        input_json=input_json,
        output_json=output_json,
        started_at=now,
        ended_at=now,
        latency_ms=0,
        error=_redact(error),
    )


def _redact(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            lowered = key.lower()
            if any(marker in lowered for marker in ("authorization", "api_key", "token", "cookie", "secret", "password")):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str) and value.lower().startswith("bearer "):
        return "Bearer [REDACTED]"
    return value


def _count_words(text: str) -> int:
    return len(text.split())


def _now() -> datetime:
    return datetime.now(timezone.utc)
