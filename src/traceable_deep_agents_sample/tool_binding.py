from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Literal


ToolScope = Literal["read:issues", "read:issue-detail"]


@dataclass(frozen=True)
class ToolDefinition:
    """Model-visible tool shape independent from tenant credentials."""

    name: str
    kind: Literal["read_only"]
    scopes: tuple[ToolScope, ...]


@dataclass(frozen=True)
class ToolBinding:
    """Tenant-scoped runtime binding for a declared tool."""

    tool_name: str
    binding_id: str
    tenant_id: str
    allowed_scopes: tuple[ToolScope, ...]
    credential_ref_hash: str
    credential_ref: str = "[REDACTED]"

    def to_trace_payload(self) -> dict:
        return asdict(self)


class ToolBindingResolver:
    """Resolve read-only TechNews tools through a tenant-scoped binding."""

    _DEFINITIONS = {
        "search_tech_news": ToolDefinition(name="search_tech_news", kind="read_only", scopes=("read:issues",)),
        "get_latest_tech_news": ToolDefinition(name="get_latest_tech_news", kind="read_only", scopes=("read:issues",)),
        "get_tech_news_article": ToolDefinition(name="get_tech_news_article", kind="read_only", scopes=("read:issue-detail",)),
    }

    def resolve(self, *, tenant_id: str, tool_name: str) -> ToolBinding:
        definition = self._DEFINITIONS.get(tool_name)
        if definition is None:
            raise ValueError(f"Unknown tool binding: {tool_name}")
        credential_ref = f"secret://tenant/{tenant_id}/tools/technews/read"
        return ToolBinding(
            tool_name=definition.name,
            binding_id=f"{tenant_id}:technews.read",
            tenant_id=tenant_id,
            allowed_scopes=definition.scopes,
            credential_ref_hash=f"sha256:{sha256(credential_ref.encode('utf-8')).hexdigest()}",
        )

    def list_definitions(self) -> list[dict]:
        return [asdict(definition) for definition in self._DEFINITIONS.values()]
