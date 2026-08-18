# baseline vs 제안 방식 비교 결과

fixture: `groq_model_migration_session`, turn 수: 20

코드 실행 결과다. 사람이 손으로 채운 값이 아니다. 실행: `python3 scripts/run_comparison.py`

## token 사용량

| 방식 | context token | 비고 |
|---|---|---|
| original_full_session | 1311 | analysis 단계 추가 token 없음(규칙 기반, LLM 미사용) |
| baseline_recency_truncation | 395 | analysis 단계 추가 token 없음(규칙 기반, LLM 미사용) |
| baseline_generic_summary | 326 | analysis 단계 추가 token 없음(규칙 기반, LLM 미사용) |
| proposed_working_context | 462 | analysis 단계 추가 token 없음(규칙 기반, LLM 미사용) |

원본 전체 대비 감소율:

- baseline_recency_truncation: 395/1311 token (69.9% 감소)
- baseline_generic_summary: 326/1311 token (75.1% 감소)
- proposed_working_context: 462/1311 token (64.8% 감소)

token 수는 근사치다(docs/decisions/0007). 절대값이 아니라 방식 간 상대 비교로만 읽는다.

## reconstruction test (7개 질문)

PASS: 즉시 답변 가능(원문 또는 요약이 context에 있음) / RETRIEVABLE: 외부 보관분을 조회하면 답변 가능 / FAIL: 어디에도 없음 / NO_GROUND_TRUTH: 사람이 만든 예시에도 해당 category 항목이 없음

| 질문 | baseline_recency_truncation | baseline_generic_summary | proposed_working_context |
|---|---|---|---|
| 현재 작업의 목표는? | FAIL | PASS | FAIL |
| 현재 상태는? | PASS | PASS | PASS |
| 핵심 결정은? | PASS | PASS | PASS |
| 결정 근거는? | PASS | PASS | PASS |
| 실패한 접근은? | PASS | PASS | PASS |
| 실패 이유는? | PASS | PASS | PASS |
| 다음 작업은? | PASS | PASS | PASS |

### 방식별 요약

| 방식 | PASS | RETRIEVABLE | FAIL | NO_GROUND_TRUTH |
|---|---|---|---|---|
| baseline_recency_truncation | 6 | 0 | 1 | 0 |
| baseline_generic_summary | 7 | 0 | 0 | 0 |
| proposed_working_context | 6 | 0 | 1 | 0 |

## 제안 방식의 retention_action 분포

- KEEP: 6
- COMPRESS: 4
- EXTERNALIZE: 0
- DISCARD: 4

## 관찰된 한계

- 제안 방식의 category 추출은 규칙 기반이며 정확도가 낮다(0006 문서 기준 turn 단위 일치 7/18). goal/decision category는 이 fixture에서 자동 추출 결과에 전혀 없다 — 그 category가 필요한 질문은 ContextItem 자체가 없어 FAIL이 나올 수 있다.
- reconstruction test는 '내용이 context에 있는지'만 확인한다. 그 내용으로 실제 질문에 사람이 만족스럽게 답할 수 있는지는 확인하지 않는다(0010 문서 참조).
- baseline_generic_summary는 모든 turn을 자르기만 하고 버리지 않으므로 reconstruction test 상 FAIL이 거의 나오지 않는다 — 대신 token 절감 효과가 제안 방식보다 작을 수 있다. token 표와 함께 봐야 한다.
