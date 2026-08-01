# Runtime Interface

This sample targets the `traceable-agent-runtime` run/trace shape and can run
behind the runtime as an external Agent Server adapter.

## Compatible Shapes

The local adapter mirrors these runtime schemas:

- `RunCreateRequest`
- `RunResponse`
- `StepRecord`
- `RunTraceResponse`
- `AgentListResponse`

The trace URL follows the runtime convention:

```text
/v1/runs/{run_id}/trace
```

## External Adapter Direction

The current integration direction is external adapter first. The sample serves
the same run/trace shape over HTTP, and `traceable-agent-runtime` can call it
from an agent manifest with `external_adapter`.

This keeps the runtime core stable while the Deep Agents behavior evolves.

## Agent Capability

The sample advertises the `tech-radar` agent and replay support through
`GET /v1/agents`:

```json
{
  "agents": [
    {
      "id": "tech-radar",
      "capabilities": {
        "replay": {
          "live": true,
          "frozen": true,
          "frozen_tool_result_schema": "traceable-agent-runtime.frozen-tool-result.v1"
        }
      }
    }
  ]
}
```

The runtime combines this discovery response with the
`external_adapter.allowed_replay_modes` allowlist in its manifest before it
allows external frozen replay.

## Replay Request

Replay is represented as an optional `replay` object on the normal
`POST /v1/runs` request:

```json
{
  "input": "AI Agent tracing",
  "agent_id": "tech-radar",
  "replay": {
    "of_run_id": "run_original",
    "tool_mode": "frozen",
    "strict_tool_input_match": true,
    "frozen_tool_results": [
      {
        "tool_name": "search_tech_news",
        "tool_input": {
          "query": "AI Agent tracing",
          "limit": 3
        },
        "result": {
          "tool_name": "search_tech_news",
          "status": "success",
          "output": {},
          "error": null
        }
      }
    ]
  }
}
```

When `tool_mode` is `frozen`, the sample consumes the matching frozen tool
result before calling the live TechNews tool.

## TechNews Tools

The sample exposes read-only TechNews tools:

- `search_tech_news`: search published TechNews issues.
- `get_latest_tech_news`: fetch the latest published daily issue.
- `get_tech_news_article`: fetch one issue by slug.

`technews-publisher/scripts/geeknews_publish.py` derives `issue_date` as KST
today minus one day and creates titles like `GeekNews 어제자 요약 - YYYY-MM-DD`.
For "today's news" questions, the runtime-compatible adapter calls
`get_latest_tech_news` and adds a freshness note that today's collection may not
be available yet.

## Step Types

The adapter emits the runtime-style step names used by
`traceable-agent-runtime`:

```text
replay_started
run_started
manifest_loaded
prompt_composed
policy_decision
tool_call_started
tool_call_completed
final_answer
run_completed
replay_completed
run_failed
```

For tool paths, `policy_decision` must appear before `tool_call_started`.
Frozen replay tool steps include `tool_mode: "frozen"`.

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
