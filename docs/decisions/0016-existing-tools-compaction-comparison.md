# 0016. 기존 도구의 압축 방식과 비교 (외부 근거)

## 상태

확정

## 배경

`docs/results.md`와 결과보고서에 "기존 코딩 에이전트의 압축 기능은 recency 기준 또는
검증되지 않은 요약 기준으로 동작하며, 압축 전후 상태 복원 정확도를 측정한 사례가
확인되지 않는다"는 주장이 있었는데, 실제로 웹 검색으로 근거를 확인하지 않은 상태로
적혀 있었다. 이 문서는 그 주장을 실제 1차 자료로 검증한 기록이다.

## 확인한 사실 (2026-08, Anthropic 공식 문서 기준)

Anthropic의 공식 Claude Developer Platform cookbook("Automatic context compaction")에
따르면, 공식 compaction 방식은 다음과 같이 동작한다:

1. 토큰 사용량이 임계값을 넘으면 "요약을 만들어 달라"는 요청을 user turn으로 주입한다.
2. Claude 자신이 `<summary></summary>` 태그로 감싼 요약을 생성한다.
3. 원본 대화 기록을 지우고 그 요약으로 통째로 교체한다.

즉 **규칙 기반도, 단순 recency truncation도 아니라 LLM 자신에게 요약을 맡기는 방식**이다
(원래 "recency 기준"이라고만 적었던 건 부정확했다 - 정정한다).

공개된 실제 수치: 5개 티켓 처리 워크플로(35회 tool call) 기준 204,416 → 82,171 token
(58.6% 감소). 이 수치는 실제로 공개돼 있다.

**공개되지 않은 것**: 이 문서는 "요약은 필연적으로 일부 정보를 잃는다"고 스스로 인정하면서도
(원문: "Summaries inherently lose some information."), 그 정보 손실을 정량적으로 측정한
수치나 baseline 대비 비교, reconstruction 정확도 벤치마크는 어디에도 공개하지 않는다.
성공 여부의 근거는 "해당 예시에서 티켓 5개가 다 처리됐다"는 정성적 확인뿐이다.

## 이 프로젝트와의 차이 및 의의

이 프로젝트가 실제로 다른 점은 압축 알고리즘 자체의 우수성이 아니라(baseline_generic_summary
대비 token에서 아직 뒤진다 - `docs/results.md`), **압축 전후 상태 복원 정확도를 baseline과
비교해서 수치로 측정하고, 그 측정 코드와 결과(유리하든 불리하든)를 공개한다는 점**이다.
공식 문서를 포함해 확인된 범위 안에서는, 이런 정량적 reconstruction 벤치마크를 공개한
사례를 찾지 못했다.

## 정정 사항

기존 문서/보고서의 "recency 기준 또는 검증되지 않은 요약 기준"이라는 표현 중 "recency
기준"은 최소한 Anthropic 공식 compaction에는 해당하지 않는다. "검증되지 않은 요약 기준"이
정확한 설명이다 - LLM 요약이되, 정확도가 공개적으로 검증되지 않았다는 뜻으로 표현을
정리했다.

## 출처

- Anthropic, "Automatic context compaction", Claude Developer Platform cookbook
  (platform.claude.com/cookbook/tool-use-automatic-context-compaction), 2026-08 확인.

## 알려진 한계

- 이 비교는 Anthropic 공식 문서 하나를 근거로 한다. Cursor, Aider 등 다른 도구의 정확한
  압축 메커니즘은 문서화가 부족해 확인하지 못했다 - 그 도구들에 대해서는 "확인 안 됨"으로
  남겨두고, 확인되지 않은 것을 확인됐다고 적지 않는다(AGENTS.md 규칙 7).
- Anthropic의 방식과 이 프로젝트의 방식은 배포 형태 자체가 다르다(자동 실시간 vs 세션
  종료 후 수동 CLI 실행) - 직접적인 1:1 성능 비교가 아니라 "압축 정확도를 공개 측정하는가"
  라는 방법론 차원의 비교다.
