# 모듈 설명서

이 문서는 `traceable-deep-agents-sample`의 중요 모듈을 코드 기준으로 정리한
개발자용 reference 문서입니다.

각 모듈은 같은 형식으로 정리합니다.

- 역할
- 입력
- 출력
- 의존성
- 부작용과 상태
- 구현 정도
- 향후 방향

문서 형식은 Diataxis의 구분을 참고했습니다. 이 문서는 주로 reference이고,
경계가 헷갈리기 쉬운 부분만 짧은 explanation을 덧붙입니다. 되돌리기 어려운
아키텍처 결정은 필요해질 때 ADR로 별도 기록하는 것이 맞습니다.

## 실행 모드

sample은 두 가지 방식으로 실행될 수 있습니다.

단독 실행 모드:

```text
client -> traceable-deep-agents-sample :8776
```

이 모드는 로컬 개발, contract 확인, smoke test에 유용합니다. sample이 HTTP
경계, 실행, 짧은 in-process trace 조회를 직접 담당합니다.

runtime adapter 모드:

```text
idounAIChat -> traceable-agent-runtime :8765
            -> traceable-deep-agents-sample :8776
            -> TechNews API
```

현재 idounAIChat과 AgentOps에서 쓰는 흐름은 이쪽입니다. sample은 Tech Radar
agent 동작을 실행하지만, public Agent Server API, durable trace store, replay,
diff, eval, Workbench 연동은 `traceable-agent-runtime`이 담당합니다.

## 모듈 요약

| 모듈 | 주 역할 | 현재 구현 정도 |
| --- | --- | --- |
| `api.py` | runtime-compatible external service의 FastAPI 경계 | 동작함, 의도적으로 얇음 |
| `server.py` | external service용 Uvicorn entrypoint | 동작함 |
| `runtime_contract.py` | `traceable-agent-runtime`과 맞춘 Pydantic 요청/응답 모델 | 동작함, 로컬 mirror contract |
| `runtime_adapter.py` | runtime-compatible 실행 orchestration의 중심 | MVP 동작, trace는 sample 내부 memory |
| `complexity_router.py` | light/deep route 결정 | bootstrap rule 기반으로 동작 |
| `context_mesh.py` | tenant/workspace/user/session context envelope 생성 | lightweight snapshot 동작 |
| `skill_registry.py` | portable `SKILL.md` 탐색과 선택 | static registry 동작 |
| `tool_binding.py` | tenant-scoped read-only TechNews tool binding | static resolver 동작 |
| `deep_agent.py` | Deep Agents graph factory와 provider/model resolution | 설정된 provider 기준 동작 |
| `deep_path.py` | deep route 실행, callback trace bridge, 답변 정규화 | synthesis retry 포함 MVP 동작 |
| `tools.py` | knowledge store 위의 tool facade | 동작함 |
| `knowledge/fixture_store.py` | test/offline용 JSONL article store | 동작함 |
| `knowledge/technews_api_store.py` | 실제 `technews-publisher` read API adapter | read adapter 동작 |
| `agent.py` | 이전 standalone fixture agent와 JSONL trace 경로 | legacy/dev path로 동작 |
| `tracing/*` | standalone 모드용 JSONL trace event/sink | legacy/dev path로 동작 |
| `config.py` | environment 기반 settings | 동작함 |
| `models.py` | domain/CLI response model | 동작함 |
| `prompts.py` | Deep Agents system prompt | 동작함 |
| `cli.py` | fixture agent용 CLI entrypoint | 동작함 |

## `api.py`

역할:

- sample을 `traceable-agent-runtime`이 호출할 수 있는 external Agent Server
  compatible FastAPI service로 노출합니다.
- HTTP 처리와 실제 runtime orchestration을 분리합니다.

입력:

- `POST /v1/runs`의 `RuntimeRunCreateRequest`
- `GET /v1/runs/{run_id}/trace`의 run id path parameter
- test에서 선택적으로 주입하는 `Settings`

출력:

- `GET /v1/agents`의 `RuntimeAgentListResponse`
- `POST /v1/runs`의 `RuntimeRunResponse`
- `GET /v1/runs/{run_id}/trace`의 `RuntimeTraceResponse`
- in-process trace map에 run이 없으면 `404 Trace not found`

의존성:

- `Settings`
- `TraceableRuntimeAdapter`
- runtime contract Pydantic model
- FastAPI

부작용과 상태:

- app instance마다 `TraceableRuntimeAdapter` 하나를 생성합니다.
- trace 조회는 해당 adapter instance의 in-memory state에 의존합니다.

구현 정도:

