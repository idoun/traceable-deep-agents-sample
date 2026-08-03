# Module Reference

This document is a code-facing reference for the important modules in
`traceable-deep-agents-sample`.

It intentionally uses a stable module card shape:

- Role
- Inputs
- Outputs
- Dependencies
- Side effects and state
- Implementation status
- Future direction

The format follows the documentation split recommended by Diataxis: this page is
mostly reference material, with short explanations only where a boundary can be
misread. Architecturally significant decisions should still be captured in ADRs
when they become hard to reverse.

## Execution Modes

The sample supports two execution modes.

Standalone mode:

```text
client -> traceable-deep-agents-sample :8776
```

This mode is useful for local development, contract checks, and smoke tests. The
sample owns the HTTP boundary, execution, and short-lived in-process trace lookup.

Runtime-adapter mode:

```text
idounAIChat -> traceable-agent-runtime :8765
            -> traceable-deep-agents-sample :8776
            -> TechNews API
```

This is the current idounAIChat and AgentOps path. The sample executes the Tech
Radar behavior, but `traceable-agent-runtime` owns the public Agent Server API,
durable trace store, replay, diff, eval, and Workbench integration.

## Module Summary

| Module | Primary responsibility | Current implementation status |
| --- | --- | --- |
| `api.py` | FastAPI boundary for the runtime-compatible external service | Functional, intentionally thin |
| `server.py` | Uvicorn entrypoint for the external service | Functional |
| `runtime_contract.py` | Pydantic request/response models compatible with `traceable-agent-runtime` | Functional, locally mirrored contract |
| `runtime_adapter.py` | Main runtime-compatible orchestration path | Functional MVP, still synchronous and in-memory for sample traces |
| `complexity_router.py` | Deterministic light/deep route classification | Functional bootstrap rules |
| `context_mesh.py` | Tenant/workspace/user/session context envelope | Functional lightweight snapshot |
| `skill_registry.py` | Portable `SKILL.md` discovery and selection | Functional static registry |
| `tool_binding.py` | Tenant-scoped read-only TechNews tool binding | Functional static resolver |
| `deep_agent.py` | Deep Agents graph factory and provider/model resolution | Functional for configured providers |
| `deep_path.py` | Deep route runner, callback trace bridge, final answer normalization | Functional MVP with synthesis retry |
| `tools.py` | Tool facade over interchangeable knowledge stores | Functional |
| `knowledge/fixture_store.py` | Local JSONL article store for deterministic tests | Functional |
| `knowledge/technews_api_store.py` | Adapter for real `technews-publisher` read APIs | Functional read adapter |
| `agent.py` | Older standalone fixture agent and JSONL trace path | Functional legacy/dev path |
| `tracing/*` | JSONL trace event model and sink for standalone mode | Functional legacy/dev path |
| `config.py` | Environment-backed settings | Functional |
| `models.py` | Domain and CLI response models | Functional |
| `prompts.py` | Deep Agents system prompt | Functional |
| `cli.py` | Command-line entrypoint for the fixture agent | Functional |

## `api.py`

Role:

- Exposes the sample as a small FastAPI service compatible with the external
  Agent Server shape used by `traceable-agent-runtime`.
- Keeps HTTP concerns separate from the actual runtime orchestration.

Inputs:

- `RuntimeRunCreateRequest` through `POST /v1/runs`.
- Run id path parameter through `GET /v1/runs/{run_id}/trace`.
- Optional `Settings` object when constructing an app in tests.

Outputs:

- `RuntimeAgentListResponse` from `GET /v1/agents`.
- `RuntimeRunResponse` from `POST /v1/runs`.
- `RuntimeTraceResponse` from `GET /v1/runs/{run_id}/trace`.
- `404 Trace not found` when the in-process trace map has no run.

Dependencies:

- `Settings`
- `TraceableRuntimeAdapter`
- Runtime contract Pydantic models
- FastAPI

Side effects and state:

- Creates one `TraceableRuntimeAdapter` per app instance.
- Trace lookup depends on that adapter instance's in-memory state.

Implementation status:

