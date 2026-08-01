# Traceable Deep Agents Sample

Small Deep Agents sample for a traceable Tech Radar analyst.

The first milestone runs locally against fixture data so agent behavior, source
handling, and trace output can be tested without depending on a running service.
The real knowledge source is the existing `technews-publisher` project, which is
the Personal Tech Radar service in this workspace.

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

## Notes

- MVP tools are read-only.
- Fixture data is synthetic.
- Deep Agents integration is exposed through `build_deep_agent`; deterministic
  fixture tests stay independent from live LLM credentials.
- The future real-data adapter should target `technews-publisher` read APIs:
  `/api/issues`, `/api/issues/latest`, `/api/issues/search`, and `/api/issues/{slug}`.

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
export TECHNEWS_SESSION_COOKIE=...
```

Only read endpoints are modeled as agent tools.

## Runtime Compatibility

`TraceableRuntimeAdapter` emits `traceable-agent-runtime`-shaped run and trace
responses locally. See [docs/runtime-interface.md](docs/runtime-interface.md).

Validate against a local sibling checkout of `traceable-agent-runtime`:

```bash
python scripts/check_runtime_contract.py
```
