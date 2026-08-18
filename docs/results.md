# 실행 결과

fixture `examples/groq_model_migration_session`(실제 개발 세션 20turn) 기준. 실행: `python3 scripts/run_comparison.py`. 원본 수치는 `examples/groq_model_migration_session/comparison_result.md`, `.json`.

## 요약 (SUMMARY_MAX_CHARS=40, 2차 측정)

| 방식 | context token | 원본 대비 감소율 | reconstruction PASS(7문항 중) |
|---|---|---|---|
| 원본 전체 | 1311 | - | - |
| baseline: recency truncation(최근 6 turn) | 395 | 69.9% | 6 |
| baseline: generic summary(turn당 40자 절삭) | 326 | 75.1% | 7 |
| 제안: Working Context(task_relevance 기반 KEEP/COMPRESS/EXTERNALIZE/DISCARD) | 462 | 64.8% | 6 |

token 수는 근사치다(`docs/decisions/0007`). 절대값이 아니라 방식 간 상대 비교로 읽는다.

### 1차 측정과 비교 (SUMMARY_MAX_CHARS=120 → 40)

| 방식 | 1차(120자) | 2차(40자) |
|---|---|---|
| 제안 방식 token | 581 (55.7% 감소) | 462 (64.8% 감소) |
| 제안 방식 reconstruction PASS | 6 | 6 (동일) |

`docs/decisions/0009` 이후 "다음 개선 과제"로 남겨뒀던 `SUMMARY_MAX_CHARS` 축소(120→40, `src/context_analysis.py`)를 실제로 적용하고 재측정했다. `scripts/run_context_analysis.py`로 fixture의 `context_analysis.json`을 재생성한 뒤 `scripts/run_comparison.py`를 다시 돌린 결과다(코드 변경, 커밋 예정).

## 판단

token 격차는 줄었지만(baseline_recency_truncation 대비 +47% → +17%, baseline_generic_summary 대비 +78% → +42%), 두 baseline보다는 여전히 더 많은 token을 쓴다. reconstruction PASS 수도 바뀌지 않았다 — COMPRESS 요약을 줄인 항목들이 애초에 7개 질문의 정답 turn과 겹치지 않기 때문에(아래 원인 2 참조), 요약 길이를 줄여도 PASS/FAIL에는 영향이 없었다.

원인을 코드 수준에서 추적했다.

1. 규칙 기반 추출기(`src/context_analysis.py`)가 이 fixture에서 goal/decision category 항목을 하나도 만들지 않았다(`docs/decisions/0006` 관찰된 한계와 동일). "현재 작업의 목표는?" 질문은 정답 turn(turn 2)에 대응하는 ContextItem 자체가 없어 baseline_recency_truncation과 제안 방식 둘 다 FAIL이다 — 이 부분은 baseline과 동률이라 이번 결과의 열세 원인이 아니다.
2. COMPRESS 항목 4개는 이번 7개 질문의 정답 turn과 겹치지 않는다. 요약 길이(`SUMMARY_MAX_CHARS`)를 120→40으로 줄이면 token은 줄지만(그래서 baseline과의 격차는 좁혀졌다), reconstruction PASS 수는 애초에 이 COMPRESS 항목들이 기여하는 게 아니었으므로 그대로다. 즉 이번 변경은 "쓸모없이 많이 쓰던 token"을 줄인 것이지, "부족했던 정보"를 보충한 게 아니다 — 근본 원인은 여전히 1번(goal/decision 추출 누락)이다.

## 다음 개선 과제

- ~~`SUMMARY_MAX_CHARS`를 baseline_generic_summary 수준(40자대)으로 낮추고 재측정한다.~~ 완료 (120→40, 위 결과 참조). token 격차는 줄었으나 baseline을 앞서지는 못했다.
- 규칙 기반 추출기가 goal/decision category를 놓치는 문제를 LLM 기반 추출기로 교체해 개선한다(`docs/decisions/0006` 재검토 조건). 이번 측정으로 이 문제가 남은 열세의 근본 원인이라는 것이 더 뚜렷해졌다.
- fixture를 하나 더 늘려 결과가 이 세션에 한정된 것인지 확인한다. 지금은 20turn 세션 1개로만 측정했다.

## 정직성 관련 메모

이 문서는 baseline 대비 제안 방식이 이긴다는 결론을 내리지 않는다. AGENTS.md 규칙(뒷받침되지 않는 성능 수치 금지)에 따라 측정된 그대로 기록했다. `SUMMARY_MAX_CHARS` 조정으로 격차는 좁혔지만(baseline_recency_truncation 대비 +47%→+17%) 여전히 두 baseline보다 token을 더 쓴다. 결과보고서에 이 프로젝트를 소개할 때도 "token을 줄이면서 재구성 가능성을 확보한다"는 주장 대신, "규칙 기반 baseline에서 시작해 실제로 측정 가능한 형태로 만들었고, 개선을 한 차례 시도해 격차를 좁혔지만 아직 baseline 대비 우위를 입증하지 못했다는 것을 코드로 확인했다"는 진행 상태로 서술한다.