- Complete enough for local service smoke tests and runtime external adapter
  integration.
- No auth, multi-process trace sharing, or persistent sample-side trace DB.

Future direction:

- Keep this file thin.
- If trace handoff changes to inline trace response or OTel export, reflect only
  the HTTP contract here and keep transformation logic in adapter/exporter
  modules.

## `server.py`

Role:

- Provides the console-script entrypoint that runs the FastAPI app with Uvicorn.

Inputs:

- Environment-backed `Settings`, especially `TECH_RADAR_SERVER_HOST` and
  `TECH_RADAR_SERVER_PORT`.

Outputs:

- A running HTTP server.

Dependencies:

- `uvicorn`
- `Settings`
- `traceable_deep_agents_sample.api:app`

Side effects and state:

- Binds the configured host/port.

Implementation status:

- Minimal and functional.

Future direction:

- Keep minimal.
- Production process management should stay outside this module, for example in
  systemd or container configuration.

## `runtime_contract.py`

Role:

- Defines the local Pydantic models that mirror the runtime-compatible
  request/response/trace contract.

Inputs:

- JSON request payloads from clients or `traceable-agent-runtime`.
- Frozen replay payloads through `RuntimeReplayContext`.

Outputs:

- Validated run, trace, step, capability, and agent list models.

Dependencies:

- Pydantic

Side effects and state:

- None.

Implementation status:

- Functional local mirror of the runtime contract.
- Contract drift is controlled by `scripts/check_runtime_contract.py`.

Future direction:

- Consider sharing a small contract package if the runtime and sample continue
  to evolve together.
- If OTel export is added, keep these models as the Agent Server contract and add
  a separate `StepRecord -> span/event` mapper.

## `runtime_adapter.py`

Role:

- Main orchestration module for runtime-compatible runs.
- Builds context, classifies complexity, selects skills, resolves tool bindings,
  executes light or deep path, records trace steps, handles frozen tool replay,
  and stores the trace for immediate lookup.

Inputs:

- `RuntimeRunCreateRequest`
- Environment-backed `Settings`
- Optional injected `DeepPathRunner` in tests
- Frozen tool results when replaying with `tool_mode="frozen"`

Outputs:

- `RuntimeRunResponse`
- `RuntimeTraceResponse` from `get_trace`
- Runtime step records such as `context_mesh_built`, `route_selected`,
  `deep_model_call_completed`, `tool_call_completed`, and `final_answer`

Dependencies:

- `ComplexityRouter`
- `build_context_mesh`
- `SkillRegistry`
- `ToolBindingResolver`
- `DeepPathRunner`
- `TechRadarTools`
- `FixtureArticleStore`
- `TechNewsApiStore`
- Runtime contract models

Side effects and state:

- Stores completed traces in `self._traces`, an in-memory dictionary.
- Calls the real TechNews API when `TECH_RADAR_KNOWLEDGE_BACKEND=technews` and
  the selected or replayed path needs live tool execution.
- Redacts token/cookie/secret-shaped values before recording trace input/output.

Implementation status:

- Functional MVP for adaptive routing, tool replay, runtime trace import, and
  Deep Agents fallback.
- Trace timing is coarse; generated step latency is currently `0`.
- Sample-side trace state is not durable and is not shared across processes.
- Runtime mode still uses synchronous handoff: runtime calls sample `POST
  /v1/runs`, then follows `trace_url` with `GET /trace`.

Future direction:

- Split trace recording/export behind an interface.
- Add an OTel-compatible mapper for `RuntimeStepRecord`.
- Consider returning inline trace from `POST /v1/runs` to remove the second
  runtime-to-sample HTTP call.
- Keep control-plane semantics such as route, replay, and policy separate from
  observability transport.

## `complexity_router.py`

Role:

- Provides a cheap, deterministic first-pass classifier for light vs. deep
  execution.

Inputs:

- User input text.

Outputs:

- `ComplexityDecision` with `route`, `score`, and `reasons`.

Dependencies:

- Python dataclasses and literal types only.

Side effects and state:

- None.

