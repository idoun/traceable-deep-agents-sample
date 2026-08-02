from __future__ import annotations

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
        return DeepPathResult(
            answer=_extract_answer(response),
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
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        for key in ("answer", "output", "content"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value
        messages = response.get("messages")
        if isinstance(messages, list) and messages:
            content = getattr(messages[-1], "content", None)
            if isinstance(content, str) and content.strip():
                return content
            if isinstance(messages[-1], dict):
                value = messages[-1].get("content")
                if isinstance(value, str) and value.strip():
                    return value
    content = getattr(response, "content", None)
    if isinstance(content, str) and content.strip():
        return content
    return str(response)


def _summarize_raw_output(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return {"keys": sorted(str(key) for key in response.keys())}
    return {"type": type(response).__name__}


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
