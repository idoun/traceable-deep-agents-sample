# Tech Radar Agent 동작 메커니즘

이 문서는 `tech-radar` agent가 idounAIChat, traceable-agent-runtime,
traceable-deep-agents-sample, technews-publisher 사이에서 어떻게 실행되고
trace를 남기는지 설명한다.

## 한 줄 요약

`tech-radar`는 idounAIChat 안에 내장된 agent가 아니다. idounAIChat은 실행
콘솔과 trace UI를 제공하고, `traceable-agent-runtime`은 Agent Server API와
trace store를 소유하며, `traceable-deep-agents-sample`은 TechNews 읽기
도구를 실행하는 외부 adapter 역할을 한다.

## 전체 실행 흐름

```text
사용자
-> idounAIChat frontend
-> idounAIChat backend proxy
-> traceable-agent-runtime :8765
-> traceable-deep-agents-sample :8776
-> technews-publisher read API :8010
```

1. 사용자가 idounAIChat에서 Agent Server Mode로 메시지를 보낸다.
2. idounAIChat frontend는 backend의 `/api/chat/agent-runs/stream`로 요청한다.
3. idounAIChat backend는 VM 내부 Agent Server URL로 요청을 proxy한다.
4. traceable-agent-runtime은 `agent_id=tech-radar` manifest를 로드한다.
5. manifest의 `external_adapter` 설정에 따라 sample server의 `/v1/runs`를 호출한다.
6. sample server는 TechNews read tool을 실행하고 runtime 호환 run/trace 응답을 만든다.
7. runtime은 sample trace를 자기 trace store로 import한다.
8. idounAIChat은 runtime의 `/v1/runs/{run_id}/trace`를 다시 조회해 trace timeline을 보여준다.

## 각 프로젝트의 역할

### idounAIChat

idounAIChat은 agent runtime이 아니라 사용자-facing chat UI다.

- Agent Server Mode 선택 UI를 제공한다.
- agent 목록을 backend proxy를 통해 조회한다.
- `tech-radar` agent가 있으면 기본 선택값으로 우선 사용한다.
- 사용자의 메시지를 Agent Server run 요청으로 보낸다.
- run 결과의 `run_id`, `status`, `agent_id`, final output을 메시지에 붙인다.
- run 완료 후 trace를 자동 조회한다.
- 실패 응답에도 `run_id`가 있으면 실패 trace를 조회한다.
- replay, trace, diff 요청도 backend proxy를 통해 runtime으로 전달한다.

idounAIChat은 Agent Server의 `core_instruction`, policy, tool 실행을 직접
수행하지 않는다. Prompt Workbench의 prompt draft는 Agent Server Mode에서
`session_instruction`으로만 전달되며, manifest의 `core_instruction`이나
policy를 대체하지 않는다.

### traceable-agent-runtime

traceable-agent-runtime은 Agent Server API의 중심이다.

- `/v1/agents`로 manifest 목록을 노출한다.
- `/v1/runs`와 `/v1/runs/stream` 요청을 받는다.
- `agents/tech-radar.yaml` manifest를 로드한다.
- manifest에 `external_adapter`가 있으면 내부 runtime loop 대신 외부
  adapter client를 사용한다.
- 외부 adapter가 돌려준 trace를 runtime trace store로 import한다.
- import된 trace를 기존 `/v1/runs/{run_id}/trace` 경로에서 그대로 제공한다.
- adapter 호출 자체가 실패하면 local failed run을 만들고
  `external_adapter_call` step을 남긴다.

`tech-radar` manifest의 핵심은 아래 설정이다.

```yaml
external_adapter:
  base_url: http://127.0.0.1:8776
  agent_id: tech-radar
  timeout_ms: 30000
```

이 설정 때문에 runtime은 `tech-radar` 실행을 직접 처리하지 않고
`traceable-deep-agents-sample`에 위임한다.

### traceable-deep-agents-sample

traceable-deep-agents-sample은 Tech Radar agent의 실제 도구 계층을 가진
외부 Agent Server-compatible service다.

노출 API:

- `GET /health`
- `POST /v1/runs`
- `GET /v1/runs/{run_id}/trace`

현재 runtime-facing 경로는 `TraceableRuntimeAdapter`가 담당한다. 이 adapter는
runtime과 같은 run/trace shape를 만들고, 다음 step 순서로 trace를 기록한다.

1. `run_started`
2. `manifest_loaded`
3. `prompt_composed`
4. `policy_decision`
5. `tool_call_started`
6. `tool_call_completed`
7. `final_answer`
8. `run_completed`

중요한 점은 `policy_decision`이 `tool_call_started`보다 먼저 기록된다는
것이다. 이 순서 덕분에 나중에 trace나 eval에서 “도구 호출 전에 정책 판단이
있었는지”를 검증할 수 있다.

### technews-publisher

technews-publisher는 실제 뉴스 데이터 source다. sample agent는 write API를
사용하지 않고 read endpoint만 사용한다.

- `/api/issues/latest`
- `/api/issues/search`
- `/api/issues/{slug}`

TechNews 데이터는 매일 아침 전날 기준 GeekNews 요약으로 저장된다.
`technews-publisher/scripts/geeknews_publish.py`는 KST 기준 오늘에서 하루를 뺀
값을 `issue_date`로 사용하고, title을 `GeekNews 어제자 요약 - YYYY-MM-DD`로
만든다. 따라서 사용자가 “오늘 뉴스”를 물으면 agent는 최신 수집 issue를 기준으로
답하면서 오늘 수집분이 아직 없을 수 있음을 알려야 한다.

