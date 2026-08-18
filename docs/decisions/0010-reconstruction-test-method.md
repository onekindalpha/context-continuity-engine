# 0010. reconstruction test 판정 방법

## 상태

확정(근사)

## 결정

고정된 7개 질문(docs/evaluation.md)에 대해, 각 context 방식이 정답 turn의 내용을 포함하는지를 기계적으로 판정한다. LLM으로 의미를 판정하지 않는다.

방법:
1. 사람이 만든 예시(`task_context_analysis.example.json`)를 정답으로 삼는다. 이 예시의 category와 depends_on으로 질문별 정답 turn_id 집합을 만든다.
2. "결정 근거는?", "실패 이유는?"은 해당 decision/failure 항목 자신이 아니라 그 항목이 depends_on으로 참조하는 항목의 turn을 정답으로 본다.
3. 각 context 방식이 그 turn_id를 즉시 포함하면(KEEP/COMPRESS, 또는 recency truncation의 포함 범위) PASS, 외부 보관(EXTERNALIZE)에만 있으면 RETRIEVABLE, 둘 다 아니면 FAIL로 판정한다.

`src/reconstruction_test.py`에 구현했다.

## 이유

이 환경에 LLM API 자격증명이 없다(0006과 동일한 제약). 사람이 매번 7개 질문 × 3개 방식을 눈으로 읽고 판정하는 것은 재현 가능하지 않다. turn_id 포함 여부는 기계적으로 재현 가능한 근사치다.

## 알려진 한계

- "turn 내용이 context에 있다"는 것과 "그 내용으로 질문에 만족스럽게 답할 수 있다"는 것은 다르다. 이 test는 전자만 확인한다.
- "결정 근거"/"실패 이유"를 depends_on 관계로 근사한 것은 검증되지 않은 가정이다. 실제로는 근거가 같은 turn 안에 있을 수도 있고, depends_on으로 연결 안 된 다른 turn에 있을 수도 있다.
- 정답 자체가 사람이 만든 예시 하나에 의존한다. 그 예시가 놓친 정보는 이 test에서도 정답으로 잡히지 않는다.

## 재검토 조건

LLM 자격증명이 생기면, 같은 7개 질문에 대해 LLM이 실제로 답변을 생성하고 그 답변의 사실성을 원본과 대조하는 방식으로 교체를 검토한다.
