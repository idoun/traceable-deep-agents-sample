# Architecture

This sample is an external Agent Server adapter for `traceable-agent-runtime`.
The runtime owns the public API, trace store, replay, eval, and Workbench
integration. The sample owns the Tech Radar behavior and read-only TechNews
tools.

Open the standalone diagram at [`architecture.html`](architecture.html).

## Runtime Boundary

`traceable-agent-runtime` exposes the public Agent Server API:

- `GET /v1/agents`
- `POST /v1/runs`
- `POST /v1/runs/{run_id}/replay`
- `GET /v1/runs/{run_id}/trace`

For `agent_id=tech-radar`, the runtime reads
`traceable-agent-runtime/agents/tech-radar.yaml` and delegates execution to this
sample through `external_adapter`.

## Sample Boundary

`traceable-deep-agents-sample` exposes a runtime-compatible external service:

- `GET /health`
- `GET /v1/agents`
- `POST /v1/runs`
- `GET /v1/runs/{run_id}/trace`

The sample advertises its capabilities through `GET /v1/agents`. Runtime uses
that discovery response together with its own manifest allowlist before it
allows external frozen replay.

## Tool Layer

The sample has three read-only TechNews tools:

- `search_tech_news`
- `get_latest_tech_news`
- `get_tech_news_article`

The deterministic runtime adapter currently chooses:

- `get_latest_tech_news` for today's-news questions.
- `search_tech_news` for general evidence search.

The Deep Agents path exposes the same tools to the model provider.

## Freshness

`technews-publisher` stores a daily GeekNews digest in the morning for the
previous day. If a user asks for today's news, the sample answers from the
latest collected issue and states that today's collection may not be available
yet.

## Replay

Replay is represented as `RunCreateRequest.replay`. Live replay re-executes the
tool. Frozen replay receives frozen tool results from the original trace and
reuses matching output instead of calling the live TechNews tool.
