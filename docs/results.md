# 실행 결과

fixture `examples/groq_model_migration_session`(실제 개발 세션 20turn) 기준. 실행: `python3 scripts/run_comparison.py`. 원본 수치는 `examples/groq_model_migration_session/comparison_result.md`, `.json`.

## 요약

| 방식 | context token | 원본 대비 감소율 | reconstruction PASS(7문항 중) |
|---|---|---|---|
| 원본 전체 | 1311 | - | - |
| baseline: recency truncation(최근 6 turn) | 395 | 69.9% | 6 |
| baseline: generic summary(turn당 40자 절삭) | 326 | 75.1% | 7 |
| 제안: Working Context(task_relevance 기반 KEEP/COMPRESS/EXTERNALIZE/DISCARD) | 581 | 55.7% | 6 |

token 수는 근사치다(`docs/decisions/0007`). 절대값이 아니라 방식 간 상대 비교로 읽는다.

## 판단

이번 fixture, 이번 실행 기준으로 제안 방식은 두 baseline보다 우위를 보이지 않았다. token은 baseline_recency_truncation보다 47% 더 썼고, reconstruction PASS 수는 baseline_generic_summary보다 1개 적다.

원인을 코드 수준에서 추적했다.

1. 규칙 기반 추출기(`src/context_analysis.py`)가 이 fixture에서 goal/decision category 항목을 하나도 만들지 않았다(`docs/decisions/0006` 관찰된 한계와 동일). "현재 작업의 목표는?" 질문은 정답 turn(turn 2)에 대응하는 ContextItem 자체가 없어 baseline_recency_truncation과 제안 방식 둘 다 FAIL이다 — 이 부분은 baseline과 동률이라 이번 결과의 열세 원인이 아니다.
2. COMPRESS 항목의 요약 길이 상한(`SUMMARY_MAX_CHARS=120`, `context_analysis.py`)이 baseline_generic_summary의 절삭 길이(40자)보다 길다. 제안 방식의 KEEP 대상(현재 episode, turn 14~19)은 baseline_recency_truncation의 유지 대상과 동일한데, 여기에 COMPRESS 항목 4개(최대 120자씩)가 더해지면서 token이 baseline_recency_truncation보다 늘었다. 그런데 이 COMPRESS 항목들은 이번 7개 질문의 정답 turn과 겹치지 않아 reconstruction PASS 수를 늘리는 데 기여하지 못했다 — token만 더 쓰고 이번 측정에서는 이득이 없었다.

## 다음 개선 과제

- `SUMMARY_MAX_CHARS`를 baseline_generic_summary 수준(40자대)으로 낮추고 재측정한다. COMPRESS의 목적("의미만 압축 보존")에 비해 현재 값이 과하게 길다.
- 규칙 기반 추출기가 goal/decision category를 놓치는 문제를 LLM 기반 추출기로 교체해 개선한다(`docs/decisions/0006` 재검토 조건).
- fixture를 하나 더 늘려 결과가 이 세션에 한정된 것인지 확인한다. 지금은 20turn 세션 1개로만 측정했다.

## 정직성 관련 메모

이 문서는 baseline 대비 제안 방식이 이긴다는 결론을 내리지 않는다. AGENTS.md 규칙(뒷받침되지 않는 성능 수치 금지)에 따라 측정된 그대로 기록했다. 결과보고서에 이 프로젝트를 소개할 때도 "token을 줄이면서 재구성 가능성을 확보한다"는 주장 대신, "규칙 기반 baseline에서 시작해 실제로 측정 가능한 형태로 만들었고, 현재 baseline 대비 우위를 아직 입증하지 못했다는 것을 코드로 확인했다"는 진행 상태로 서술한다.