- local service smoke test와 runtime external adapter 연동에는 충분합니다.
- auth, multi-process trace 공유, sample-side persistent trace DB는 없습니다.

향후 방향:

- 이 파일은 계속 얇게 유지합니다.
- trace handoff가 inline trace response나 OTel export로 바뀌더라도 HTTP
  contract만 반영하고, 변환 로직은 adapter/exporter 쪽에 둡니다.

## `server.py`

역할:

- FastAPI app을 Uvicorn으로 실행하는 console-script entrypoint입니다.

입력:

- `TECH_RADAR_SERVER_HOST`, `TECH_RADAR_SERVER_PORT` 등 환경 기반 `Settings`

출력:

- 실행 중인 HTTP server

의존성:

- `uvicorn`
- `Settings`
- `traceable_deep_agents_sample.api:app`

부작용과 상태:

- 설정된 host/port에 bind합니다.

구현 정도:

- 최소 구현으로 동작합니다.

향후 방향:

- 계속 최소로 유지합니다.
- production process 관리는 systemd나 container 설정에 둡니다.

## `runtime_contract.py`

역할:

- runtime-compatible request/response/trace contract를 로컬 Pydantic model로
  정의합니다.

입력:

- client 또는 `traceable-agent-runtime`에서 들어오는 JSON request payload
- `RuntimeReplayContext`를 통한 frozen replay payload

출력:

- 검증된 run, trace, step, capability, agent list model

의존성:

- Pydantic

부작용과 상태:

- 없습니다.

구현 정도:

- runtime contract의 functional local mirror입니다.
- contract drift는 `scripts/check_runtime_contract.py`로 확인합니다.

향후 방향:

- runtime과 sample이 계속 함께 진화한다면 작은 shared contract package를
  검토할 수 있습니다.
- OTel export를 추가하더라도 이 model은 Agent Server contract로 두고,
  `StepRecord -> span/event` mapper를 별도로 둡니다.

## `runtime_adapter.py`

역할:

- runtime-compatible run의 핵심 orchestration module입니다.
- context 생성, complexity classification, skill 선택, tool binding resolve,
  light/deep path 실행, trace step 기록, frozen tool replay, 즉시 trace 조회용
  저장을 담당합니다.

입력:

- `RuntimeRunCreateRequest`
- 환경 기반 `Settings`
- test에서 주입 가능한 `DeepPathRunner`
- `tool_mode=\"frozen\"` replay 시 frozen tool result

출력:

- `RuntimeRunResponse`
- `get_trace`의 `RuntimeTraceResponse`
- `context_mesh_built`, `route_selected`, `deep_model_call_completed`,
  `tool_call_completed`, `final_answer` 같은 runtime step record

의존성:

- `ComplexityRouter`
- `build_context_mesh`
- `SkillRegistry`
- `ToolBindingResolver`
- `DeepPathRunner`
- `TechRadarTools`
- `FixtureArticleStore`
- `TechNewsApiStore`
- runtime contract model

부작용과 상태:

- 완료된 trace를 `self._traces` in-memory dictionary에 저장합니다.
- `TECH_RADAR_KNOWLEDGE_BACKEND=technews`이고 live tool execution이 필요하면
  실제 TechNews API를 호출합니다.
- token/cookie/secret 형태의 값은 trace 기록 전에 redact합니다.

구현 정도:

- adaptive routing, tool replay, runtime trace import, Deep Agents fallback의
  MVP로 동작합니다.
- step timing은 아직 거칠고, 생성되는 step latency는 현재 `0`입니다.
- sample-side trace state는 durable하지 않고 process 간 공유되지 않습니다.
- runtime 모드에서는 아직 동기 handoff를 씁니다. runtime이 sample
  `POST /v1/runs`를 호출한 뒤 `trace_url`을 따라 `GET /trace`를 한 번 더
  호출합니다.

향후 방향:

- trace recording/export를 interface 뒤로 분리합니다.
- `RuntimeStepRecord`의 OTel-compatible mapper를 추가합니다.
- `POST /v1/runs` 응답에 inline trace를 선택적으로 포함해 두 번째
  runtime-to-sample HTTP call을 줄이는 방안을 검토합니다.
- route, replay, policy 같은 control-plane 의미와 observability transport를
  분리합니다.

## `complexity_router.py`

역할:

- light/deep 실행을 위한 cheap deterministic first-pass classifier입니다.

입력:

- 사용자 입력 text

출력:

- `route`, `score`, `reasons`를 가진 `ComplexityDecision`

의존성:

- Python dataclasses와 literal type만 사용합니다.

부작용과 상태:

- 없습니다.

구현 정도:

