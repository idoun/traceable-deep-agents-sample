from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from inspect import signature
from typing import Any, Callable

from langchain_core.callbacks import BaseCallbackHandler

from traceable_deep_agents_sample.config import Settings
from traceable_deep_agents_sample.deep_agent import build_deep_agent
from traceable_deep_agents_sample.runtime_contract import RuntimeRunCreateRequest
from traceable_deep_agents_sample.skill_registry import SkillRef
from traceable_deep_agents_sample.tool_binding import ToolBinding


@dataclass(frozen=True)
class DeepPathResult:
    """Normalized result from the Deep Agents execution path."""

    answer: str
    raw_output: dict[str, Any]
    trace_events: list[dict[str, Any]]


class DeepPathRunner:
    """Invoke the Deep Agents graph behind the runtime-facing adapter boundary."""

    provider = "deepagents"
    model = "configured"

    def __init__(self, settings: Settings | None = None, agent_factory: Callable[..., Any] = build_deep_agent):
        self.settings = settings or Settings()
        self._agent_factory = agent_factory
        self.provider = self.settings.llm_provider.strip().lower() or "openai"
        self.model = _configured_model_name(self.settings)

    def run(
        self,
        *,
        payload: RuntimeRunCreateRequest,
        context_mesh: dict[str, Any],
        selected_skills: list[SkillRef],
        tool_binding: ToolBinding,
    ) -> DeepPathResult:
        agent = self._agent_factory(self.settings)
        agent_input = {
            "messages": [
                {
                    "role": "user",
                    "content": _compose_user_message(
                        payload=payload,
                        context_mesh=context_mesh,
                        selected_skills=selected_skills,
                        tool_binding=tool_binding,
                    ),
                }
            ]
        }
        collector = DeepTraceCallbackHandler()
        response = _invoke_agent(agent, agent_input, collector)
        answer = _extract_final_answer(response)
        if not answer:
            retry_input = _compose_synthesis_retry_input(response)
            if retry_input is not None:
                retry_response = _invoke_agent(agent, retry_input, collector)
                retry_answer = _extract_final_answer(retry_response)
                if retry_answer:
                    response = retry_response
                    answer = retry_answer
        return DeepPathResult(
            answer=answer or _extract_answer(response),
            raw_output=_summarize_raw_output(response),
            trace_events=collector.events,
        )


