# Adaptive Agent Architecture

This document describes the target architecture for turning the current Tech
Radar sample into a portfolio-ready adaptive agent. The goal is not to send
every request into a large autonomous agent. The goal is to route each request
through the cheapest useful path while keeping memory, skills, tools, and
traces visible.

## Positioning

The sample should become a traceable adaptive agent:

- simple requests use a light deterministic path;
- complex requests use Deep Agents with model reasoning;
- skills provide reusable procedural knowledge;
- tools remain tenant-scoped and read-only unless explicitly expanded;
- memory is retrieved through scoped context, not an ever-growing prompt;
- every routing, skill, memory, and tool decision is recorded in trace steps.

## Two Execution Paths

```text
Client
  -> traceable-agent-runtime
  -> tech-radar external adapter
  -> Request Intake
  -> ContextMesh
  -> Complexity Router
       -> Light Path
       -> Deep Path
  -> Trace Export
  -> runtime trace import
```

### Light Path

The light path handles requests that can be answered with one bounded tool plan.

Examples:

- latest TechNews issue;
- today's AI news, using the latest available daily issue;
- search by one topic;
- article detail by slug;
- short summaries over one issue.

The first implementation should use deterministic rules and intent scoring.
Semantic cache can be added next. A small classifier model should be reserved
for ambiguous requests instead of being called for every run.

### Deterministic Complexity Routing Rules

`ComplexityRouter` currently uses three marker groups as a transparent bootstrap
classifier. They are intentionally simple because the first goal is traceability,
not perfect intent detection.

- `_SYNTHESIS_MARKERS`: raises the score when the request asks for judgment,
  synthesis, comparison, strategy, risk, or forecasting. Examples include
  `compare`, `risk`, `forecast`, `비교`, `전망`, and `리스크`.
- `_MULTI_STEP_MARKERS`: raises the score when the request asks for evidence
  expansion, details, sources, research, or report-style output. Examples
  include `evidence`, `detail`, `report`, `근거`, `출처`, and `보고서`.
- `_SIMPLE_MARKERS`: lowers the score only when no synthesis or multi-step
  markers are present. These markers identify requests that can usually be
  answered with one bounded news lookup, such as `today`, `latest`, `search`,
  `오늘`, `최신`, and `뉴스`.

The marker lists are not intended to be the permanent control plane. They are
the deterministic v1 policy for the sample. The planned migration path is:

1. keep the current marker rules as a cheap, testable bootstrap;
2. move tenant-specific routing terms into tenant policy/config instead of code;
3. add semantic cache for repeated or near-duplicate requests;
4. use a small classifier model only for ambiguous requests;
5. keep the final routing decision traceable through `complexity_classified` and
   `route_selected` regardless of which classifier implementation is used.

Recommended trace steps:

```text
request_normalized
context_mesh_built
complexity_classified
route_selected
light_plan_created
tool_binding_resolved
tool_call_started
tool_call_completed
light_answer_composed
```

### Deep Path

The deep path handles requests that require synthesis, comparison, planning, or
multi-step reasoning.

Examples:

- compare several trends across multiple days;
- explain why a technology matters;
- produce a portfolio-style briefing;
- answer a follow-up that depends on previous evidence;
- use a tenant skill to follow a domain-specific workflow.

The Deep Agents path should receive a scoped set of skills, tools, and memory
references from `ContextMesh`. It should not discover global tenant data or raw
credentials on its own.

Recommended trace steps:

```text
deep_agent_started
skill_catalog_filtered
skill_selection_started
skill_loaded
deep_plan_created
model_call_started
model_call_completed
tool_binding_resolved
tool_call_started
tool_call_completed
evidence_synthesized
deep_agent_completed
```

## ContextMesh

`ContextMesh` is the sample-side name for the component that assembles scoped
context for a run. The name fits the intended architecture because context is
not a single growing transcript. It is a mesh of scoped artifacts:

- tenant policy;
- user preferences;
- session summary;
- selected memories;
- selected skills;
- allowed tool bindings;
- request intent and complexity;
- evidence references.

The component should stay explicit and inspectable. A trace viewer should be
able to show which context sources were considered, selected, skipped, or
blocked.

