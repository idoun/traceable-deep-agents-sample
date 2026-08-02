from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

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
        response = agent.invoke(
            {
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
        )
        return DeepPathResult(answer=_extract_answer(response), raw_output=_summarize_raw_output(response))


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
