# Test Plan

This project uses focused tests to pin down the current routing and runtime
contracts before expanding answer quality.

## Route Matrix

`tests/test_complexity_router.py` owns the routing utterance matrix.

| Case | Utterance | Expected route | Expected reason |
| --- | --- | --- | --- |
| `light-simple-latest-news` | `오늘 뉴스중에 AI 내용 알려줘` | `light` | `single-step news lookup can use the light path` |
| `deep-synthesis-comparison-risk` | `AI agent 관련 뉴스들을 비교하고 투자 관점의 리스크와 전망을 분석해줘` | `deep` | `requires synthesis, comparison, or judgment` |
| `deep-evidence-report` | `AI agent 관련 근거와 출처를 자세히 보고서처럼 정리해줘` | `deep` | `asks for evidence expansion or report-style output` |
| `deep-semantic-exclusion` | `어제 기사중 AI가 아닌 기사만 조회해줄래` | `deep` | `requires semantic filtering or exclusion` |

## Runtime Adapter Coverage

`tests/test_runtime_adapter.py` verifies that route decisions survive the
runtime-facing path:

- light requests record `light_plan_created` and use deterministic TechNews
  tool execution.
- deep candidates fall back to light when the Deep Agents path is disabled.
- deep candidates call the deep runner when `deep_path_enabled=true`.
- semantic exclusion requests call the deep runner when enabled.
- deep runner failures record `deep_agent_failed` and fall back to light.
- frozen replay reuses supplied frozen tool output and records
  `tool_mode="frozen"`.
- ContextMesh and Tool Binding traces remain tenant-scoped.

## Deep Path Interface Coverage

`tests/test_deep_path.py` verifies the boundary between Deep Agents/LangChain
objects and the runtime response contract:

- runtime tenant, skill, tool binding, and scope context is passed into the Deep
  Agents input.
- LangChain model/tool callbacks become portable `deep_*` trace events.
- mapping-like graph responses are normalized instead of leaking Python object
  reprs into `output_text`.
- if the graph returns tool results but no final assistant answer, the adapter
  emits a readable fallback summary instead of raw messages.

## Replay Semantics

Current replay mode is tool replay, not model replay:

- `live` calls the tool/API again.
- `frozen` reuses the original recorded tool result.
- both modes may produce identical answers when the tool output is unchanged.

Future model replay should use a separate concept and UI label.

## Verification Commands

```bash
.venv/bin/pytest -q
.venv/bin/python scripts/check_runtime_contract.py
.venv/bin/python -m compileall src tests
git diff --check
```

## Remaining Test Gaps

- Browser-level AgentOps checks for route/model/tool-mode labels.
- Live Gemini answer-quality checks for deep route prompts.
- Structured filter/query-planner tests if semantic filtering moves out of the
  bootstrap marker router.
- Model replay tests if replay expands beyond tool result replay.
