# 동일 token budget에서의 reconstruction 비교

fixture: `groq_model_migration_session`, turn 수: 20

코드 실행 결과다. 실행: `python3 experiments/budget_reconstruction/run_budget_experiment.py`

지표: **content recall**(정답 turn의 내용어가 context 텍스트에 실제로 남아있는 비율). 기존 `src/reconstruction_test.py`의 turn_id 포함 여부 지표는 generic summary가 turn을 절대 버리지 않기 때문에 어떤 budget에서도 항상 7/7이 나와 비교에 쓸 수 없다 — 그 이유는 `content_recall.py`에 기록했다.

| budget(token) | generic 실제 token | generic mean recall | generic PASS | CCE 실제 token | CCE mean recall | CCE PASS |
|---|---|---|---|---|---|---|
| 500 | 500 | 0.67 | 5/7 | 344 | 0.666 | 3/7 |
| 400 | 400 | 0.602 | 3/7 | 344 | 0.666 | 3/7 |
| 326 | 326 | 0.53 | 3/7 | 324 | 0.641 | 3/7 |
| 260 | 260 | 0.429 | 3/7 | 256 | 0.584 | 3/7 |
| 200 | 195 | 0.311 | 1/7 | 193 | 0.509 | 3/7 |
| 150 | 149 | 0.204 | 0/7 | 150 | 0.426 | 2/7 |
| 100 | 98 | 0.095 | 0/7 | 93 | 0.363 | 2/7 |

## 질문별 상세 (budget=326, generic summary의 현재 크기 기준)

| 질문 | generic recall | generic 판정 | CCE recall | CCE 판정 |
|---|---|---|---|---|
| 현재 작업의 목표는? | 0.917 | PASS | 1.0 | PASS |
| 현재 상태는? | 0.407 | PARTIAL | 0.441 | PARTIAL |
| 핵심 결정은? | 0.314 | PARTIAL | 0.367 | PARTIAL |
| 결정 근거는? | 0.418 | PARTIAL | 0.461 | PARTIAL |
| 실패한 접근은? | 0.605 | PASS | 0.789 | PASS |
| 실패 이유는? | 0.3 | PARTIAL | 0.429 | PARTIAL |
| 다음 작업은? | 0.75 | PASS | 1.0 | PASS |

## 한계 (정직하게)

- content recall은 내용어가 **남아있는지**를 보는 것이지 의미를 이해했는지가 아니다. 여전히 근사 지표다.
- 불용어 목록과 PASS 임계값(0.5)은 사람이 정한 값이다. 값이 바뀌면 절대 점수는 바뀐다 — 그래서 이 실험은 같은 지표로 두 방식을 비교하는 용도로만 읽어야 한다.
- fixture 1개 기준이다. `docs/results.md`의 일반화 한계가 그대로 적용된다.
- 결과가 CCE에 불리하게 나오면 그대로 기록한다(AGENTS.md 규칙 7).