로컬 backend가 인증을 요구하는 경우 sample service는 다음 중 하나를 받는다.

```bash
TECHNEWS_AUTH_TOKEN=...
TECHNEWS_SESSION_COOKIE='idounai_session=...'
```

token이나 cookie는 trace에 그대로 저장하지 않도록 redaction 대상이다.

## 요청 payload와 응답

idounAIChat backend가 runtime으로 보내는 run 요청은 대략 아래 형태다.

```json
{
  "agent_id": "tech-radar",
  "input": "최근 AI Agent 관련 뉴스는 뭐야?",
  "session_instruction": "optional per-session guidance",
  "client_context": {
    "source": "legacy-web-ui"
  },
  "stream": true
}
```

runtime은 외부 adapter로 보낼 때 `agent_id`를 manifest의
`external_adapter.agent_id`로 맞춘다. 지금은 runtime agent id와 external
agent id가 둘 다 `tech-radar`지만, 필요하면 서로 다른 이름을 사용할 수 있다.

run이 성공하면 응답에는 `run_id`, `status`, `agent_id`, `trace_url`,
`output_text`가 포함된다. idounAIChat은 이 `run_id`로 trace를 조회한다.

## Trace import가 중요한 이유

sample server가 자체적으로 trace를 만들지만, 최종 조회 지점은 runtime이다.
runtime이 외부 trace를 import하지 않으면 idounAIChat, AgentOps Workbench,
eval, replay 관련 API가 run origin을 따로 알아야 한다.

현재 구조는 외부 실행 결과를 runtime store에 넣어서 다음 장점을 얻는다.

- UI는 항상 runtime의 `/v1/runs/{run_id}/trace`만 보면 된다.
- AgentOps Workbench와 eval API가 외부 agent 여부를 몰라도 된다.
- 실패나 latency를 runtime 기준으로 모아 볼 수 있다.
- 향후 다른 external agent도 같은 방식으로 붙일 수 있다.

## 성공 경로

성공 경로는 다음과 같다.

```text
runtime POST /v1/runs
-> manifest_loaded: tech-radar
-> external adapter POST http://127.0.0.1:8776/v1/runs
-> sample adapter policy_decision
-> search_tech_news tool_call
-> TechNews API read
-> sample final_answer
-> runtime import_trace
-> idounAIChat fetch trace
```

sample adapter의 final answer는 검색 결과를 근거 bullet로 묶어 만든다.
검색 결과가 없으면 합의된 no-evidence fallback을 반환한다.

## 실패 경로

외부 sample server가 죽었거나 timeout이 나면 runtime은 그냥 502만 반환하지
않는다. local failed run을 만들고 다음 step을 남긴다.

```text
external_adapter_call: failed
```

그리고 error detail에 `run_id`를 포함한다. idounAIChat은 이 `run_id`를
사용해 실패 trace를 자동 조회할 수 있다. 그래서 “왜 실패했는지”를 UI에서
바로 확인할 수 있다.

## LLM과 Gemini의 현재 위치

이 repository에는 Deep Agents graph를 만드는 `build_deep_agent` 경로가 있다.
Runtime-facing adapter는 `DeepPathRunner`를 통해 이 경로를 호출할 수 있다. 이
경로는 OpenAI 또는 Gemini provider 설정을 읽을 수 있다.

```bash
TECH_RADAR_DEEP_PATH_ENABLED=true
TECH_RADAR_LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
GEMINI_API_KEY=...
```

기본값에서는 안정적인 contract 검증을 위해 `TraceableRuntimeAdapter`가
deterministic light path로 fallback한다. `TECH_RADAR_DEEP_PATH_ENABLED=true`이고
요청이 deep candidate로 분류되면 Deep Agents path를 호출한다. 따라서 기본 smoke는
여전히 다음에 가깝다.

```text
runtime trace 계약 + TechNews 실제 read data + deterministic answer composition
```

Gemini key를 연결하면 Deep Agents/LLM 실행 경로를 live smoke하고, model call과
tool 결과가 trace에 어떻게 남는지 확장 검증하면 된다. Deep Agents graph가
LangChain callback을 내보내면 `deep_model_call_*`, `deep_tool_call_*` 형태의
route-specific trace step으로 bridge한다.

## 보안과 trace redaction

이 흐름에서 secret으로 취급해야 하는 값은 다음과 같다.

- `AGENT_SERVER_AUTH_TOKEN`
- `TECHNEWS_AUTH_TOKEN`
- `TECHNEWS_SESSION_COOKIE`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`

이 값들은 repo에 커밋하지 않는다. service wrapper나 private env 파일에서
읽고, trace에는 raw value가 남지 않도록 redaction한다.

## 운영 시 실행 단위

로컬 VM 기준으로 필요한 서비스는 보통 네 개다.

- idounAIChat frontend: `127.0.0.1:3000`
- idounAIChat backend: `127.0.0.1:8000`
- traceable-agent-runtime: `127.0.0.1:8765`
- traceable-deep-agents-sample: `127.0.0.1:8776`

TechNews backend는 `127.0.0.1:8010`에서 read API를 제공해야 한다.

## 다음 확장 포인트

- Gemini key 연결 후 Deep Agents live path smoke
- deterministic adapter와 LLM-backed adapter의 역할 경계 정리
- trace step에 model call 관련 step을 추가할지 결정
- Tech Radar 답변 품질 eval/regression suite 추가
- idounAIChat trace timeline UI polish
- 배포 환경에서 private env 파일과 systemd service 구성을 표준화
