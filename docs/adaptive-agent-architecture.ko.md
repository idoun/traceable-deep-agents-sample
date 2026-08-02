# Adaptive Agent Architecture

이 문서는 현재 Tech Radar sample을 portfolio에 잘 드러나는 adaptive agent로
발전시키기 위한 target architecture를 설명합니다.

핵심은 모든 요청을 큰 자율 agent에 넣지 않는 것입니다. 간단한 요청은 가장 가벼운
경로로 처리하고, 복잡한 요청만 Deep Agents의 추론, skill, tool, memory를 사용하게
합니다. 그리고 이 선택 과정이 trace에 드러나야 합니다.

## Positioning

이 sample은 다음 성격을 가진 traceable adaptive agent를 지향합니다.

- 간단한 요청은 deterministic light path에서 처리합니다.
- 복잡한 요청은 LLM reasoning을 쓰는 Deep Agents path로 보냅니다.
- Skill은 재사용 가능한 절차 지식으로 관리합니다.
- Tool은 tenant scope 안에서만 bind하고 실행합니다.
- Memory는 계속 커지는 prompt가 아니라 scoped context로 조회합니다.
- Routing, skill, memory, tool 결정은 모두 trace step으로 남깁니다.

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

Light path는 한 번의 제한된 tool plan으로 답할 수 있는 요청을 처리합니다.

예:

- 최신 TechNews issue
- 오늘 AI 뉴스. 단, 실제로는 최신 수집된 daily issue 기준으로 안내
- 단일 주제 검색
- slug 기준 article detail
- 한 issue에 대한 짧은 요약

첫 구현은 deterministic rule과 intent score로 충분합니다. 그 다음 semantic cache를
붙이고, 작은 classifier model은 애매한 요청에만 선택적으로 쓰는 편이 좋습니다.

### Deterministic Complexity Routing Rules

현재 `ComplexityRouter`는 세 marker group을 사용하는 투명한 bootstrap
classifier입니다. 첫 목표는 완벽한 intent detection이 아니라, 왜 light/deep
후보가 되었는지 trace에 설명 가능하게 남기는 것입니다.

- `_SYNTHESIS_MARKERS`: 판단, 종합, 비교, 전략, 리스크, 전망이 필요한 요청이면
  score를 올립니다. 예: `compare`, `risk`, `forecast`, `비교`, `전망`, `리스크`
- `_MULTI_STEP_MARKERS`: 근거 확장, 상세 조회, 출처, research, report-style output이
  필요한 요청이면 score를 올립니다. 예: `evidence`, `detail`, `report`, `근거`,
  `출처`, `보고서`
- `_SIMPLE_MARKERS`: synthesis나 multi-step marker가 없을 때만 score를 낮춥니다.
  한 번의 bounded news lookup으로 처리할 수 있는 요청을 가리킵니다. 예: `today`,
  `latest`, `search`, `오늘`, `최신`, `뉴스`

이 marker list는 영구적인 control plane이 아닙니다. 지금은 sample을 위한
deterministic v1 policy입니다. 계획은 다음 순서입니다.

1. 현재 marker rule은 cheap하고 test 가능한 bootstrap으로 유지합니다.
2. tenant별 routing term은 code가 아니라 tenant policy/config로 이동합니다.
3. 반복 또는 유사 요청에는 semantic cache를 붙입니다.
4. 애매한 요청에만 작은 classifier model을 사용합니다.
5. classifier 구현이 바뀌어도 최종 routing decision은 `complexity_classified`와
   `route_selected` trace로 계속 설명 가능하게 유지합니다.

권장 trace step:

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

Deep path는 synthesis, comparison, planning, multi-step reasoning이 필요한 요청을
처리합니다.

예:

- 여러 날짜의 trend 비교
- 특정 기술이 왜 중요한지 설명
- portfolio 스타일 briefing 작성
- 이전 evidence를 이어받는 follow-up
- tenant skill을 따라야 하는 domain workflow