- bootstrap rule 기반으로 동작합니다.
- simple lookup, synthesis/comparison/risk, evidence/report,
  semantic exclusion/filter marker를 처리합니다.

향후 방향:

- route matrix가 커지면 marker weight를 tenant 또는 agent policy로 옮깁니다.
- 날짜/filter/exclusion semantics는 deep routing만으로 해결하지 말고
  structured query planning을 추가합니다.
- model-based classifier는 충분한 test case가 쌓인 뒤 선택적으로 검토합니다.

## `context_mesh.py`

역할:

- tenant, workspace, user, session identity로 portable context envelope을
  만듭니다.

입력:

- `RuntimeRunCreateRequest`

출력:

- tenant identity, optional workspace/user/session, memory namespace hint를
  담은 dictionary

의존성:

- runtime contract request model

부작용과 상태:

- 없습니다.

구현 정도:

- lightweight ContextMesh snapshot으로 동작합니다.
- tenant가 없으면 `tenant:default`를 사용합니다.

향후 방향:

- static sample data를 넘어 real policy, memory, skill/tool allowlist가 생기면
  여기에 연결합니다.
- 공유와 테스트가 쉽도록 pure module로 유지합니다.

## `skill_registry.py`

역할:

- local portable skill을 발견하고 run에 필요한 skill을 선택합니다.

입력:

- 사용자 입력
- `ComplexityDecision`
- `traceable_deep_agents_sample/skills/*/SKILL.md`

출력:

- id, name, version, relative path, content hash, selection reason을 가진
  `SkillRef`

의존성:

- `ComplexityDecision`
- local filesystem
- SHA-256 hashing

부작용과 상태:

- skill file을 disk에서 읽습니다.

구현 정도:

- static registry로 동작합니다.
- 현재 skill:
  - `daily-news-freshness`
  - `tech-trend-briefing`

향후 방향:

- tenant-aware skill allowlist를 추가합니다.
- skill이 extension surface가 되면 metadata validation을 더 엄격하게 합니다.
- 실제 skill이 더 쌓이기 전에는 general plugin system으로 키우지 않습니다.

## `tool_binding.py`

역할:

- model-visible TechNews tool을 tenant-scoped read-only binding으로 resolve합니다.

입력:

- tenant id
- tool name

출력:

- binding id, allowed scopes, hashed credential reference를 가진 `ToolBinding`

의존성:

- static `ToolDefinition` registry
- SHA-256 hashing

부작용과 상태:

- 없습니다.
- 실제 credential은 읽지 않고 redacted reference shape만 기록합니다.

구현 정도:

- 세 개의 read-only tool에 대해 static resolver로 동작합니다.

향후 방향:

- 실제 binding policy를 runtime 또는 tenant configuration에서 resolve합니다.
- write tool이 생긴다면 tool invocation boundary에 더 가까운 곳에서 scope를
  enforce합니다.

## `deep_agent.py`

역할:

- read-only Tech Radar tool을 가진 Deep Agents graph를 만들고 provider/model을
  resolve합니다.

입력:

- `Settings`
- 선택적 LangChain chat model 또는 model string override

출력:

- Deep Agents runnable graph

의존성:

- `deepagents`
- LangChain tool decorator
- Gemini 사용 시 `langchain_google_genai`
- `TechRadarTools`
- `FixtureArticleStore`
- `TechNewsApiStore`
- `SYSTEM_PROMPT`

부작용과 상태:

- model string 기반 Deep Agents 실행을 위해 read-only harness profile을
  등록합니다.
- 선택된 knowledge backend에 bind된 tool function을 만듭니다.

구현 정도:

- OpenAI-style model string과 Gemini chat model construction 기준으로 동작합니다.
- read-only tool restriction은 excluded harness tools로 명시되어 있습니다.

향후 방향:

- provider 선택은 작고 runtime-compatible하게 유지합니다.
- 새 provider가 필요할 때만 capability check를 추가합니다.
- UI label이 trace에서만 추론되지 않도록 tool metadata 공유를 검토합니다.

## `deep_path.py`

역할:

- runtime adapter 경계 뒤에서 Deep Agents path를 실행합니다.
- LangChain callback을 runtime trace event로 변환합니다.
- Deep Agents response를 사용자에게 보여줄 answer text로 정규화합니다.

입력:

- `RuntimeRunCreateRequest`
- ContextMesh dictionary
- 선택된 skill 목록
- Tool binding
- test에서 주입 가능한 agent factory

출력:

- answer text, raw output summary, trace event list를 가진 `DeepPathResult`

의존성:

