from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from traceable_deep_agents_sample.agent import NO_EVIDENCE
from traceable_deep_agents_sample.complexity_router import ComplexityRouter
from traceable_deep_agents_sample.config import Settings
from traceable_deep_agents_sample.context_mesh import build_context_mesh
from traceable_deep_agents_sample.knowledge.fixture_store import FixtureArticleStore
from traceable_deep_agents_sample.knowledge.technews_api_store import TechNewsApiStore
from traceable_deep_agents_sample.runtime_contract import (
    RuntimeRunCreateRequest,
    RuntimeRunResponse,
    RuntimeRunStats,
    RuntimeStepRecord,
    RuntimeTraceResponse,
)
from traceable_deep_agents_sample.skill_registry import SkillRegistry
from traceable_deep_agents_sample.tool_binding import ToolBindingResolver
from traceable_deep_agents_sample.tools import TechRadarTools

MANIFEST_VERSION = "traceable-deep-agents-sample.v1"
RUNTIME_STEP_TYPES = {
    "run_started",
    "replay_started",
    "replay_completed",
    "replay_failed",
    "manifest_loaded",
    "context_mesh_built",
    "prompt_composed",
    "complexity_classified",
    "route_selected",
    "skill_catalog_filtered",
    "skill_loaded",
    "light_plan_created",
    "tool_binding_resolved",
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
        context_mesh = build_context_mesh(payload)
        run = RuntimeRunResponse(
            run_id=run_id,
            replay_of_run_id=payload.replay.of_run_id if payload.replay else None,
            replay_tool_mode=payload.replay.tool_mode if payload.replay else None,
            tenant_id=context_mesh["tenant"]["id"],
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
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
            if payload.replay:
                record(
                    "replay_started",
                    "Replay run started by external adapter.",
                    input_json={"replay_of_run_id": payload.replay.of_run_id, "tool_mode": payload.replay.tool_mode},
                    output_json={"run_id": run_id},
                )
            record(
                "run_started",
                "Run accepted by TraceableRuntimeAdapter.",
                input_json={"agent_id": agent_id, "stream": payload.stream},
                output_json={"status": "started"},
            )
            record(
                "context_mesh_built",
                "Tenant-scoped ContextMesh built for this sample run.",
                input_json={
                    "tenant_id": payload.tenant_id,
                    "workspace_id": payload.workspace_id,
                    "user_id": payload.user_id,
                    "session_id": payload.session_id,
                },
                output_json=context_mesh,
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

            complexity = ComplexityRouter().classify(payload.input)
            requested_route = _requested_route(self.settings.execution_mode, complexity.route)
            selected_route = "light"
            fallback_reason = None
            if requested_route == "deep":
                fallback_reason = "Deep Agents execution is not yet wired into the runtime-facing path."
            record(
                "complexity_classified",
                "Request complexity classified by deterministic router.",
                input_json={"input": payload.input, "execution_mode": self.settings.execution_mode},
                output_json={
                    "score": complexity.score,
                    "route": complexity.route,
                    "reasons": complexity.reasons,
                    "router": "deterministic.v1",
                },
            )
            record(
                "route_selected",
                "Adaptive execution route selected.",
                input_json={
                    "classified_route": complexity.route,
                    "execution_mode": self.settings.execution_mode,
                    "deep_path_enabled": self.settings.deep_path_enabled,
                },
                output_json={
                    "requested_route": requested_route,
                    "selected_route": selected_route,
                    "fallback_reason": fallback_reason,
                },
            )
            skill_registry = SkillRegistry()
            selected_skills = skill_registry.select(user_input=payload.input, decision=complexity)
            record(
                "skill_catalog_filtered",
                "Tenant-scoped skill catalog filtered for this run.",
                input_json={
                    "tenant_id": context_mesh["tenant"]["id"],
                    "route": complexity.route,
                    "available_skill_ids": skill_registry.list_skill_ids(),
                },
                output_json={
                    "selected_skill_ids": [skill.skill_id for skill in selected_skills],
                    "selection_reasons": {skill.skill_id: skill.reason for skill in selected_skills},
                },
            )
            for skill in selected_skills:
                record(
                    "skill_loaded",
                    "Portable Agent Skill loaded for this run.",
                    input_json={"skill_id": skill.skill_id, "reason": skill.reason},
                    output_json={
                        "skill_id": skill.skill_id,
                        "name": skill.name,
                        "version": skill.version,
                        "hash": skill.hash,
                        "path": skill.path,
                    },
                )
            tool_name = _selected_tool_name(payload.input)
            tool_input = _tool_input(tool_name, payload.input)
            tool_binding_resolver = ToolBindingResolver()
            tool_binding = tool_binding_resolver.resolve(tenant_id=context_mesh["tenant"]["id"], tool_name=tool_name)
            record(
                "tool_binding_resolved",
                "Tenant-scoped Tool Binding resolved for this tool call.",
                input_json={
                    "tool_name": tool_name,
                    "tenant_id": context_mesh["tenant"]["id"],
                    "available_tool_definitions": tool_binding_resolver.list_definitions(),
                },
                output_json=tool_binding.to_trace_payload(),
            )
            record(
                "policy_decision",
                "Read-only TechNews tool allowed.",
                input_json={"tool_name": tool_name, "binding_id": tool_binding.binding_id},
                output_json={
                    "decision": "allow",
                    "reason": "tool binding is read-only and tenant-scoped",
                    "allowed_scopes": tool_binding.allowed_scopes,
                },
            )

            # Keep the runtime-facing adapter on the same knowledge backend as
            # Deep Agents tools, so external server smoke tests exercise real data.
            tools = TechRadarTools(_build_store(self.settings))
            record(
                "light_plan_created",
                "Light path planned a single read-only TechNews tool call.",
                input_json={"route": selected_route},
                output_json={"tool_name": tool_name, "tool_input": tool_input, "max_tool_calls": 1},
            )
            record(
                "tool_call_started",
                "Tech Radar tool call started.",
                input_json={"tool_name": tool_name, "tool_input": tool_input, "tool_mode": _tool_mode(payload)},
            )
            frozen_result = _frozen_tool_result(payload, tool_name=tool_name, tool_input=tool_input)
            search_result = frozen_result if frozen_result is not None else _execute_tool(tools, tool_name, tool_input)
            record(
                "tool_call_completed",
                "Tech Radar tool call completed.",
                output_json={
                    "tool_name": tool_name,
                    "status": "success",
                    "output": search_result,
                    "error": None,
                    "tool_mode": _tool_mode(payload),
                },
            )

            answer = _answer_from_search(search_result, freshness_note=_freshness_note(payload.input, search_result))
            record(
                "final_answer",
                "Final answer prepared.",
                input_json={"source_count": search_result["total_results"]},
                output_json={"answer": answer},
            )
            record("run_completed", "Run completed successfully.", output_json={"status": "completed"})
            if payload.replay:
                record(
                    "replay_completed",
                    "Replay run completed by external adapter.",
                    input_json={"replay_of_run_id": payload.replay.of_run_id, "tool_mode": payload.replay.tool_mode},
                    output_json={"status": "completed"},
                )
            completed_at = _now()
            run = run.model_copy(
                update={
                    "status": "completed",
                    "output_text": answer,
                    "stats": RuntimeRunStats(
                        model=f"deterministic-{self.settings.knowledge_backend}",
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


def _answer_from_search(search_result: dict, *, freshness_note: str | None = None) -> str:
    if not search_result["results"]:
        return NO_EVIDENCE
    bullets = "\n".join(f"- {item['title']}: {item['summary']}" for item in search_result["results"])
    prefix = f"{freshness_note}\n\n" if freshness_note else ""
    return f"{prefix}수집된 Tech Radar 데이터에서 관련 근거를 찾았습니다.\n\n{bullets}"


def _selected_tool_name(user_input: str) -> str:
    return "get_latest_tech_news" if _asks_for_today_news(user_input) else "search_tech_news"


def _tool_input(tool_name: str, user_input: str) -> dict:
    if tool_name == "get_latest_tech_news":
        return {"limit": 3}
    return {"query": user_input, "limit": 3}


def _execute_tool(tools: TechRadarTools, tool_name: str, tool_input: dict) -> dict:
    if tool_name == "get_latest_tech_news":
        return tools.get_latest_tech_news(limit=tool_input["limit"])
    return tools.search_tech_news(tool_input["query"], limit=tool_input["limit"])


def _requested_route(execution_mode: str, classified_route: str) -> str:
    mode = execution_mode.strip().lower()
    if mode in {"light", "deep"}:
        return mode
    return classified_route


def _asks_for_today_news(user_input: str) -> bool:
    lowered = user_input.lower()
    return ("오늘" in user_input or "today" in lowered) and ("뉴스" in user_input or "news" in lowered)


def _freshness_note(user_input: str, search_result: dict) -> str | None:
    if not _asks_for_today_news(user_input):
        return None
    latest_date = None
    if search_result.get("results"):
        latest_date = search_result["results"][0].get("issue_date")
    suffix = f" 최신 수집분({latest_date}) 기준으로 알려드릴게요." if latest_date else " 최신 수집분 기준으로 알려드릴게요."
    return f"오늘 뉴스는 아직 문서 수집이 완료되지 않았을 수 있습니다. TechNews는 매일 아침 전날 기준 GeekNews 요약을 저장합니다.{suffix}"


def _tool_mode(payload: RuntimeRunCreateRequest) -> str:
    return payload.replay.tool_mode if payload.replay is not None else "live"


def _frozen_tool_result(payload: RuntimeRunCreateRequest, *, tool_name: str, tool_input: dict) -> dict | None:
    replay = payload.replay
    if replay is None or replay.tool_mode != "frozen":
        return None
    if not replay.frozen_tool_results:
        raise ValueError(f"No frozen tool result provided for {tool_name}")
    frozen = replay.frozen_tool_results[0]
    if frozen.tool_name != tool_name:
        raise ValueError(f"Frozen tool mismatch: expected {frozen.tool_name}, got {tool_name}")
    if replay.strict_tool_input_match and frozen.tool_input != tool_input:
        raise ValueError(f"Frozen tool input mismatch for {tool_name}")
    result = frozen.result
    if result.get("status") not in (None, "success"):
        raise ValueError(str(result.get("error") or f"Frozen tool failed: {tool_name}"))
    output = result.get("output")
    if not isinstance(output, dict):
        raise ValueError(f"Frozen tool result output must be an object for {tool_name}")
    return output


def _build_store(settings: Settings):
    if settings.knowledge_backend == "fixture":
        return FixtureArticleStore(settings.data_path)
    if settings.knowledge_backend == "technews":
        return TechNewsApiStore(
            base_url=settings.technews_api_base_url,
            timeout=settings.technews_request_timeout,
            auth_token=settings.technews_auth_token,
            session_cookie=settings.technews_session_cookie,
        )
    raise ValueError(f"Unsupported knowledge backend: {settings.knowledge_backend}")


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
