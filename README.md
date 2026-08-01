# Traceable Deep Agents Sample

Small Deep Agents sample for a traceable Tech Radar analyst.

The first milestone runs locally against fixture data so agent behavior, source
handling, and trace output can be tested without depending on a running service.
The real knowledge source is the existing `technews-publisher` project, which is
the Personal Tech Radar service in this workspace.

The sample can also run as an external Agent Server adapter behind
`traceable-agent-runtime`. In that mode the runtime owns the public run/trace
API and imports the sample trace into its own trace store.

Korean documentation is available at [README.ko.md](README.ko.md).
Architecture documentation is available at [docs/architecture.md](docs/architecture.md)
and [docs/architecture.html](docs/architecture.html).
The target adaptive, multi-tenant agent design is documented in
[docs/adaptive-agent-architecture.md](docs/adaptive-agent-architecture.md).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
python -m traceable_deep_agents_sample.cli "최근 AI Agent 관련 뉴스는 뭐야?"
```

The CLI prints:

- answer
- sources
- run id
- trace path

## Test

```bash
pytest
```

## External Agent Server

Run the sample as a small Agent Server-compatible service:

```bash
tech-radar-agent-server
```

Then create a run and fetch its trace:

```bash
curl -fsS http://127.0.0.1:8776/v1/agents

curl -fsS -X POST http://127.0.0.1:8776/v1/runs \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"tech-radar","input":"최근 AI Agent 관련 뉴스는 뭐야?"}'

curl -fsS http://127.0.0.1:8776/v1/runs/<run_id>/trace
```

When `traceable-agent-runtime` has an agent manifest like
`agents/tech-radar.yaml`, clients should normally call the runtime on `8765`
instead of calling this sample directly:

```bash
curl -fsS -X POST http://127.0.0.1:8765/v1/runs \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"tech-radar","input":"최근 AI Agent 관련 뉴스는 뭐야?"}'
```

The runtime delegates execution to this service and then imports the returned
trace, so `GET /v1/runs/<run_id>/trace` on the runtime returns the same
evidence-backed execution timeline.

The external service advertises replay support through `GET /v1/agents`.
Runtime frozen replay sends `replay.tool_mode="frozen"` and portable frozen tool
results in the normal `POST /v1/runs` request. The sample then reuses matching
frozen tool output instead of calling the live TechNews tool.

## Notes

- MVP tools are read-only.
- Fixture data is synthetic.
- Deep Agents integration is exposed through `build_deep_agent`; deterministic
  fixture tests stay independent from live LLM credentials.
- The runtime-compatible adapter now runs a deterministic `ComplexityRouter`.
  It records `complexity_classified`, `route_selected`, and `light_plan_created`
  before tool execution. Deep candidates currently fall back to the light path
  until the Deep Agents runtime path is wired.
- The real TechNews adapter targets `technews-publisher` read APIs:
  `/api/issues/latest`, `/api/issues/search`, and `/api/issues/{slug}`.
- TechNews stores a daily GeekNews digest in the morning for the previous day.
  When a user asks for today's news, the runtime-compatible adapter uses the
  latest issue and says that today's collection may not be available yet.

## Deep Agents LLM Provider

By default, the sample uses the same provider vocabulary as
`traceable-agent-runtime`:

```bash
export TECH_RADAR_LLM_PROVIDER=openai
export TECH_RADAR_LLM_MODEL=gpt-5.5
export OPENAI_API_KEY=...
```

Gemini is available with the runtime-compatible Gemini environment variables:

```bash
export TECH_RADAR_LLM_PROVIDER=gemini
export GEMINI_MODEL=gemini-2.5-flash
export GEMINI_API_KEY=...
```

`TECH_RADAR_MODEL` is still supported as a direct Deep Agents/LangChain model
string override. Leave it empty when using provider-specific settings.

## Real TechNews API Adapter

Configure the real Personal Tech Radar service with:

```bash
export TECH_RADAR_KNOWLEDGE_BACKEND=technews
export TECHNEWS_API_BASE_URL=http://127.0.0.1:8010
```

If the API requires auth, set one of:

```bash
export TECHNEWS_AUTH_TOKEN=...
export TECHNEWS_SESSION_COOKIE='idounai_session=...'
```

Only read endpoints are modeled as agent tools.

Modeled tools:

- `search_tech_news`: search published TechNews issues.
- `get_latest_tech_news`: fetch the latest published daily issue.
- `get_tech_news_article`: fetch one issue by slug.

For the local service wrapper, keep any generated session cookie or API token
outside git. The sample accepts either a bearer token or a full
`idounai_session=...` cookie string and passes it only to the TechNews backend.

## Runtime Compatibility

`TraceableRuntimeAdapter` emits `traceable-agent-runtime`-shaped run, trace, and
agent capability responses locally. See
[docs/runtime-interface.md](docs/runtime-interface.md).
For a Korean explanation of the full idounAIChat -> runtime -> sample ->
TechNews mechanism, see
[docs/agent-mechanism.ko.md](docs/agent-mechanism.ko.md).
Korean runtime contract documentation is available at
[docs/runtime-interface.ko.md](docs/runtime-interface.ko.md).

Validate against a local sibling checkout of `traceable-agent-runtime`:

```bash
python scripts/check_runtime_contract.py
```
