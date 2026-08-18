# 평가 방법

## 고정 질문

1. 현재 작업의 목표는?
2. 현재 상태는?
3. 핵심 결정은?
4. 결정 근거는?
5. 실패한 접근은?
6. 실패 이유는?
7. 다음 작업은?

Baseline과 Proposed에 동일한 질문을 적용한다. 질문 목록은 `eval/fixed_questions.yaml`에 둔다.

## 비교 대상

- Baseline 1: recency truncation
- Baseline 2: generic summary
- Proposed: task-aware context preservation

## 측정 지표

- context reconstruction accuracy
- input tokens
- total tokens (분석 비용 포함)
- repeated questions
- repeated failed approaches
- task success

## reconstruction accuracy 채점 방법

압축된 working context만 제공한 상태에서 고정 질문에 답하게 한다.

원본 session log를 기준으로 답변을 채점한다. 질문별로 정답 또는 오답을 판정한다. 판정 근거를 기록한다.

1차 테스트는 수동 채점을 사용한다. 채점 기준은 `docs/decisions/`에 기록한다.

## token 측정 범위

측정 대상은 다음을 포함한다.

- Task Context Analysis 단계의 LLM 호출
- Reconstruction Test 단계의 LLM 호출

분석 비용을 제외하면 전체 비용을 과소 측정한다.

## 비용 계산

```
total_cost = input_tokens * input_price + output_tokens * output_price
```

모델별 가격은 설정 파일로 입력한다. 가격을 입력하지 않으면 비용은 계산하지 않고 token 수만 표기한다.

## 첫 번째 테스트 데이터

실제 개발 session 1개를 사용한다. 실패, 결정 변경, 오류, 수정이 포함된 session을 사용한다.

## 판정 기준

- reconstruction accuracy가 baseline보다 낮으면 실패로 판단한다.
- token이 baseline보다 늘어나면 목표를 달성하지 못한 것으로 판단한다.
- 두 조건을 모두 만족하는 경우에만 제안 방식을 채택한다.

## 확인되지 않음

- 고정 질문 7개가 충분한지. 질문 수 확장 여부는 실험 후 판단한다.
- 자동 채점 도입 여부.