Deep Agents path는 `ContextMesh`가 넘겨준 scoped skill, tool, memory reference만
사용해야 합니다. Global tenant data나 raw credential을 직접 탐색하게 만들지
않습니다.

권장 trace step:

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

`ContextMesh`는 run에 필요한 context를 scope에 맞게 조립하는 sample-side component
이름입니다.

이 이름은 잘 어울립니다. Multi-tenant agent의 context는 하나의 긴 transcript가
아니라 여러 scoped artifact의 mesh이기 때문입니다.

- tenant policy
- user preference
- session summary
- selected memory
- selected skill
- allowed tool binding
- request intent and complexity
- evidence reference

단, 이름만 쓰면 의미가 흐릴 수 있으므로 문서와 trace에서는
`tenant-scoped context assembly mesh`라고 풀어 설명합니다.

예:

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

Tenant context는 조직 또는 서비스 instance 수준의 설정입니다. User context와
동일하지 않습니다.

Tenant context가 답하는 질문:

- 이 tenant에서 어떤 tool이 enabled인가?
- 어떤 skill version이 승인되어 있는가?
- 어떤 model provider를 사용할 수 있는가?
- 이 tenant의 TechNews backend는 어디인가?
- Tool이 어떤 credential reference를 사용할 수 있는가?
- Retention/redaction policy는 무엇인가?
- 어떤 memory namespace를 읽거나 쓸 수 있는가?

B2C에서는 처음에 user 하나를 tenant 하나로 취급해도 됩니다.

```text
tenant_id = user:{user_id}
```

Enterprise에서는 조직 단위 tenant가 자연스럽습니다.

```text
tenant_id = org:{org_id}
```

하나의 user가 여러 tenant에 속할 수 있으므로, memory/skill/tool 조회 전에 active
tenant를 먼저 확정해야 합니다.

## Tenant와 User 용어

`tenant`와 `user`는 동급이 아닙니다.

- `tenant`: 데이터, 설정, 과금, 권한, tool credential, skill catalog가 묶이는
  격리 단위
- `user`: tenant 안에서 행동하는 사람 또는 계정
- `workspace`: tenant 안에서 프로젝트나 팀별로 나누는 작업 공간
- `session`: user와 agent 사이의 대화 또는 작업 흐름
- `run`: 한 번의 agent 실행

B2C에서는 tenant와 user가 사실상 1:1일 수 있습니다. 그래도 contract에는 둘을
분리해 두는 편이 좋습니다. 그래야 나중에 family/team/company plan으로 확장할 때
memory와 tool credential 경계가 깨지지 않습니다.

## Skill Strategy

Deep Agents는 Agent Skills 계열의 `SKILL.md` 구조를 지원합니다. 넓은 의미의 Agent
Skills 패턴은 skill folder 안에 instruction, metadata, optional resource를 담고,
agent가 필요한 때에만 자세한 내용을 읽는 progressive disclosure 방식입니다.

참고:

- Deep Agents skills:
  <https://docs.langchain.com/oss/python/deepagents/skills>
- Agent Skills overview:
  <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview>
- Agent Skills specification:
  <https://agentskills.io/specification>
- MCP prompts/resources:
  <https://modelcontextprotocol.io/specification/2026-07-28/server/prompts>,
  <https://modelcontextprotocol.io/specification/2026-07-28/server/resources>

이 sample은 portable `SKILL.md` folder pattern을 따르는 것이 좋습니다. 그 위에
runtime metadata로 multi-tenant control을 추가합니다.

```text
skill_id
version
scope: global | tenant | user
hash
enabled_for_tenant
approved_by
```

초기 skill 후보:

- `daily-news-freshness`: 오늘/어제/최신 질문에서 TechNews 수집 기준을 적용
- `ai-news-filter`: AI 관련 기사 판별 기준
- `tech-trend-briefing`: 여러 기사를 짧은 briefing으로 종합
- `deep-research-report`: plan, evidence expansion, synthesis, limitation을 강제

### Skill Format Compatibility

실용적인 기준은 Agent Skills folder format입니다.

```text
skill-name/
  SKILL.md
  scripts/
  templates/
  resources/
```

