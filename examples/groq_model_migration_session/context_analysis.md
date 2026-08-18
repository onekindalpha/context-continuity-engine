# Task Context Analysis 결과 (규칙 기반 baseline)

생성 방식: `src/context_analysis.py`(규칙 기반, LLM 미사용, docs/decisions/0006 참조). 입력: `session.json`(20 turn). schema: `docs/decisions/0004`, `0005`.

- item 수: 14
- schema validator 결과: ok=True, errors=[]
- current_task(자동 추정, 첫 현재-episode item 요약): LLM text pipeline error] Error code: 404 - {'error': {'message': 'The model `llama-3.1-8b-instant` does not exist or you...

## item 목록

| item_id | category | source_turn_ids | importance | task_relevance | retention_action | retention_reason |
|---|---|---|---|---|---|---|
| item-0001 | evidence | [0] | 0.4 | 0.2 | DISCARD | task_relevance 낮음, importance 낮음, dependency 대상 아님 |
| item-0002 | failure | [1] | 0.7 | 0.2 | COMPRESS | importance=0.7 >= 0.6이지만 참조하는 item 없음 — 원문 보존 불필요, 의미만 압축 보존 |
| item-0003 | evidence | [5] | 0.4 | 0.2 | DISCARD | task_relevance 낮음, importance 낮음, dependency 대상 아님 |
| item-0004 | failure | [6] | 0.7 | 0.2 | COMPRESS | importance=0.7 >= 0.6이지만 참조하는 item 없음 — 원문 보존 불필요, 의미만 압축 보존 |
| item-0005 | failure | [7] | 0.7 | 0.2 | COMPRESS | importance=0.7 >= 0.6이지만 참조하는 item 없음 — 원문 보존 불필요, 의미만 압축 보존 |
| item-0006 | evidence | [10] | 0.4 | 0.2 | DISCARD | task_relevance 낮음, importance 낮음, dependency 대상 아님 |
| item-0007 | failure | [11] | 0.7 | 0.2 | COMPRESS | importance=0.7 >= 0.6이지만 참조하는 item 없음 — 원문 보존 불필요, 의미만 압축 보존 |
| item-0008 | evidence | [13] | 0.4 | 0.2 | DISCARD | task_relevance 낮음, importance 낮음, dependency 대상 아님 |
| item-0009 | failure | [14] | 0.7 | 0.9 | KEEP | task_relevance=0.9 >= 0.7 (현재 task 수행에 직접 필요) |
| item-0010 | evidence | [15] | 0.4 | 0.9 | KEEP | task_relevance=0.9 >= 0.7 (현재 task 수행에 직접 필요) |
| item-0011 | evidence | [16] | 0.5 | 0.9 | KEEP | task_relevance=0.9 >= 0.7 (현재 task 수행에 직접 필요) |
| item-0012 | current_state | [17] | 0.7 | 0.9 | KEEP | task_relevance=0.9 >= 0.7 (현재 task 수행에 직접 필요) |
| item-0013 | evidence | [18] | 0.4 | 0.9 | KEEP | task_relevance=0.9 >= 0.7 (현재 task 수행에 직접 필요) |
| item-0014 | next_action | [19] | 0.5 | 0.9 | KEEP | task_relevance=0.9 >= 0.7 (현재 task 수행에 직접 필요) |

## retention_action 분포

| action | 개수 |
|---|---|
| KEEP | 6 |
| COMPRESS | 4 |
| EXTERNALIZE | 0 |
| DISCARD | 4 |

episode 경계(가장 최근 1시간 이상 간격) 이전 item은 대부분 EXTERNALIZE/COMPRESS/DISCARD로, 이후(현재 task로 추정된 episode) item은 대부분 KEEP으로 갈렸다. 실제 값은 위 표 참조.

## dependency 그래프

- item-0012 → ['item-0011']
- item-0014 → ['item-0012']

## 수동 예시(task_context_analysis.example.json)와 비교

수동 예시는 사람이 20개 turn을 14개 item으로 정리한 것이다(일부는 여러 turn을 하나로 합침, 일부 turn은 의도적으로 제외). 규칙 기반 결과는 turn 단위로만 분류한다(합치지 않음). 아래 표는 turn 단위로 두 결과를 비교한다.

| turn_id | 수동(원본) category | 자동(규칙 기반) category | 일치? |
|---|---|---|---|
| 0 | (미포함) | evidence | 불일치 |
| 1 | (미포함) | failure | 불일치 |
| 2 | goal | (미포함) | 불일치 |
| 3 | (미포함) | (미포함) | - |
| 4 | evidence | (미포함) | 불일치 |
| 5 | decision | evidence | 불일치 |
| 6 | decision | failure | 불일치 |
| 7 | failure | failure | 일치 |
| 8 | decision | (미포함) | 불일치 |
| 9 | (미포함) | (미포함) | - |
| 10 | evidence | evidence | 일치 |
| 11 | evidence | failure | 불일치 |
| 12 | current_state | (미포함) | 불일치 |
| 13 | evidence | evidence | 일치 |
| 14 | failure | failure | 일치 |
| 15 | evidence | evidence | 일치 |
| 16 | evidence | evidence | 일치 |
| 17 | decision | current_state | 불일치 |
| 18 | current_state | evidence | 불일치 |
| 19 | next_action | next_action | 일치 |

두 결과 중 하나라도 item을 만든 turn 기준: 18개 중 7개 category 일치.

## 관찰된 한계(정직하게 기록)

- turn 2(실제 goal 발화)를 규칙이 놓쳤다. GOAL_PATTERNS 키워드가 실제 표현과 맞지 않았다.
- turn 5는 본문 대부분이 decision(작업 계획 발표)이지만 괄호 안 'git log' 언급 때문에 evidence로 분류됐다. 우선순위 규칙이 turn 안의 지배적 의미가 아니라 첫 매치를 따른다.
- turn 6, turn 11은 검증 성공 맥락에서 '에러'/'unsupported file type' 단어가 나와 failure로 잘못 분류됐다(실제로는 오류 처리가 의도대로 동작했음을 확인하는 evidence).
- turn 8(실제 changed_approach 결정)을 규칙이 놓쳤다. 실제 문장이 영어 진행 서술이라 한국어 DECISION_PATTERNS와 맞지 않았다.
- turn 12, turn 18(커밋 로그 원문)은 커밋 해시는 있지만 '완료' 계열 문구가 같은 turn에 없어 current_state 규칙(해시+문구 동시 조건)을 통과하지 못했다.
- 이번 실행 결과에는 decision category item이 하나도 없다(0개). DECISION_PATTERNS가 매치한 turn이 없었기 때문이다(turn 5는 evidence 규칙에 먼저 걸렸고, turn 8은 규칙 자체가 매치 안 됨). decision이 dependency 연결의 핵심 축(failure/current_state가 decision을 참조)인데 decision이 없으니 연쇄적으로 dependency edge도 2개뿐이고 EXTERNALIZE도 0개다. 카테고리 분류 실패가 dependency, retention_action까지 하류로 영향을 준 사례다.
- 결론: schema와 파이프라인(추출 → task_relevance → dependency → importance → retention_action)은 정상 동작하고 validator를 통과하지만, 규칙 기반 분류 자체의 의미 정확도는 낮다(turn 기준 18개 중 7개 일치). docs/decisions/0006에서 예정한 대로 다음 단계는 LLM 기반 추출기다.