- `build_deep_agent`
- LangChain callback base class
- runtime request model
- `SkillRef`
- `ToolBinding`

부작용과 상태:

- adapter에서 활성화되면 live LLM/tool graph를 호출합니다.
- initial call과 synthesis retry가 같은 callback collector를 사용하므로 두 시도가
  trace event에 함께 남습니다.

구현 정도:

- MVP로 동작합니다.
- string, mapping, message-list, LangChain content-list output을 처리합니다.
- model이 tool result 이후 멈추면 final synthesis instruction으로 한 번 재시도합니다.
- 그래도 실패하면 readable tool-result summary로 fallback합니다.

향후 방향:

- provider response에서 안정적으로 얻을 수 있을 때 token/cost/model metadata를
  더 풍부하게 기록합니다.
- callback event를 OTel span/event로 매핑합니다.
- raw provider object가 사용자 답변이나 trace에 새지 않게 유지합니다.

## `tools.py`

역할:

- deterministic path와 Deep Agents path가 함께 쓰는 stable tool facade입니다.

입력:

- `search`, `latest`, `get_article` method를 가진 store object
- query, slug, limit, optional tags, optional minimum score

출력:

- tool call용 JSON-serializable dictionary

의존성:

- convention 기반 knowledge store contract

부작용과 상태:

- 실제 부작용은 underlying store에 위임합니다.

구현 정도:

- 세 개 read-only tool의 facade로 동작합니다.

향후 방향:

- store가 추가되면 formal protocol 도입을 검토합니다.
- 이 모듈은 tool output normalization boundary로 유지합니다.

## `knowledge/fixture_store.py`

역할:

- CLI, test, offline smoke run을 위한 deterministic local article data를 제공합니다.

입력:

- JSONL data file path
- search query, limit, optional tags, optional minimum score

출력:

- `Article`, `SearchResult` model

의존성:

- local JSONL fixture data
- `Article`
- `SearchResult`

부작용과 상태:

- fixture article을 lazy load하고 memory에 cache합니다.

구현 정도:

- deterministic store로 동작합니다.
- search는 단순 term matching과 local scoring입니다.

향후 방향:

- 의도적으로 단순하게 유지합니다. production search backend로 키우지 않습니다.
- route/tool behavior를 test로 보호할 때 필요한 fixture만 추가합니다.

## `knowledge/technews_api_store.py`

역할:

- 실제 `technews-publisher` read API를 fixture store와 같은 store shape로
  맞춥니다.

입력:

- base URL
- timeout
- optional bearer token 또는 session cookie
- search query, slug, tags, score filters

출력:

- `Article`, `SearchResult` model

의존성:

- `httpx`
- `Article`
- `ArticleScore`
- `SearchResult`
- `technews-publisher` read endpoint:
  - `/api/issues/latest`
  - `/api/issues/search`
  - `/api/issues/{slug}`

부작용과 상태:

- outbound HTTP GET request를 만듭니다.
- auth header/cookie는 설정된 TechNews base URL에만 보냅니다.

구현 정도:

- read adapter로 동작합니다.
- `latest`는 single latest issue API response를 list로 바꿔 store 호환성을 유지합니다.
- tag/score filter는 API response 정규화 이후 local에서 적용합니다.

향후 방향:

- write API는 이 adapter에 넣지 않습니다.
- `technews-publisher`가 structured query parameter를 제공하면 연결합니다.
- request latency/error category를 trace 또는 OTel attribute로 노출합니다.

## `agent.py`

역할:

- CLI와 초기 test에서 쓰는 이전 standalone fixture agent입니다.

입력:

- 사용자 질문
- optional `Settings`
- optional thread id

출력:

- answer, sources, run id, thread id, JSONL trace path를 가진 `AgentResponse`

의존성:

- `FixtureArticleStore`
- `TechRadarTools`
- `JsonlTraceSink`
- domain model

부작용과 상태:

- `Settings.trace_dir` 아래 JSONL trace file을 씁니다.
- fixture data를 읽습니다.

구현 정도:

- development path로 동작합니다.
- runtime-compatible trace contract와는 별도 경로입니다.

향후 방향:

- simple local smoke path로 유지하거나 runtime-compatible CLI coverage가 충분해지면
  정리합니다.
- runtime replay나 Deep Agents complexity는 여기에 추가하지 않고
  `runtime_adapter.py`에 둡니다.

## `tracing/events.py`와 `tracing/jsonl_sink.py`

역할:

- standalone fixture mode용 local JSONL trace event model과 file sink를 제공합니다.

입력:

- `TraceEvent`
- trace directory
- run id

출력:

- JSONL trace file

의존성:

- Pydantic
- local filesystem