`SKILL.md`는 metadata와 Markdown instruction을 담습니다. Deep Agents는 이 패턴을
직접 사용할 수 있는 방향이므로, sample이 별도 primary skill format을 새로 만들
필요는 없습니다. 대신 portable skill 위에 얇은 registry layer를 추가하는 게
좋습니다.

비교:

- Agent Skills: instruction, metadata, script, template, resource를 담는 portable
  package
- Deep Agents skills: `SKILL.md` skill을 Deep Agents harness 안에서 task-specific
  behavior로 로드
- MCP prompts/resources: protocol을 통해 reusable prompt template과 context
  resource를 노출하는 데 적합하지만, local skill package의 대체재는 아님
- Runtime registry: 어떤 portable skill이 특정 tenant/run에서 enabled, approved,
  hashed, visible인지 결정하는 tenant-aware control plane

권장 원칙은 skill content는 portable하게 유지하고, tenant policy는 skill folder
밖 runtime registry에서 관리하는 것입니다.

## Tool Gateway Strategy

Tool Gateway는 중요한 확장 지점입니다. 다만 첫 구현은 필요한 최소 범위로 시작하는
편이 좋습니다.

최소 설계:

- tool definition과 tenant tool binding을 분리합니다.
- credential은 model-visible text로 넘기지 않고 `credential_ref`로 resolve합니다.
- binding마다 allowed scope를 둡니다.
- `tool_call_started` 전에 `tool_binding_resolved`를 기록합니다.
- trace에서는 credential reference를 redacted/hash 형태로만 남깁니다.

예:

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

Memory는 tenant, user, workspace, session scope로 나눕니다. 하나의 global memory
namespace를 쓰지 않습니다.

권장 namespace:

```text
tenant/{tenant_id}/user/{user_id}/profile
tenant/{tenant_id}/user/{user_id}/preferences
tenant/{tenant_id}/session/{session_id}/summary
tenant/{tenant_id}/workspace/{workspace_id}/knowledge
tenant/{tenant_id}/tool/{tool_id}/cache
tenant/{tenant_id}/skill/{skill_id}/state
```

Light path와 deep path는 같은 memory interface를 공유해야 합니다. 차이는 얼마나
많이 가져오고, 얼마나 깊게 추론하는가입니다.

## Implementation Phases

1. Contract에 `tenant_id`, `workspace_id`, `user_id`, `ContextMesh` trace snapshot을
   optional로 추가합니다.
2. Sample adapter에 `ContextMesh` assembly를 넣고 `context_mesh_built` trace를
   기록합니다.
3. Deterministic `ComplexityRouter`와 route trace를 추가합니다.
4. Portable `SKILL.md` folder 기반 read-only skill registry를 추가합니다.
5. 기존 TechNews tool을 tenant-aware tool binding으로 감쌉니다.
6. Deep Agents path는 `ContextMesh`가 넘긴 scoped skill/tool/memory만 사용하게
   연결합니다.
7. Memory, skill, tool binding, replay identity, trace visibility에
   cross-tenant leakage test를 추가합니다.

## Roadmap / Open Decisions

이 섹션은 adaptive-agent 설계의 짧은 작업 체크리스트로 유지합니다. 별도 TODO
문서는 roadmap이 이 architecture 문서 안에서 관리하기 어려울 정도로 커졌을 때
분리합니다.

- Routing marker: `_SYNTHESIS_MARKERS`, `_SIMPLE_MARKERS`,
  `_MULTI_STEP_MARKERS`는 deterministic v1 bootstrap rule로만 유지합니다.
- Routing policy: tenant config storage가 생기면 tenant별 routing term은 code가
  아니라 tenant policy/config로 이동합니다.
- Semantic cache: trace contract가 안정된 뒤 추가해서 반복/유사 질문은 model call
  없이 route/tool decision을 재사용할 수 있게 합니다.
- Classifier model: 작은 classifier는 애매한 요청에만 사용합니다.
  Deterministic/semantic layer로 충분하면 모든 요청에 호출하지 않습니다.
