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

## Notes

- MVP tools are read-only.
- Fixture data is synthetic.
- Deep Agents integration is exposed through `build_deep_agent`; deterministic
  fixture tests stay independent from live LLM credentials.
- The future real-data adapter should target `technews-publisher` read APIs:
  `/api/issues`, `/api/issues/latest`, `/api/issues/search`, and `/api/issues/{slug}`.

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
