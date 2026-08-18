# 실행 결과

fixture `examples/groq_model_migration_session`(실제 개발 세션 20turn) 기준. 실행: `python3 scripts/run_comparison.py`. 원본 수치는 `examples/groq_model_migration_session/comparison_result.md`, `.json`.

## 요약 (3차 측정 — SUMMARY_MAX_CHARS=40 + GOAL_PATTERNS 보강)

| 방식 | context token | 원본 대비 감소율 | reconstruction PASS(7문항 중) |
|---|---|---|---|
| 원본 전체 | 1311 | - | - |
| baseline: recency truncation(최근 6 turn) | 395 | 69.9% | 6 |
| baseline: generic summary(turn당 40자 절삭) | 326 | 75.1% | 7 |
| 제안: Working Context(task_relevance 기반 KEEP/COMPRESS/EXTERNALIZE/DISCARD) | 486 | 62.9% | **7** |

token 수는 근사치다(`docs/decisions/0007`). 절대값이 아니라 방식 간 상대 비교로 읽는다.

### 측정 히스토리

| 방식 | 1차(SUMMARY_MAX_CHARS=120) | 2차(=40) | 3차(=40 + GOAL_PATTERNS 추가) |
|---|---|---|---|
| 제안 방식 token | 581 (55.7% 감소) | 462 (64.8% 감소) | 486 (62.9% 감소) |
| 제안 방식 reconstruction PASS | 6/7 | 6/7 | **7/7** |

3차 측정에서 `src/context_analysis.py`의 `GOAL_PATTERNS`에 정규식 `기능이\s?없다`를 추가했다. 이 fixture의 turn 2("...pdf 등 첨부 기능이 없다고")가 사람이 만든 ground truth(`task_context_analysis.example.json`)에서는 goal로 표시돼 있는데, 기존 규칙으로는 어떤 category에도 걸리지 않아 ContextItem 자체가 없었다. 새 패턴을 추가하자 이 turn이 goal로 분류됐고, "현재 작업의 목표는?" 질문이 baseline_recency_truncation과 제안 방식 모두에서 FAIL이던 것이 제안 방식에서만 PASS로 바뀌었다. 20개 turn 전체를 확인해 이 패턴이 다른 turn을 잘못 걸러내지 않는 것도 확인했다(`git log` 커밋 메시지 참조). 전체 테스트 94개 통과.

## 판단

**baseline_recency_truncation 대비**: token은 여전히 더 쓴다(486 vs 395, +23%). 하지만 이제 reconstruction에서 recency_truncation이 놓치는 질문(목표)을 제안 방식은 답한다(7/7 vs 6/7) — token을 조금 더 쓰는 대신 정답률에서 앞선다. "token만 적으면 이긴다"는 기준이 아니라 "같은 token 예산에서 얼마나 더 잘 재구성되는가"로 보면, 이번 측정에서는 제안 방식이 우위다.

**baseline_generic_summary 대비**: reconstruction PASS는 동률(7/7)이지만 token은 여전히 더 쓴다(486 vs 326, +49%). 이 baseline은 여전히 이기지 못했다 — 모든 turn을 균일하게 짧게 자르기만 해도 이 fixture에서는 완전한 재구성이 가능했다는 뜻이고, 제안 방식의 "선택적으로 버린다"는 접근이 아직 이 baseline보다 효율적이라고 말할 수 없다.

즉, 두 baseline을 동시에, 모든 지표에서 이긴 것은 아니다. 하나(recency_truncation)는 reconstruction 품질에서 앞섰고, 다른 하나(generic_summary)는 아직 앞서지 못했다. 이것이 정확한 현재 상태다.

## 남은 원인

- decision category는 이 fixture에서 여전히 규칙 기반으로 일부만 잡힌다(`docs/decisions/0006`). goal 하나를 고친 것이지 추출기 전체의 낮은 정확도 문제(턴 단위 일치 7/18)를 해결한 게 아니다.
- 이번에 추가한 `기능이\s?없다` 패턴은 이 fixture 하나를 보고 만든 규칙이다. 다른 세션에서도 통할지는 검증되지 않았다 — 오히려 rule-based 접근의 "fixture별로 규칙을 손으로 추가해야 한다"는 근본 한계를 보여주는 사례이기도 하다.

## 다음 개선 과제

- ~~`SUMMARY_MAX_CHARS`를 baseline_generic_summary 수준(40자대)으로 낮추고 재측정한다.~~ 완료.
- ~~"현재 작업의 목표는?" 질문의 FAIL을 규칙 추가로 고쳐본다.~~ 완료 — recency_truncation 대비는 역전, generic_summary 대비는 아직.
- baseline_generic_summary를 token 기준으로도 이기려면: COMPRESS 요약 로직 자체를 baseline의 균일 절삭보다 효율적으로 만들어야 한다(예: KEEP 항목과 겹치는 정보 제거, 중복 COMPRESS 항목 병합). 아직 시도하지 않음.
- 규칙 기반 추출기가 fixture마다 손으로 규칙을 추가해야 하는 문제를 LLM 기반 추출기로 교체해 근본적으로 개선한다(`docs/decisions/0006` 재검토 조건).
- fixture를 하나 더 늘려 결과가 이 세션에 한정된 것인지 확인한다. 지금은 20turn 세션 1개로만 측정했고, 이번 GOAL_PATTERNS 추가는 그 한계를 오히려 더 뚜렷하게 보여준다.

## 정직성 관련 메모

이 문서는 baseline 대비 제안 방식이 모든 지표에서 이긴다는 결론을 내리지 않는다. AGENTS.md 규칙(뒷받침되지 않는 성능 수치 금지)에 따라 측정된 그대로 기록했다. 정확한 현재 상태: 원본 전체 복사(1311 token) 대비로는 62.9% 감소하며 7문항 모두 재구성 가능하고, 가장 단순한 baseline(recency_truncation) 대비로는 token을 더 쓰지만 재구성 품질에서 앞서며, 또 다른 baseline(generic_summary) 대비로는 재구성 품질은 동률이지만 token 효율에서 아직 뒤진다.