Example:

```json
{
  "tenant_id": "org_123",
  "user_id": "user_456",
  "session_id": "session_789",
  "route": "deep",
  "memory_refs": ["tenant:org_123:user:user_456:preferences"],
  "skill_refs": ["daily-news-freshness@2026-08-01"],
  "tool_bindings": ["technews.read@tenant:org_123"]
}
```

## Tenant Context

Tenant context is organization-level or service-instance-level configuration.
It is different from user context.

Tenant context answers:

- which tools are enabled for this tenant?
- which skill versions are approved?
- which model providers are allowed?
- where is this tenant's TechNews backend?
- which credential references can tools use?
- what retention and redaction policy applies?
- which memory namespaces may be read or written?

B2C can use one tenant per user at first:

```text
tenant_id = user:{user_id}
```

Enterprise should use organization tenants:

```text
tenant_id = org:{org_id}
```

A user may belong to more than one tenant. The active tenant must therefore be
resolved before memory, skill, or tool lookup.

## Skill Strategy

Deep Agents supports Agent Skills-style `SKILL.md` files. The wider Agent Skills
pattern packages instructions, metadata, and optional resources in a skill
folder and uses progressive disclosure so the agent loads detailed instructions
only when needed.

Useful references:

- Deep Agents skills documentation:
  <https://docs.langchain.com/oss/python/deepagents/skills>
- Agent Skills overview:
  <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview>
- Agent Skills specification:
  <https://agentskills.io/specification>
- MCP prompts and resources:
  <https://modelcontextprotocol.io/specification/2026-07-28/server/prompts>
  and <https://modelcontextprotocol.io/specification/2026-07-28/server/resources>

The sample should follow the `SKILL.md` folder pattern for portability. Runtime
metadata should add tenant controls around it:

```text
skill_id
version
scope: global | tenant | user
hash
enabled_for_tenant
approved_by
```

Initial skills:

- `daily-news-freshness`: explain today's/news freshness based on yesterday's
  morning TechNews collection;
- `ai-news-filter`: define AI-related filtering criteria;
- `tech-trend-briefing`: synthesize several articles into a short briefing;
- `deep-research-report`: require plan, evidence expansion, synthesis, and
  limitations.

### Skill Format Compatibility

The practical baseline is the Agent Skills folder format:

```text
skill-name/
  SKILL.md
  scripts/
  templates/
  resources/
```

`SKILL.md` should contain metadata plus Markdown instructions. Deep Agents uses
this pattern directly enough that the sample should not invent a new primary
skill format. Instead, the sample should add a thin registry layer around
portable skills.

Comparison:

- Agent Skills: portable package of instructions, metadata, scripts, templates,
  and resources.
- Deep Agents skills: uses `SKILL.md` skills and loads them into the Deep Agents
  harness for task-specific behavior.
- MCP prompts/resources: useful for exposing reusable prompt templates and
  context resources over a protocol, but not a replacement for local skill
  packages.
- Runtime registry: the tenant-aware control plane that decides which portable
  skills are enabled, approved, hashed, and visible for a run.

Recommended rule: keep skill contents portable, keep tenant policy outside the
skill folder.

## Tool Gateway Strategy

Tool gateway remains an important extension point, but the first version should
stay small.

Minimum useful design:

- separate tool definition from tenant tool binding;
- resolve credentials through `credential_ref`, never through model-visible
  text;
- include allowed scopes on each binding;
- record `tool_binding_resolved` before `tool_call_started`;
- redact credential references in trace output.

Example:

```json
{
  "tool": "search_tech_news",
  "binding_id": "technews.read",
  "tenant_id": "org_123",
  "credential_ref": "[REDACTED]",
  "allowed_scopes": ["read:issues"]
}
```

## Memory Strategy

Memory should be scoped by tenant, user, workspace, and session. Do not use one
global memory namespace.

Recommended namespaces:

```text
tenant/{tenant_id}/user/{user_id}/profile
tenant/{tenant_id}/user/{user_id}/preferences
tenant/{tenant_id}/session/{session_id}/summary
tenant/{tenant_id}/workspace/{workspace_id}/knowledge
tenant/{tenant_id}/tool/{tool_id}/cache
tenant/{tenant_id}/skill/{skill_id}/state
```