Implementation status:

- Functional bootstrap rules.
- Handles simple lookup, synthesis/comparison/risk, evidence/report, and
  semantic exclusion/filter markers.

Future direction:

- Move marker weights into tenant or agent policy when the route matrix grows.
- Add structured query planning for date/filter/exclusion semantics instead of
  relying only on deep routing.
- Consider an optional model-based classifier only after enough test cases exist.

## `context_mesh.py`

Role:

- Builds a portable context envelope from tenant, workspace, user, and session
  identity.

Inputs:

- `RuntimeRunCreateRequest`

Outputs:

- Context dictionary with tenant identity, optional workspace/user/session, and
  memory namespace hints.

Dependencies:

- Runtime contract request model.

Side effects and state:

- None.

Implementation status:

- Functional lightweight ContextMesh snapshot.
- Defaults missing tenant to `tenant:default`.

Future direction:

- Attach real policy, memory, and skill/tool allowlists when those systems move
  beyond static sample data.
- Keep this module pure so it can be shared or tested easily.

## `skill_registry.py`

Role:

- Discovers local portable skills and selects the skills relevant to a run.

Inputs:

- User input
- `ComplexityDecision`
- Skill files under `traceable_deep_agents_sample/skills/*/SKILL.md`

Outputs:

- `SkillRef` entries with id, name, version, relative path, content hash, and
  selection reason.

Dependencies:

- `ComplexityDecision`
- Local filesystem
- SHA-256 hashing

Side effects and state:

- Reads skill files from disk.

Implementation status:

- Functional static registry.
- Current skills:
  - `daily-news-freshness`
  - `tech-trend-briefing`

Future direction:

- Add tenant-aware skill allowlists.
- Validate skill metadata more formally if skills become an extension surface.
- Avoid making the registry a general plugin system until there are more real
  skills.

## `tool_binding.py`

Role:

- Resolves model-visible TechNews tools into tenant-scoped read-only bindings.

Inputs:

- Tenant id
- Tool name

Outputs:

- `ToolBinding` with binding id, allowed scopes, and hashed credential reference.

Dependencies:

- Static `ToolDefinition` registry
- SHA-256 hashing

Side effects and state:

- None.
- Does not read real credentials; it records only a redacted reference shape.

Implementation status:

- Functional static resolver for three read-only tools.

Future direction:

- Resolve actual binding policy from runtime or tenant configuration.
- Enforce scopes closer to the tool invocation boundary if write tools are ever
  introduced.

## `deep_agent.py`

Role:

- Builds the Deep Agents graph with read-only Tech Radar tools and resolves the
  configured model provider.

Inputs:

- `Settings`
- Optional LangChain chat model or model string override

Outputs:

- Deep Agents runnable graph.

Dependencies:

- `deepagents`
- LangChain tool decorator
- Optional `langchain_google_genai` for Gemini
- `TechRadarTools`
- `FixtureArticleStore`
- `TechNewsApiStore`
- `SYSTEM_PROMPT`

Side effects and state:

- Registers a read-only harness profile for model-string based Deep Agents
  execution.
- Builds tool functions bound to the selected knowledge backend.

Implementation status:

- Functional for OpenAI-style model strings and Gemini chat model construction.
- Read-only tool restriction is explicit through excluded harness tools.

Future direction:

- Keep provider selection small and runtime-compatible.
- Add clearer provider capability checks only when new providers are needed.
- Consider sharing tool metadata with runtime/AgentOps so UI labels are not
  inferred from traces alone.

## `deep_path.py`

Role:

- Runs the Deep Agents path behind the runtime adapter boundary.
- Converts LangChain callbacks into runtime trace events.
- Normalizes Deep Agents responses into user-facing answer text.

Inputs:

- `RuntimeRunCreateRequest`
- ContextMesh dictionary
- Selected skills
- Tool binding
- Injected agent factory in tests

Outputs:

- `DeepPathResult` with answer text, raw output summary, and trace event list.

Dependencies:

- `build_deep_agent`
- LangChain callback base class
- Runtime request model
- `SkillRef`
- `ToolBinding`

