from typing import Any

from traceable_deep_agents_sample.runtime_contract import RuntimeRunCreateRequest

DEFAULT_TENANT_ID = "tenant:default"


def build_context_mesh(payload: RuntimeRunCreateRequest) -> dict[str, Any]:
    """Build a portable, tenant-scoped context envelope for this sample run."""

    tenant_id = payload.tenant_id or DEFAULT_TENANT_ID
    tenant_source = "request" if payload.tenant_id else "default"
    memory_namespaces = [f"tenant/{tenant_id}/agent/{payload.agent_id or 'tech-radar'}"]
    if payload.workspace_id:
        memory_namespaces.append(f"tenant/{tenant_id}/workspace/{payload.workspace_id}/knowledge")
    if payload.user_id:
        memory_namespaces.append(f"tenant/{tenant_id}/user/{payload.user_id}/preferences")
    if payload.session_id:
        memory_namespaces.append(f"tenant/{tenant_id}/session/{payload.session_id}/summary")

    return {
        "tenant": {"id": tenant_id, "source": tenant_source},
        "workspace": {"id": payload.workspace_id, "source": "request"} if payload.workspace_id else None,
        "user": {"id": payload.user_id, "source": "request"} if payload.user_id else None,
        "session": {"id": payload.session_id, "source": "request"} if payload.session_id else None,
        "memory": {"namespaces": memory_namespaces},
        "skills": {"allowed": []},
        "tools": {"bindings": []},
    }

