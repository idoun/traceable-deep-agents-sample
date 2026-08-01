# Architecture

이 sample은 `traceable-agent-runtime`을 위한 external Agent Server adapter입니다.
Runtime은 public API, trace store, replay, eval, Workbench 연동을 소유하고,
sample은 Tech Radar 동작과 read-only TechNews tool을 소유합니다.

Standalone diagram은 [`architecture.html`](architecture.html)에서 볼 수 있습니다.

## Runtime Boundary

`traceable-agent-runtime`은 public Agent Server API를 제공합니다.

- `GET /v1/agents`
- `POST /v1/runs`
- `POST /v1/runs/{run_id}/replay`
- `GET /v1/runs/{run_id}/trace`

`agent_id=tech-radar` 요청이 오면 runtime은
`traceable-agent-runtime/agents/tech-radar.yaml`을 읽고, `external_adapter`
설정에 따라 실행을 이 sample service에 위임합니다.

## Sample Boundary

`traceable-deep-agents-sample`은 runtime-compatible external service를 제공합니다.

- `GET /health`
- `GET /v1/agents`
- `POST /v1/runs`
- `GET /v1/runs/{run_id}/trace`

Sample은 `GET /v1/agents`에서 capability를 광고합니다. Runtime은 이 discovery
응답과 자기 manifest allowlist를 함께 확인한 뒤 external frozen replay를 허용할지
결정합니다.

## Tool Layer

Sample에는 세 개의 read-only TechNews tool이 있습니다.

- `search_tech_news`
- `get_latest_tech_news`
- `get_tech_news_article`

Deterministic runtime adapter는 현재 다음처럼 선택합니다.

- 오늘 뉴스를 묻는 질문: `get_latest_tech_news`
- 일반 근거 검색: `search_tech_news`

Deep Agents 경로도 같은 tool을 model provider에 노출합니다.

## Freshness

`technews-publisher`는 매일 아침 전날 기준 GeekNews 요약을 저장합니다. 사용자가
오늘 뉴스를 물으면 sample은 최신 수집 issue를 기준으로 답하고, 오늘 수집분이
아직 없을 수 있음을 먼저 말합니다.

## Replay

Replay는 `RunCreateRequest.replay`로 표현됩니다. Live replay는 tool을 다시
실행합니다. Frozen replay는 original trace에서 추출한 frozen tool result를 받아
matching output을 재사용하고 live TechNews tool 호출을 건너뜁니다.