Side effects and state:

- Invokes live LLM/tool graph when enabled by the adapter.
- Reuses one callback collector across the initial call and synthesis retry so
  both attempts are visible in trace events.

Implementation status:

- Functional MVP.
- Handles string, mapping, message-list, and LangChain content-list outputs.
- If a model stops after a tool result, it retries once with a final synthesis
  instruction.
- If synthesis still fails, it falls back to a readable tool-result summary.

Future direction:

- Record richer token/cost/model metadata when provider responses expose it
  consistently.
- Map callback events to OTel spans/events.
- Keep raw provider objects out of user-facing answers and traces.

## `tools.py`

Role:

- Provides the stable tool facade used by deterministic and Deep Agents paths.

Inputs:

- Store object with `search`, `latest`, and `get_article` methods.
- Query, slug, limit, optional tags, optional minimum score.

Outputs:

- JSON-serializable dictionaries for tool calls.

Dependencies:

- Knowledge store contract by convention.

Side effects and state:

- Delegates side effects to the underlying store.

Implementation status:

- Functional facade for three read-only tools.

Future direction:

- Introduce a formal store protocol if additional stores are added.
- Preserve this module as the tool output normalization boundary.

## `knowledge/fixture_store.py`

Role:

- Provides deterministic local article data for CLI, tests, and offline smoke
  runs.

Inputs:

- JSONL data file path
- Search query, limit, optional tags, optional minimum score

Outputs:

- `Article` and `SearchResult` models.

Dependencies:

- Local JSONL fixture data
- `Article`
- `SearchResult`

Side effects and state:

- Lazily reads and caches fixture articles in memory.

Implementation status:

- Functional deterministic store.
- Search is simple term matching with local scoring.

Future direction:

- Keep deliberately simple; do not evolve into a production search backend.
- Add fixtures only when they protect route/tool behavior in tests.

## `knowledge/technews_api_store.py`

Role:

- Adapts the real `technews-publisher` read APIs to the same store shape as the
  fixture store.

Inputs:

- Base URL
- Timeout
- Optional bearer token or session cookie
- Search query, slug, tags, score filters

Outputs:

- `Article` and `SearchResult` models.

Dependencies:

- `httpx`
- `Article`
- `ArticleScore`
- `SearchResult`
- `technews-publisher` read endpoints:
  - `/api/issues/latest`
  - `/api/issues/search`
  - `/api/issues/{slug}`

Side effects and state:

- Makes outbound HTTP GET requests.
- Sends auth headers/cookies only to the configured TechNews base URL.

Implementation status:

- Functional read adapter.
- `latest` maps a single latest-issue API response into a list for store
  compatibility.
- Filtering by tags and score is local after API response normalization.

Future direction:

- Keep write APIs out of this adapter.
- Add structured query parameters when `technews-publisher` supports them.
- Surface request latency/error categories into trace or OTel attributes.

## `agent.py`

Role:

- Older standalone fixture agent used by the CLI and early tests.

Inputs:

- User question
- Optional `Settings`
- Optional thread id

Outputs:

- `AgentResponse` with answer, sources, run id, thread id, and JSONL trace path.

Dependencies:

- `FixtureArticleStore`
- `TechRadarTools`
- `JsonlTraceSink`
- Domain models

Side effects and state:

- Writes JSONL trace files under `Settings.trace_dir`.
- Reads fixture data.

Implementation status:

- Functional development path.
- Separate from the runtime-compatible trace contract.

Future direction:

- Keep as a simple local smoke path or retire once runtime-compatible CLI
  coverage is enough.
- Do not add runtime replay or Deep Agents complexity here; that belongs in
  `runtime_adapter.py`.

## `tracing/events.py` and `tracing/jsonl_sink.py`

Role:

- Provide the local JSONL trace event model and file sink for standalone fixture
  mode.

Inputs:

- `TraceEvent`
- Trace directory
- Run id

Outputs:

- JSONL trace file.

Dependencies:

- Pydantic
- Local filesystem

Side effects and state:

- Creates the trace directory if needed.
- Appends trace events to a local file.

Implementation status:

- Functional for local CLI traces.
- Not used as the runtime/AgentOps trace store.

Future direction:

- Keep or replace with the same OTel exporter used by runtime-compatible traces.
- Avoid adding a second durable trace model.

## `config.py`

Role:

- Centralizes environment-backed settings for local, runtime-compatible, and
  Deep Agents execution.

Inputs:

- `.env`
- `TECH_RADAR_*`
- Selected compatibility aliases such as `TECHNEWS_API_BASE_URL`,
  `OPENAI_API_KEY`, `GEMINI_API_KEY`, and `GOOGLE_API_KEY`

Outputs:

- `Settings`

Dependencies:

- `pydantic-settings`

Side effects and state:

- Reads environment and optional `.env`.

Implementation status:

- Functional.
- Supports fixture vs. real TechNews backend, execution mode, Deep Agents flag,
  and provider-specific model settings.

Future direction:

- Keep sample-specific private env values separate from runtime and application
  env files.
- Add new settings only when a concrete runtime or deployment path needs them.

## `models.py`

Role:

- Defines domain models used by article stores, tool outputs, and the standalone
  fixture agent.

Inputs:

- Parsed JSON data from fixtures or TechNews API responses.

Outputs:

- `ArticleScore`
- `Article`
- `SearchResult`
- `Source`
- `AgentResponse`

Dependencies:

- Pydantic

Side effects and state:

- None.

Implementation status:

- Functional.
- Some models are mainly for standalone mode (`Source`, `AgentResponse`) while
  others are shared by stores and tools.

Future direction:

- Keep store/domain models separate from runtime contract models.
- Add fields only when they are returned by TechNews and used by tests or UI.

## `prompts.py`

Role:

- Holds the Deep Agents system prompt.

Inputs:

- None at runtime, aside from import.

Outputs:

- `SYSTEM_PROMPT`

Dependencies:

- None.

Side effects and state:

- None.

Implementation status:

- Functional compact prompt.
- Encodes Korean answer default, evidence-first behavior, untrusted article text,
  freshness note, and no-evidence fallback.

Future direction:

- Keep prompt changes coupled to route/test-plan updates.
- If prompt versioning becomes important, move version metadata into trace.

## `cli.py`

Role:

- Provides a command-line smoke path for the fixture agent.

Inputs:

- Positional question string.

Outputs:

- Answer, sources, run id, and trace path printed to stdout.

Dependencies:

- `run_fixture_agent`
- `argparse`

Side effects and state:

- Writes JSONL trace through the fixture agent.

Implementation status:

- Functional local utility.

Future direction:

- Add a runtime-compatible CLI mode only if it becomes useful for operator
  smoke tests.

## Skill Files

Role:

- Portable instruction bundles loaded by `SkillRegistry`.

Inputs:

- User input and `ComplexityDecision` indirectly through registry selection.

Outputs:

- Skill metadata and instruction text hash recorded into trace.

Dependencies:

- Local `SKILL.md` files.

Side effects and state:

- None beyond file reads.

Implementation status:

- Functional static skills:
  - `daily-news-freshness`
  - `tech-trend-briefing`

Future direction:

- Add only behaviorally meaningful skills.
- Keep skill files copyable and independent from private runtime/application
  environment values.

## Current Cross-Cutting Gaps

- Runtime trace handoff is synchronous and uses an extra `GET /trace` call.
- Sample-side runtime traces are in-memory only.
- Trace events are runtime-specific records, not yet OTel spans/events.
- Tool replay is implemented, but model replay is still a separate future
  concept.
- Structured date/filter/exclusion planning is not implemented; semantic filter
  requests are routed deep as a safer interim behavior.
- Langfuse/LangSmith migration would still need metadata mapping for model,
  prompt, token, cost, tool call, route, and replay semantics.

## Documentation Sources

- Diataxis documentation framework: https://diataxis.fr/
- Architecture Decision Records: https://github.com/architecture-decision-record/architecture-decision-record
- AWS ADR process guidance: https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html