- Skill registry: portable `SKILL.md` folder는 유지하되, tenant enablement,
  approval, version, hash policy는 runtime registry로 이동합니다.
- Tool Gateway: tenant-aware tool binding을 light와 deep execution이 공유하는
  contract로 유지합니다.
- Deep path: deep execution을 default-on으로 둘지, tenant 기준으로 켤지,
  agent policy 기준으로 켤지 결정할 때까지 Deep Agents는
  `TECH_RADAR_DEEP_PATH_ENABLED` 뒤에 둡니다.
- Trace contract: 내부 구현이 바뀌어도 `context_mesh_built`,
  `complexity_classified`, `route_selected`, `skill_catalog_filtered`,
  `skill_loaded`, `tool_binding_resolved`는 안정적으로 유지합니다.

## Current Implementation Status

초기 contract phase는 구현되어 있습니다.

- `RuntimeRunCreateRequest`가 optional `tenant_id`, `workspace_id`, `user_id`를
  받습니다.
- `RuntimeRunResponse`가 resolved identity field를 반환합니다.
- `tenant_id`가 없으면 명시적인 `tenant:default` boundary로 resolve합니다.
- `TraceableRuntimeAdapter`는 policy/tool 실행 전에 `context_mesh_built` trace를
  기록합니다.
- Focused test는 default tenant resolution과 tenant/user/session이 ContextMesh
  trace step으로 전달되는지 확인합니다.

첫 adaptive routing phase도 구현되어 있습니다.

- `ComplexityRouter`가 deterministic rule과 visible score로 요청을 분류합니다.
- `TraceableRuntimeAdapter`가 `complexity_classified`, `route_selected`,
  `light_plan_created`를 기록합니다.
- 단순 news/search 요청은 light path에 남습니다.
- synthesis, comparison, strategy, risk, report-style 요청은 deep candidate로
  표시합니다.
- Portable `SKILL.md` folder는 read-only `SkillRegistry`를 통해 로드합니다.
- 모든 run에 `skill_catalog_filtered`를 기록하고, `daily-news-freshness` 또는
  `tech-trend-briefing`이 적용되면 `skill_loaded`를 기록합니다.
- TechNews tool은 tenant-aware Tool Binding layer를 통해 resolve합니다.
- `tool_binding_resolved`는 policy/tool 실행 전에 binding id, allowed scope,
  hashed credential reference를 기록합니다.
- Focused cross-tenant leakage test가 ContextMesh memory namespace, skill
  filtering trace, Tool Binding trace, runtime snapshot, external replay payload가
  resolved tenant boundary 안에 머무는지 확인합니다.
- Runtime-facing adapter는 `build_deep_agent`로 이어지는 `DeepPathRunner`
  bridge를 가집니다. Deep candidate는 기본적으로 light path로 fallback되지만,
  `TECH_RADAR_DEEP_PATH_ENABLED=true`이면 Deep Agents path를 호출합니다.
- Deep path trace에는 `deep_agent_started`, `model_call_started`,
  `model_call_completed`, `deep_agent_completed`가 남습니다. Deep path가 실패하면
  `deep_agent_failed`를 기록하고 deterministic light path를 사용합니다.
- Deep Agents graph에서 발생하는 LangChain callback event는 가능한 경우
  `deep_model_call_started`, `deep_model_call_completed`,
  `deep_tool_call_started`, `deep_tool_call_completed` 같은 route-specific trace
  step으로 bridge합니다.
- `DeepPathRunner`는 LangChain/Gemini graph response를 plain `output_text`로
  normalize합니다. Graph가 tool result 이후 최종 assistant message 없이 멈추면,
  readable tool-result summary로 fallback하기 전에 최종 synthesis를 한 번 더
  요청합니다.

Gemini live smoke로 enabled deep path, model/tool callback bridge, final answer
추출은 확인했습니다. 다음 구현 작업은 답변 품질 케이스, tool replay와 model
replay의 의미 분리, semantic filter가 bootstrap marker router를 넘어설 경우의
structured query planning에 초점을 둡니다.
