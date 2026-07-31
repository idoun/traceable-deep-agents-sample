#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from traceable_deep_agents_sample.runtime_adapter import TraceableRuntimeAdapter
from traceable_deep_agents_sample.runtime_contract import RuntimeRunCreateRequest


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate sample output against traceable-agent-runtime schemas.")
    parser.add_argument(
        "--runtime-src",
        default="../traceable-agent-runtime/src",
        help="Path to traceable-agent-runtime/src",
    )
    parser.add_argument("--query", default="AI Agent tracing")
    args = parser.parse_args()

    runtime_src = Path(args.runtime_src).resolve()
    if not runtime_src.exists():
        raise SystemExit(f"Runtime source path does not exist: {runtime_src}")
    sys.path.insert(0, str(runtime_src))

    from traceable_agent_runtime.schemas.runs import RunResponse, RunTraceResponse  # noqa: PLC0415

    adapter = TraceableRuntimeAdapter()
    run = adapter.run(
        RuntimeRunCreateRequest(
            input=args.query,
            client_context={"authorization": "Bearer synthetic-secret"},
        )
    )
    trace = adapter.get_trace(run.run_id)
    if trace is None:
        raise SystemExit(f"Trace not found for run: {run.run_id}")

    RunResponse.model_validate(run.model_dump())
    RunTraceResponse.model_validate(trace.model_dump())

    steps = [step.type for step in trace.steps]
    required = ["run_started", "policy_decision", "tool_call_started", "tool_call_completed", "final_answer", "run_completed"]
    missing = [step for step in required if step not in steps]
    if missing:
        raise SystemExit(f"Missing required trace steps: {missing}")
    if steps.index("policy_decision") > steps.index("tool_call_started"):
        raise SystemExit("policy_decision must be recorded before tool_call_started")
    if "synthetic-secret" in trace.model_dump_json():
        raise SystemExit("Trace leaked a synthetic secret")

    print(f"runtime contract ok: {run.run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

