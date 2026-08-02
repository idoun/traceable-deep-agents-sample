# 테스트 계획

이 프로젝트는 답변 품질을 넓히기 전에 현재 routing과 runtime contract를
작은 테스트로 먼저 고정합니다.

## Route Matrix

`tests/test_complexity_router.py`가 routing 발화 matrix를 소유합니다.

| Case | 발화 | 기대 route | 기대 reason |
| --- | --- | --- | --- |
| `light-simple-latest-news` | `오늘 뉴스중에 AI 내용 알려줘` | `light` | `single-step news lookup can use the light path` |
| `deep-synthesis-comparison-risk` | `AI agent 관련 뉴스들을 비교하고 투자 관점의 리스크와 전망을 분석해줘` | `deep` | `requires synthesis, comparison, or judgment` |
| `deep-evidence-report` | `AI agent 관련 근거와 출처를 자세히 보고서처럼 정리해줘` | `deep` | `asks for evidence expansion or report-style output` |
| `deep-semantic-exclusion` | `어제 기사중 AI가 아닌 기사만 조회해줄래` | `deep` | `requires semantic filtering or exclusion` |

## Runtime Adapter Coverage

`tests/test_runtime_adapter.py`는 route decision이 runtime-facing path에서도
유지되는지 검증합니다.

- light request는 `light_plan_created`를 기록하고 deterministic TechNews tool
  실행을 사용합니다.
- deep candidate는 Deep Agents path가 꺼져 있으면 light로 fallback합니다.
- `deep_path_enabled=true`이면 deep candidate가 deep runner를 호출합니다.
- semantic exclusion request는 deep path가 켜져 있을 때 deep runner를 호출합니다.
- deep runner 실패는 `deep_agent_failed`를 기록하고 light로 fallback합니다.
- frozen replay는 전달받은 frozen tool output을 재사용하고
  `tool_mode="frozen"`을 기록합니다.
- ContextMesh와 Tool Binding trace는 tenant별로 격리됩니다.

## Deep Path Interface Coverage

`tests/test_deep_path.py`는 Deep Agents/LangChain 객체와 runtime response contract
사이의 boundary를 검증합니다.

- runtime tenant, skill, tool binding, scope context가 Deep Agents input에
  전달됩니다.
- LangChain model/tool callback은 portable `deep_*` trace event로 변환됩니다.
- mapping-like graph response가 Python object repr로 `output_text`에 새지 않도록
  normalize합니다.
- graph가 tool result까지만 반환하고 최종 assistant answer를 반환하지 않으면,
  Deep Agents path에 최종 synthesis를 한 번 더 요청합니다. 이 retry에도 최종
  assistant answer가 없을 때만 읽을 수 있는 fallback summary를 반환합니다.

## Replay Semantics

현재 replay mode는 model replay가 아니라 tool replay입니다.

- `live`는 tool/API를 다시 호출합니다.
- `frozen`은 원본 trace에 저장된 tool result를 재사용합니다.
- tool output이 같으면 두 mode의 answer가 동일할 수 있습니다.

나중에 model replay를 추가한다면 별도 개념과 UI label이 필요합니다.

## Verification Commands

```bash
.venv/bin/pytest -q
.venv/bin/python scripts/check_runtime_contract.py
.venv/bin/python -m compileall src tests
git diff --check
```

## Remaining Test Gaps

- AgentOps에서 route/model/tool-mode label을 확인하는 browser-level test
- deep route prompt에 대한 live Gemini 답변 품질 검증
- fake graph response가 아닌 live provider 기준 synthesis retry path 검증
- semantic filtering을 bootstrap marker router 밖으로 옮길 경우 structured
  filter/query-planner test
- replay가 tool result replay를 넘어 model replay까지 확장될 경우 model replay
  test
