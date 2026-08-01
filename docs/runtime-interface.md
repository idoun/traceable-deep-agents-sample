# Runtime Interface

This sample targets the `traceable-agent-runtime` run/trace shape and can run
behind the runtime as an external Agent Server adapter.

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

The current integration direction is external adapter first. The sample serves
the same run/trace shape over HTTP, and `traceable-agent-runtime` can call it
from an agent manifest with `external_adapter`.

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

This is not a native `traceable-agent-runtime` plugin. It remains a separate
service, and the runtime delegates to it through a manifest such as
`agents/tech-radar.yaml`. The runtime then imports the external trace into its
own trace store so normal trace lookup, replay, eval, and UI paths can stay on
the runtime API.

## Contract Check

When this repository sits beside `traceable-agent-runtime`, run:

```bash
python scripts/check_runtime_contract.py
```

The script validates the adapter output against the real runtime Pydantic
schemas and checks that policy is recorded before tool execution.
