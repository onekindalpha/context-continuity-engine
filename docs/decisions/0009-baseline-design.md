# 0009. baseline 설계

## 상태

확정

## 결정

baseline을 두 가지로 둔다.

1. recency truncation: 최근 N개 turn만 verbatim으로 남기고 나머지는 버린다. N=6.
2. generic summary: 모든 turn을 동일한 길이(40자)로 잘라서 남긴다. task_relevance/importance를 계산하지 않는다.

둘 다 `src/baseline.py`에 구현했다.

## 이유

두 방식은 LLM 없이 흔히 쓰이는 실제 관행을 대표한다. recency truncation은 sliding-window 방식 채팅 컨텍스트 관리의 기본형이다. generic summary는 category/중요도 구분 없이 일괄로 길이만 줄이는 방식이다. 제안 방식(task_relevance/importance 기반 KEEP/COMPRESS/EXTERNALIZE/DISCARD)이 실제로 이 두 방식보다 나은지 비교해야 "context는 남기고 token은 줄인다"는 주장을 검증할 수 있다.

N=6, 40자라는 값은 이 fixture(20 turn, 두 episode)에서 제안 방식의 KEEP 대상 turn 수(현재 episode, turn 14~19, 6개)와 맞춘 것이다. baseline과 제안 방식이 "최근 것을 온전히 남긴다"는 점에서는 동일한 조건에서 시작하도록 하기 위함이다.

## 알려진 한계

- N=6, 40자는 이 fixture 하나에 맞춘 값이다. 다른 세션에서는 다른 값이 적절할 수 있다 — 일반화되지 않았다.
- generic summary는 잘린 지점을 고려하지 않는다. 문장 중간에서 잘려도 그대로 40자에서 끊는다.
