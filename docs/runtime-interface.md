# Runtime Interface

This sample targets the `traceable-agent-runtime` run/trace shape before direct
server integration.

## Compatible Shapes

The local adapter mirrors these runtime schemas:

- `RunCreateRequest`
- `RunResponse`
- `StepRecord`
- `RunTraceResponse`

The trace URL follows the runtime convention:

```text
/v1/runs/{run_id}/trace
```

## External Adapter Direction

The current integration direction is an external adapter first. The sample
serves the same run/trace shape over HTTP, and `traceable-agent-runtime` can
later call it as a proxy target or wrap it as a native adapter.

This keeps the runtime core stable while the Deep Agents behavior evolves.

## Step Types

The adapter emits the runtime-style step names used by
`traceable-agent-runtime`:

```text
run_started
manifest_loaded
prompt_composed
policy_decision
tool_call_started
tool_call_completed
final_answer
run_completed
run_failed
```

For tool paths, `policy_decision` must appear before `tool_call_started`.

## Current Boundary

This is not yet a `traceable-agent-runtime` plugin or manifest. It is a local
contract adapter that proves the sample can produce the same run/trace response
shape. The next integration step is to decide whether the runtime should call
this package as an external adapter or absorb the agent as a runtime manifest
plus local tools.

## Contract Check

When this repository sits beside `traceable-agent-runtime`, run:

```bash
python scripts/check_runtime_contract.py
```

The script validates the adapter output against the real runtime Pydantic
schemas and checks that policy is recorded before tool execution.