Light and deep paths should share the same memory interface. The difference is
how much context they retrieve and how much reasoning they do with it.

## Implementation Phases

1. Add contract fields: `tenant_id`, `workspace_id`, `user_id`, and a
   `ContextMesh` trace snapshot. Keep them optional so existing local runs keep
   working.
2. Add `ContextMesh` assembly in the sample adapter and trace
   `context_mesh_built`.
3. Add deterministic `ComplexityRouter` and route trace steps.
4. Add a read-only skill registry using portable `SKILL.md` folders.
5. Add tenant-aware tool binding around the existing TechNews tools.
6. Connect Deep Agents as the deep path using only scoped skills, tools, and
   memory from `ContextMesh`.
7. Add cross-tenant leakage tests for memory, skill, tool binding, replay
   identity, and trace visibility.

## Roadmap / Open Decisions

Keep this section as the short working checklist for the adaptive-agent design.
Do not duplicate it into a separate TODO file until the roadmap becomes too
large for this architecture document.

- Routing markers: keep `_SYNTHESIS_MARKERS`, `_SIMPLE_MARKERS`, and
  `_MULTI_STEP_MARKERS` as deterministic v1 bootstrap rules only.
- Routing policy: move tenant-specific routing terms out of code and into
  tenant policy/config when tenant config storage exists.
- Semantic cache: add only after the trace contract proves stable, so repeated
  questions can reuse route/tool decisions without model calls.
- Classifier model: reserve a small classifier for ambiguous requests. Do not
  call it for every request unless the deterministic/semantic layers are not
  enough.
- Skill registry: keep portable `SKILL.md` folders, but move tenant enablement,
  approval, version, and hash policy into the runtime registry.
- Tool Gateway: add tenant-aware tool binding before wiring the real Deep Agents
  path, so both light and deep execution use the same scoped tool contract.
- Deep path: connect Deep Agents only after route, skill, memory, and tool
  boundaries are visible in trace.
- Trace contract: keep `context_mesh_built`, `complexity_classified`,
  `route_selected`, `skill_catalog_filtered`, `skill_loaded`, and
  `tool_binding_resolved` stable even if the internal implementation changes.

## Current Implementation Status

The initial contract phase is implemented:

- `RuntimeRunCreateRequest` accepts optional `tenant_id`, `workspace_id`, and
  `user_id`.
- `RuntimeRunResponse` returns the resolved identity fields.
- missing `tenant_id` resolves to the explicit `tenant:default` boundary.
- `TraceableRuntimeAdapter` records `context_mesh_built` before policy/tool
  execution.
- focused tests cover default tenant resolution and tenant/user/session
  propagation into the ContextMesh trace step.

The first adaptive routing phase is also implemented:

- `ComplexityRouter` classifies requests with deterministic rules and a visible
  score.
- `TraceableRuntimeAdapter` records `complexity_classified`, `route_selected`,
  and `light_plan_created`.
- simple news/search requests stay on the light path.
- synthesis, comparison, strategy, risk, or report-style requests are marked as
  deep candidates.
- portable `SKILL.md` folders are loaded through a read-only `SkillRegistry`.
- `skill_catalog_filtered` is recorded for every run, and `skill_loaded` is
  recorded when `daily-news-freshness` or `tech-trend-briefing` applies.
- TechNews tools resolve through a tenant-aware Tool Binding layer.
- `tool_binding_resolved` records the binding id, allowed scopes, and a hashed
  credential reference before policy and tool execution.
- focused cross-tenant leakage tests verify that ContextMesh memory namespaces,
  skill filtering traces, Tool Binding traces, runtime snapshots, and external
  replay payloads stay inside the resolved tenant boundary.
- until the Deep Agents runtime path is wired, deep candidates explicitly fall
  back to the light path with a traceable fallback reason.

The next implementation step is connecting the real Deep Agents path behind the
existing route and feature-flag controls. It should use the same scoped skill,
memory, and tool contract as the light path.
