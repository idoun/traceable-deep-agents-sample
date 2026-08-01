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

## Notes

- MVP tools are read-only.
- Fixture data is synthetic.
- Deep Agents integration is exposed through `build_deep_agent`; deterministic
  fixture tests stay independent from live LLM credentials.
- The real TechNews adapter targets `technews-publisher` read APIs:
  `/api/issues/latest`, `/api/issues/search`, and `/api/issues/{slug}`.

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

For the local service wrapper, keep any generated session cookie or API token
outside git. The sample accepts either a bearer token or a full
`idounai_session=...` cookie string and passes it only to the TechNews backend.

## Runtime Compatibility

`TraceableRuntimeAdapter` emits `traceable-agent-runtime`-shaped run and trace
responses locally. See [docs/runtime-interface.md](docs/runtime-interface.md).
For a Korean explanation of the full idounAIChat -> runtime -> sample ->
TechNews mechanism, see
[docs/agent-mechanism.ko.md](docs/agent-mechanism.ko.md).

Validate against a local sibling checkout of `traceable-agent-runtime`:

```bash
python scripts/check_runtime_contract.py
```