부작용과 상태:

- 필요하면 trace directory를 만듭니다.
- local file에 trace event를 append합니다.

구현 정도:

- local CLI trace 용도로 동작합니다.
- runtime/AgentOps trace store로는 쓰이지 않습니다.

향후 방향:

- runtime-compatible trace와 같은 OTel exporter로 대체할지 검토합니다.
- 두 번째 durable trace model로 키우지 않습니다.

## `config.py`

역할:

- local, runtime-compatible, Deep Agents 실행에 필요한 environment-backed
  settings를 모읍니다.

입력:

- `.env`
- `TECH_RADAR_*`
- `TECHNEWS_API_BASE_URL`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`
  같은 일부 compatibility alias

출력:

- `Settings`

의존성:

- `pydantic-settings`

부작용과 상태:

- environment와 optional `.env`를 읽습니다.

구현 정도:

- 동작합니다.
- fixture/real TechNews backend, execution mode, Deep Agents flag,
  provider-specific model setting을 지원합니다.

향후 방향:

- sample service 전용 private env 값을 runtime/application env file과 분리해서
  유지합니다.
- 새 설정은 구체적인 runtime 또는 deployment 경로가 필요할 때만 추가합니다.

## `models.py`

역할:

- article store, tool output, standalone fixture agent에서 쓰는 domain model을
  정의합니다.

입력:

- fixture 또는 TechNews API response에서 parsing된 JSON data

출력:

- `ArticleScore`
- `Article`
- `SearchResult`
- `Source`
- `AgentResponse`

의존성:

- Pydantic

부작용과 상태:

- 없습니다.

구현 정도:

- 동작합니다.
- `Source`, `AgentResponse`는 주로 standalone mode용이고, 나머지는 store/tool에서
  공유됩니다.

향후 방향:

- store/domain model과 runtime contract model을 분리해서 유지합니다.
- TechNews가 반환하고 test/UI에서 실제로 쓰는 field만 추가합니다.

## `prompts.py`

역할:

- Deep Agents system prompt를 보관합니다.

입력:

- import 외 runtime 입력은 없습니다.

출력:

- `SYSTEM_PROMPT`

의존성:

- 없습니다.

부작용과 상태:

- 없습니다.

구현 정도:

- compact prompt로 동작합니다.
- 한국어 기본 답변, evidence-first behavior, untrusted article text, freshness note,
  no-evidence fallback을 담고 있습니다.

향후 방향:

- prompt 변경은 route/test-plan update와 함께 관리합니다.
- prompt versioning이 중요해지면 version metadata를 trace에 남깁니다.

## `cli.py`

역할:

- fixture agent용 command-line smoke path입니다.

입력:

- positional question string

출력:

- stdout에 answer, sources, run id, trace path 출력

의존성:

- `run_fixture_agent`
- `argparse`

부작용과 상태:

- fixture agent를 통해 JSONL trace를 씁니다.

구현 정도:

- local utility로 동작합니다.

향후 방향:

- operator smoke test에 유용해질 때만 runtime-compatible CLI mode를 추가합니다.

## Skill 파일

역할:

- `SkillRegistry`가 읽는 portable instruction bundle입니다.

입력:

- registry selection을 통한 사용자 입력과 `ComplexityDecision`

출력:

- trace에 기록되는 skill metadata와 instruction text hash

의존성:

- local `SKILL.md` file

부작용과 상태:

- file read 외에는 없습니다.

구현 정도:

- static skill로 동작합니다.
- 현재 skill:
  - `daily-news-freshness`
  - `tech-trend-briefing`

향후 방향:

- 실제 behavior에 의미 있는 skill만 추가합니다.
- skill file은 복사 가능하고 private runtime/application env에 의존하지 않게
  유지합니다.

## 현재 공통 gap

- runtime trace handoff가 synchronous이고 추가 `GET /trace` call을 사용합니다.
- sample-side runtime trace는 in-memory입니다.
- trace event는 아직 OTel span/event가 아니라 runtime-specific record입니다.
- tool replay는 구현되어 있지만 model replay는 별도 future concept입니다.
- 날짜/filter/exclusion을 구조화하는 planner는 아직 없습니다. semantic filter
  request는 interim safety로 deep route에 태웁니다.
- Langfuse/LangSmith 전환에는 model, prompt, token, cost, tool call, route,
  replay semantics mapping이 여전히 필요합니다.

## 참고한 문서 규격

- Diataxis documentation framework: https://diataxis.fr/
- Architecture Decision Records: https://github.com/architecture-decision-record/architecture-decision-record
- AWS ADR process guidance: https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html
