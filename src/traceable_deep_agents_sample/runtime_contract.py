from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RuntimeRunCreateRequest(BaseModel):
    input: str
    agent_id: str | None = None
    session_id: str | None = None
    messages: list[dict[str, str]] = Field(default_factory=list)
    summary: str | None = None
    session_instruction: str | None = None
    client_context: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


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

