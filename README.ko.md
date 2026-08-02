# Traceable Deep Agents Sample

trace 가능한 Tech Radar 분석 agent를 위한 작은 Deep Agents sample입니다.

첫 번째 milestone은 fixture data로 로컬에서 실행됩니다. 그래서 실행 동작,
source 처리, trace 출력을 실제 서비스 의존 없이 테스트할 수 있습니다. 실제
knowledge source는 이 workspace의 Personal Tech Radar 서비스인
`technews-publisher`입니다.

이 sample은 `traceable-agent-runtime` 뒤에서 external Agent Server adapter로도
실행할 수 있습니다. 이 모드에서는 runtime이 public run/trace API를 소유하고,
sample이 만든 trace를 runtime trace store로 가져옵니다.

English documentation is available at [README.md](README.md).
Architecture 문서는 [docs/architecture.ko.md](docs/architecture.ko.md)와
[docs/architecture.html](docs/architecture.html)에 있습니다.
Adaptive, multi-tenant agent target design은
[docs/adaptive-agent-architecture.ko.md](docs/adaptive-agent-architecture.ko.md)에
정리되어 있습니다.
현재 route와 runtime 검증 계획은 [docs/test-plan.ko.md](docs/test-plan.ko.md)에
정리되어 있습니다.

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

CLI는 다음 정보를 출력합니다.

- answer
- sources
- run id
- trace path

## Test

```bash
pytest
```

## External Agent Server

sample을 작은 Agent Server-compatible service로 실행합니다.

```bash
tech-radar-agent-server
```

그 다음 run을 만들고 trace를 조회할 수 있습니다.

```bash
curl -fsS http://127.0.0.1:8776/v1/agents

curl -fsS -X POST http://127.0.0.1:8776/v1/runs \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"tech-radar","input":"최근 AI Agent 관련 뉴스는 뭐야?"}'

curl -fsS http://127.0.0.1:8776/v1/runs/<run_id>/trace
```

`traceable-agent-runtime`에 `agents/tech-radar.yaml` 같은 manifest가 있으면,
client는 보통 sample을 직접 호출하지 않고 runtime의 `8765` 포트를 호출합니다.

```bash
curl -fsS -X POST http://127.0.0.1:8765/v1/runs \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"tech-radar","input":"최근 AI Agent 관련 뉴스는 뭐야?"}'
```

runtime은 실행을 이 service에 위임한 뒤 반환된 trace를 import합니다. 그래서
runtime의 `GET /v1/runs/<run_id>/trace`는 같은 evidence-backed execution
timeline을 반환합니다.

External service는 `GET /v1/agents`에서 replay 지원 여부를 광고합니다. Runtime
frozen replay는 일반 `POST /v1/runs` request 안에 `replay.tool_mode="frozen"`과
portable frozen tool result를 함께 보내고, sample은 matching frozen tool output을
재사용해 live TechNews tool 호출을 건너뜁니다.

## Notes

- MVP tool은 read-only입니다.
- Fixture data는 synthetic data입니다.
- Deep Agents integration은 `build_deep_agent`와 runtime-facing `DeepPathRunner`를
  통해 노출됩니다.
- deterministic fixture test는 live LLM credential 없이 동작합니다.
- runtime-compatible adapter는 deterministic `ComplexityRouter`를 실행합니다.
  Tool 실행 전에 `complexity_classified`, `route_selected`,
  `light_plan_created`를 기록합니다. Deep candidate는 기본적으로 light path로
  fallback되지만, `TECH_RADAR_DEEP_PATH_ENABLED=true`이면 같은 ContextMesh,
  SkillRegistry, Tool Binding boundary 뒤에서 Deep Agents path를 호출합니다.
- Deep Agents graph가 model/tool callback을 내보내면 route-specific trace step으로
  bridge합니다.
- Portable skill은 `traceable_deep_agents_sample/skills/*/SKILL.md` 아래에
  둡니다. Adapter는 매 run마다 `skill_catalog_filtered`를 기록하고,
  freshness나 trend briefing skill이 적용되면 `skill_loaded`를 기록합니다.
- TechNews tool은 tenant-aware Tool Binding layer를 통해 resolve합니다. Adapter는
  policy/tool 실행 전에 binding id, scope, hashed credential reference를 담은
  `tool_binding_resolved`를 기록합니다.
- 실제 TechNews adapter는 `technews-publisher` read API를 사용합니다.
  - `/api/issues/latest`
  - `/api/issues/search`
  - `/api/issues/{slug}`
- TechNews는 매일 아침 전날 기준 GeekNews 요약을 저장합니다. 사용자가 오늘
  뉴스를 물으면 runtime-compatible adapter는 최신 issue를 사용하고, 오늘 수집분이
  아직 없을 수 있음을 답변에 명시합니다.

## Deep Agents LLM Provider

기본적으로 sample은 `traceable-agent-runtime`과 같은 provider vocabulary를
사용합니다.

```bash
export TECH_RADAR_LLM_PROVIDER=openai
export TECH_RADAR_LLM_MODEL=gpt-5.5
export OPENAI_API_KEY=...
```

Gemini는 runtime-compatible Gemini 환경 변수로 사용할 수 있습니다.

```bash
export TECH_RADAR_LLM_PROVIDER=gemini
export TECH_RADAR_GEMINI_MODEL=gemini-2.5-flash
export TECH_RADAR_GEMINI_API_KEY=...
```

`TECH_RADAR_MODEL`은 Deep Agents/LangChain model string을 직접 넘기는 override로
계속 지원합니다. provider-specific 설정을 사용할 때는 비워둡니다.

## Real TechNews API Adapter

실제 Personal Tech Radar service를 쓰려면 다음처럼 설정합니다.

```bash
export TECH_RADAR_KNOWLEDGE_BACKEND=technews
export TECHNEWS_API_BASE_URL=http://127.0.0.1:8010
```

API가 인증을 요구하면 둘 중 하나를 설정합니다.

```bash
export TECHNEWS_AUTH_TOKEN=...
export TECHNEWS_SESSION_COOKIE='idounai_session=...'
```

agent tool은 read endpoint만 모델링합니다.

모델링된 tool:

- `search_tech_news`: published TechNews issue 검색
- `get_latest_tech_news`: 최신 published daily issue 조회
- `get_tech_news_article`: slug 기준 단일 issue 조회

로컬 service wrapper에서 생성한 session cookie나 API token은 git 밖에 둡니다.
sample은 bearer token 또는 전체 `idounai_session=...` cookie string을 받고,
그 값을 TechNews backend에만 전달합니다.
운영에 가까운 service 구성에서는 필요한 private 값을 sample service 전용 env
파일에 복사해서 둡니다. 이 service가 다른 repository의 runtime/app env 파일을
직접 참조하게 만들지 않습니다.

## Runtime Compatibility

`TraceableRuntimeAdapter`는 `traceable-agent-runtime` 형태의 run, trace, agent
capability 응답을 로컬에서 생성합니다. 자세한 runtime contract는
[docs/runtime-interface.ko.md](docs/runtime-interface.ko.md)를 참고하세요.
영문 runtime contract는 [docs/runtime-interface.md](docs/runtime-interface.md)에
있습니다.

idounAIChat -> runtime -> sample -> TechNews 전체 동작 메커니즘은
[docs/agent-mechanism.ko.md](docs/agent-mechanism.ko.md)에 한국어로 정리되어
있습니다.

형제 checkout으로 `traceable-agent-runtime`이 있으면 contract를 검증할 수
있습니다.

```bash
python scripts/check_runtime_contract.py
```