class DeepTraceCallbackHandler(BaseCallbackHandler):
    """Collect LangChain model/tool callbacks as portable trace events."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def on_chat_model_start(self, serialized: dict[str, Any], messages: list, **kwargs: Any) -> None:
        del kwargs
        self.events.append(
            {
                "step_type": "deep_model_call_started",
                "summary": "Deep Agents chat model call started.",
                "input_json": {"model": _serialized_name(serialized), "message_count": len(messages)},
            }
        )

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        del kwargs
        self.events.append(
            {
                "step_type": "deep_model_call_started",
                "summary": "Deep Agents LLM call started.",
                "input_json": {"model": _serialized_name(serialized), "prompt_count": len(prompts)},
            }
        )

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        del kwargs
        self.events.append(
            {
                "step_type": "deep_model_call_completed",
                "summary": "Deep Agents model call completed.",
                "output_json": {"response_type": type(response).__name__},
            }
        )

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        del kwargs
        self.events.append(
            {
                "step_type": "deep_model_call_failed",
                "summary": "Deep Agents model call failed.",
                "status": "failed",
                "error": str(error),
            }
        )

    def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        del kwargs
        self.events.append(
            {
                "step_type": "deep_tool_call_started",
                "summary": "Deep Agents tool call started.",
                "input_json": {"tool_name": _serialized_name(serialized), "input": input_str},
            }
        )

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        del kwargs
        self.events.append(
            {
                "step_type": "deep_tool_call_completed",
                "summary": "Deep Agents tool call completed.",
                "output_json": {"output_type": type(output).__name__},
            }
        )

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        del kwargs
        self.events.append(
            {
                "step_type": "deep_tool_call_failed",
                "summary": "Deep Agents tool call failed.",
                "status": "failed",
                "error": str(error),
            }
        )


def _invoke_agent(agent: Any, agent_input: dict[str, Any], collector: DeepTraceCallbackHandler) -> Any:
    invoke = agent.invoke
    if "config" in signature(invoke).parameters:
        return invoke(agent_input, config={"callbacks": [collector]})
    return invoke(agent_input)


def _compose_user_message(
    *,
    payload: RuntimeRunCreateRequest,
    context_mesh: dict[str, Any],
    selected_skills: list[SkillRef],
    tool_binding: ToolBinding,
) -> str:
    skill_ids = ", ".join(skill.skill_id for skill in selected_skills) or "none"
    return "\n".join(
        [
            payload.input,
            "",
            "Runtime context:",
            f"- tenant_id: {context_mesh['tenant']['id']}",
            f"- selected_skills: {skill_ids}",
            f"- allowed_tool_binding: {tool_binding.binding_id}",
            f"- allowed_scopes: {', '.join(tool_binding.allowed_scopes)}",
            "",
            "Use only the supplied read-only Tech Radar tools and cite the evidence you use.",
        ]
    )


def _extract_answer(response: Any) -> str:
    answer = _extract_final_answer(response)
    if answer:
        return answer
    if isinstance(response, Mapping):
        messages = response.get("messages")
        if isinstance(messages, list) and messages:
            tool_summary = _extract_tool_result_summary(messages)
            if tool_summary:
                return tool_summary
    return str(response)


def _extract_final_answer(response: Any) -> str | None:
    if isinstance(response, str):
        return response if response.strip() else None
    if isinstance(response, Mapping):
        for key in ("answer", "output", "content"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value
        messages = response.get("messages")
        if isinstance(messages, list) and messages:
            return _extract_final_assistant_content(messages)
    content = getattr(response, "content", None)
    if isinstance(content, str) and content.strip():
        return content
    return None


def _compose_synthesis_retry_input(response: Any) -> dict[str, Any] | None:
    if not isinstance(response, Mapping):
        return None
    messages = response.get("messages")
    if not isinstance(messages, list) or not messages:
        return None
    if _extract_tool_result_summary(messages) is None:
        return None
    return {
        "messages": [
            *messages,
            {
                "role": "user",
                "content": (
                    "위 Tech Radar tool 결과만 근거로 사용해서 사용자 질문에 대한 최종 답변을 한국어로 작성하세요. "
                    "raw JSON, Python 객체 repr, 내부 메시지 목록은 출력하지 말고, 비교/전망/리스크를 간결하게 정리하세요."
                ),
            },
        ]
    }


def _summarize_raw_output(response: Any) -> dict[str, Any]:
    if isinstance(response, Mapping):
        return {"keys": sorted(str(key) for key in response.keys())}
    return {"type": type(response).__name__}


def _extract_final_assistant_content(messages: list[Any]) -> str | None:
    for message in reversed(messages):
        if _message_role(message) not in {"assistant", "ai", "aimessage"}:
            continue
        content = _message_content(message)
        if content:
            return content
    return None


def _extract_tool_result_summary(messages: list[Any]) -> str | None:
    for message in reversed(messages):
        if _message_role(message) not in {"tool", "toolmessage"}:
            continue
        content = _message_content(message)
        if not content:
            continue
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return content
        return _summarize_tool_payload(payload)
    return None


def _message_role(message: Any) -> str:
    if isinstance(message, Mapping):
        value = message.get("role") or message.get("type")
        if isinstance(value, str):
            return value.lower()
    for attribute in ("role", "type"):
        value = getattr(message, attribute, None)
        if isinstance(value, str):
            return value.lower()
    return type(message).__name__.lower()


def _message_content(message: Any) -> str | None:
    if isinstance(message, Mapping):
        value = message.get("content")
    else:
        value = getattr(message, "content", None)
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, list):
        text_parts = []
        for item in value:
            if isinstance(item, str) and item.strip():
                text_parts.append(item)
            elif isinstance(item, Mapping):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text)
        if text_parts:
            return "\n".join(text_parts)
    return None


def _summarize_tool_payload(payload: Any) -> str:
    if not isinstance(payload, Mapping):
        return json.dumps(payload, ensure_ascii=False)
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        return "Deep Agents path가 tool call은 완료했지만 최종 assistant 답변을 반환하지 않았습니다."
    bullets = []
    for item in results[:5]:
        if not isinstance(item, Mapping):
            continue
        title = str(item.get("title") or item.get("slug") or "Untitled result")
        summary = str(item.get("summary") or "").strip()
        bullets.append(f"- {title}: {summary}" if summary else f"- {title}")
    if not bullets:
        return "Deep Agents path가 tool call은 완료했지만 최종 assistant 답변을 반환하지 않았습니다."
    return "\n".join(
        [
            "Deep Agents path가 tool call은 완료했지만 최종 assistant 답변을 반환하지 않았습니다.",
            "마지막 TechNews tool 결과 요약:",
            "",
            *bullets,
        ]
    )


def _serialized_name(serialized: dict[str, Any]) -> str | None:
    name = serialized.get("name")
    if isinstance(name, str):
        return name
    identifier = serialized.get("id")
    if isinstance(identifier, list) and identifier:
        return str(identifier[-1])
    if isinstance(identifier, str):
        return identifier
    return None


def _configured_model_name(settings: Settings) -> str:
    if settings.model.strip():
        return settings.model.strip()
    provider = settings.llm_provider.strip().lower()
    if provider == "gemini":
        return settings.gemini_model
    return settings.llm_model
