from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RuntimeRunCreateRequest(BaseModel):
    input: str
    agent_id: str | None = None
    tenant_id: str | None = None
    workspace_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    messages: list[dict[str, str]] = Field(default_factory=list)
    summary: str | None = None
    session_instruction: str | None = None
    client_context: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    replay: "RuntimeReplayContext | None" = None


class RuntimeFrozenToolResult(BaseModel):
    tool_name: str
    tool_input: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)


class RuntimeReplayContext(BaseModel):
    of_run_id: str
    tool_mode: str = "live"
    strict_tool_input_match: bool = True
    frozen_tool_results: list[RuntimeFrozenToolResult] = Field(default_factory=list)


class RuntimeRunStats(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    total_time_ms: float
    ttft_ms: float | None = None


class RuntimeStepRecord(BaseModel):
    step_id: str
    run_id: str
    sequence: int
    type: str
    summary: str
    status: str
    input_json: dict[str, Any] = Field(default_factory=dict)
    output_json: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    ended_at: datetime
    latency_ms: float
    error: str | None = None


class RuntimeRunResponse(BaseModel):
    run_id: str
    replay_of_run_id: str | None = None
    replay_tool_mode: str | None = None
    tenant_id: str | None = None
    workspace_id: str | None = None
    user_id: str | None = None
    session_id: str | None
    status: str
    agent_id: str
    manifest_version: str | None = None
    output_text: str | None = None
    error_message: str | None = None
    stats: RuntimeRunStats | None = None
    trace_url: str
    created_at: datetime
    completed_at: datetime | None = None


class RuntimeTraceResponse(BaseModel):
    run: RuntimeRunResponse
    steps: list[RuntimeStepRecord]


class RuntimeReplayCapabilities(BaseModel):
    live: bool = True
    frozen: bool = True
    frozen_tool_result_schema: str = "traceable-agent-runtime.frozen-tool-result.v1"


class RuntimeAgentCapabilities(BaseModel):
    streaming: bool = False
    tools: bool = True
    trace_lookup: bool = True
    replay: RuntimeReplayCapabilities = Field(default_factory=RuntimeReplayCapabilities)


class RuntimePublicAgent(BaseModel):
    id: str
    agent_id: str
    name: str
    description: str
    manifest_version: str
    tools: list[str] = Field(default_factory=list)
    capabilities: RuntimeAgentCapabilities = Field(default_factory=RuntimeAgentCapabilities)


class RuntimeAgentListResponse(BaseModel):
    agents: list[RuntimePublicAgent]
