# Runtime 인터페이스

이 sample은 `traceable-agent-runtime`의 run/trace shape를 따르며, runtime 뒤에서
external Agent Server adapter로 실행될 수 있습니다.

## 호환 Shape

local adapter는 다음 runtime schema를 맞춥니다.

- `RunCreateRequest`
- `RunResponse`
- `StepRecord`
- `RunTraceResponse`
- `AgentListResponse`

Trace URL은 runtime convention을 따릅니다.

```text
/v1/runs/{run_id}/trace
```

## External Adapter 방향

현재 통합 방향은 external adapter 우선입니다. Sample은 HTTP로 같은 run/trace
shape를 제공하고, `traceable-agent-runtime`은 agent manifest의
`external_adapter` 설정을 통해 sample을 호출합니다.

이 구조는 Deep Agents 동작이 바뀌어도 runtime core를 안정적으로 유지합니다.

## Agent Capability

Sample은 `GET /v1/agents`에서 `tech-radar` agent와 capability를 광고합니다.

```json
{
  "agents": [
    {
      "id": "tech-radar",
      "capabilities": {
        "replay": {
          "live": true,
          "frozen": true,
          "frozen_tool_result_schema": "traceable-agent-runtime.frozen-tool-result.v1"
        }
      }
    }
  ]
}
```

Runtime은 이 discovery 응답과 manifest의 `external_adapter.allowed_replay_modes`
allowlist를 함께 보고 external frozen replay를 허용할지 결정합니다.

## Replay Request

Replay는 별도 endpoint가 아니라 일반 `POST /v1/runs` request에 optional
`replay` object를 붙이는 방식입니다.

```json
{
  "input": "AI Agent tracing",
  "agent_id": "tech-radar",
  "replay": {
    "of_run_id": "run_original",
    "tool_mode": "frozen",
    "strict_tool_input_match": true,
    "frozen_tool_results": [
      {
        "tool_name": "search_tech_news",
        "tool_input": {
          "query": "AI Agent tracing",
          "limit": 3
        },
        "result": {
          "tool_name": "search_tech_news",
          "status": "success",
          "output": {},
          "error": null
        }
      }
    ]
  }
}
```

`tool_mode="frozen"`이면 sample은 matching frozen tool result를 먼저 찾고,
일치하면 live TechNews tool을 호출하지 않습니다.

## TechNews Tools

Sample은 read-only TechNews tool을 제공합니다.

- `search_tech_news`: published TechNews issue 검색
- `get_latest_tech_news`: 최신 published daily issue 조회
- `get_tech_news_article`: slug 기준 단일 issue 조회

`technews-publisher/scripts/geeknews_publish.py`는 KST 기준 오늘 날짜에서 하루를
뺀 값을 `issue_date`로 만들고, `GeekNews 어제자 요약 - YYYY-MM-DD` 형태의
title을 생성합니다. 사용자가 “오늘 뉴스”를 물으면 runtime-compatible adapter는
`get_latest_tech_news`를 호출하고, 오늘 수집분이 아직 없을 수 있다는 freshness
note를 답변 앞에 붙입니다.

## Step Types

Adapter는 `traceable-agent-runtime`이 쓰는 runtime-style step name을 기록합니다.

```text
replay_started
run_started
manifest_loaded
prompt_composed
policy_decision
tool_call_started
tool_call_completed
final_answer
run_completed
replay_completed
run_failed
```

Tool 경로에서는 `policy_decision`이 `tool_call_started`보다 먼저 나와야 합니다.
Frozen replay의 tool step에는 `tool_mode: "frozen"`이 기록됩니다.

## 현재 Boundary

이 sample은 native `traceable-agent-runtime` plugin이 아닙니다. 별도 service로
유지되고, runtime이 `agents/tech-radar.yaml` 같은 manifest를 통해 실행을
위임합니다. Runtime은 external trace를 자기 trace store로 import하므로 trace
lookup, replay, eval, UI 경로는 runtime API 위에 유지됩니다.

## Contract Check

이 repository가 `traceable-agent-runtime`과 같은 부모 폴더에 있으면 다음을
실행합니다.

```bash
python scripts/check_runtime_contract.py
```

스크립트는 adapter output을 실제 runtime Pydantic schema에 맞춰 검증하고,
정책 판단이 tool 실행보다 먼저 기록되는지 확인합니다.
