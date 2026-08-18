# 0004. Task Context Analysis 출력 schema

## 상태

확정(schema만). 구현은 아직 없음.

## 평가 목적

Keep/Compress/Externalize/Discard 단계와 Reconstruction Test 단계가 이 schema에 의존한다. 두 단계를 만들기 전에 schema를 고정해 인터페이스를 먼저 검증한다.

## 범위

이 문서는 schema만 다룬다. 다음은 이 단계에 포함하지 않는다.

- LLM 호출
- relevance scoring 알고리즘
- compaction 실행
- `annotations.json`의 13개 사건 유형을 그대로 제품 schema로 사용하는 것

`annotations.json`(13개 사건 유형)은 원본 session을 사람이 분석하기 위한 annotation layer로 유지한다. 아래 schema는 제품이 실제로 쓸 최소 구조다. 둘은 다른 목적을 가진다.

## 1. 최소 schema

```
TaskContextAnalysis:
  schema_version: "1"
  session_id: string            # SessionLog.session_id와 연결
  current_task: string | null   # 아직 계산하지 않음. null 유지
  items: [ContextItem, ...]

ContextItem:
  item_id: string
  category: "goal" | "decision" | "failure" | "evidence" | "current_state" | "next_action"
  summary: string
  timestamp: string | null       # 대표 source turn의 timestamp
  source_turn_ids: [int, ...]    # 비어 있으면 안 됨
  depends_on: [item_id, ...]     # 없으면 빈 리스트
  importance: float | null       # 아직 계산하지 않음. null 유지
  task_relevance: float | null   # 아직 계산하지 않음. null 유지
  retention_action: "KEEP" | "COMPRESS" | "EXTERNALIZE" | "DISCARD" | null   # 아직 계산하지 않음. null 유지
```

후보로 제시된 7개 필드(goal, current_state, decision, dependency, failure, evidence, next_action) 중 `dependency`는 카테고리에서 제외했다. 이유는 4절 참조. 나머지 6개는 category enum 값으로 채택했다.

## 2. 각 필드의 의미

- `category`: item의 종류. 하나의 item은 하나의 category만 가진다.
- `summary`: item의 내용을 짧게 정리한 문장. 원문 자체가 아니다. 원문은 `source_turn_ids`로 SessionLog를 다시 조회해서 얻는다.
- `timestamp`: 대표 source turn의 timestamp를 그대로 복사한 값. 정렬과 표시 목적으로만 쓴다.
- `source_turn_ids`: item이 어떤 turn에서 나왔는지 기록한다. SessionLog.turns[turn_id]를 가리킨다. 하나의 item이 여러 turn에서 나올 수 있다(예: 결정을 발표한 turn과 실행 결과를 보고한 turn이 다를 때).
- `depends_on`: 이 item을 온전히 이해하는 데 필요한 다른 item의 id 목록. 방향은 "이 item을 유지하려면 저 item도 같이 유지해야 한다"는 의미다.
- `importance`: item 자체의 중요도. 시간이 지나도 값이 바뀌지 않는다.
- `task_relevance`: 현재 task 기준 관련도. `current_task`가 바뀌면 다시 계산해야 한다.
- `retention_action`: Keep/Compress/Externalize/Discard 단계가 채워 넣을 값. 오늘은 항상 null이다.

### turn과 item의 관계

turn은 원본 발화 단위, item은 의미 단위다. 하나의 turn이 여러 item으로 나뉠 수 있고, 여러 turn이 하나의 item으로 합쳐질 수도 있다. 단, 같은 사실을 서로 다른 category의 item으로 중복 저장하지 않는다(조건 1).

## 3. fixture 20개 turn의 schema 표현

전체 예시는 `examples/groq_model_migration_session/task_context_analysis.example.json`에 있다. 사람이 직접 만든 예시다. LLM이나 코드가 생성하지 않았다.

20개 turn 중 14개 item으로 정리했다. turn 0, 1, 3, 9는 item으로 만들지 않았다.

| turn_id | 내용 | 처리 |
|---|---|---|
| 0 | "근데 pdf 안넣어져" | item 없음. turn 2가 같은 목표를 더 명확하게 표현 |
| 1 | 어시스턴트의 확인 질문 | item 없음. 새 사실 없음 |
| 3 | 어시스턴트의 원인 설명(1차) | item 없음. turn 5의 current_state가 같은 사실을 더 명확하게 표현 |
| 9 | "smoke test 하겠다" | item 없음. turn 10/11의 evidence가 결과를 담음 |

| item_id | category | source_turn_ids | depends_on | 요약 |
|---|---|---|---|---|
| item-0001 | goal | [2] | [] | 문서 업로드를 기존 dropzone/파일 선택에 통합 |
| item-0002 | evidence | [4] | [] | git log에 문서 업로드 commit 없음, 실제 레포 경로 확인 |
| item-0003 | current_state | [5] | [item-0002] | 문서 업로드 기능이 레포에 없는 상태 |
| item-0004 | decision | [5, 6] | [item-0003] | document_ingest.py 신규 작성 + 별도 DOC 버튼 UI로 추가(commit 8bdfda2) |
| item-0005 | failure | [7] | [item-0004] | DOC 버튼이 안 보임 + markitdown 모듈 미설치 오류 |
| item-0006 | decision | [8] | [item-0005, item-0001] | 별도 버튼 대신 기존 dropzone에 통합하기로 변경 |
| item-0007 | evidence | [10, 11] | [item-0006] | 통합 흐름에서 문서+이미지 업로드 200 성공, .exe는 안전하게 거부 |
| item-0008 | current_state | [12] | [item-0006, item-0007] | dropzone 통합 완료, commit feba752 |
| item-0009 | evidence | [13] | [] | 사용자 비용 불만("돈 아까워") |
| item-0010 | failure | [14] | [item-0011] | Groq 404, `llama-3.1-8b-instant` not found |
| item-0011 | evidence | [15, 16] | [] | 해당 모델 2026-08-16 deprecated, 대체 모델 확인(공식 문서) |
| item-0012 | decision | [17] | [item-0010, item-0011] | 기본 모델을 openai/gpt-oss-20b, qwen/qwen3.6-27b로 교체(commit 9b20be9) |
| item-0013 | current_state | [18] | [item-0012] | 모델 교체 완료, commit 9b20be9 |
| item-0014 | next_action | [19] | [item-0013] | 개별 수정에서 전체 방향 재논의로 전환 |

item-0010(failure)이 item-0011(evidence)에 의존하는 방향에 주의한다. 시간 순서로는 evidence(turn 15/16)가 failure(turn 14)보다 늦게 나온다. `depends_on`은 시간 순서가 아니라 "이해에 필요한 관계"를 나타낸다. failure를 유지하면서 "실패 이유"에 답하려면 그 원인을 설명하는 evidence도 같이 유지해야 하므로 이 방향으로 정의했다.

item-0011은 item-0010과 item-0012 양쪽에서 참조된다. 같은 사실(모델 deprecated)을 두 item의 summary에 각각 적지 않고 한 곳에 두고 참조만 공유한다. 조건 1을 만족하는 방식이다.

## 4. schema가 KEEP/COMPRESS/EXTERNALIZE/DISCARD 판단을 지원하는 이유

이 schema 자체는 판단을 내리지 않는다. 판단에 필요한 신호를 미리 구조화해 둔다.

- `category`만으로는 판단이 안 된다. goal은 대체로 유지 대상이지만, evidence는 item마다 다르다(item-0011은 유지 대상, item-0009는 아닐 수 있다). category와 importance/task_relevance를 같이 봐야 한다.
- `depends_on`은 discard 가능 여부를 정한다. 다른 item이 참조하는 item(예: item-0011, item-0001, item-0004, item-0006)을 그대로 버리면 참조하는 쪽이 깨진다. 이런 item은 discard 대신 externalize(원문은 밖으로 빼되 참조는 유지)가 적절하다. 반대로 아무도 참조하지 않는 leaf item(예: item-0009)은 discard 후보가 될 수 있다.
- `importance`와 `task_relevance`를 분리해 뒀기 때문에, "오래됐지만 중요함"(예: item-0001 goal, 세션 앞부분에 있지만 끝까지 중요)과 "최근이지만 무관함"을 구분해서 판단할 수 있다. recency만으로 판단하는 기존 도구들의 문제를 이 구조로 피한다.

## 5. 제거한 필드와 이유

- **dependency(category로)**: 관계는 item의 종류가 아니다. category enum에서 빼고 `depends_on` 필드로 옮겼다.
- **recency(저장 필드로)**: recency는 "지금 시점" 기준 상대값이라 세션이 길어질수록 값이 바뀐다. item 생성 시점에 고정값으로 저장하면 곧 낡은 값이 된다. `timestamp`와 `source_turn_ids`만 있으면 판단 시점에 다시 계산할 수 있으므로 별도 필드를 두지 않았다.
- **error(별도 category로)**: 실제 fixture에서 오류 발생과 실패 보고가 같은 turn(turn 7)에 같이 있는 경우가 있었다. error를 별도 category로 두면 같은 turn을 failure와 error 두 item으로 중복 저장하게 된다. failure 하나로 합쳤다.
- **root_cause(별도 category로)**: evidence의 한 종류로 처리했다. 별도 category를 두면 root_cause를 참조하는 item마다 내용을 복사해야 한다. evidence + depends_on 조합으로 참조를 공유하는 쪽을 택했다.
- **user_feedback(별도 category로)**: 내용에 따라 failure(문제를 보고하는 피드백, 예: turn 7) 또는 evidence(문제 보고가 아닌 피드백, 예: turn 13)로 흡수했다. 별도 category를 두면 failure/evidence와 경계가 자주 겹친다.
- **initial_approach / changed_approach(별도 category로)**: 둘 다 decision이다. "이전 결정을 뒤집은 결정인지"는 category가 아니라 depends_on 관계(예: item-0006이 item-0005 failure에 의존)로 구분할 수 있다.
- **tool_framework_usage(별도 category로)**: 독립적인 keep/discard 판단이 필요 없다. 관련 decision의 summary 안에 내용으로 남긴다(예: item-0004에 "MarkItDown 기반" 포함).
- **validation(별도 category로)**: evidence의 한 종류로 처리했다(예: item-0007).
- **source_excerpt(원문 일부 복사 필드)**: 설계 중 후보에 있었으나 뺐다. `source_turn_ids`로 SessionLog를 다시 조회하면 원문 전체를 볼 수 있어 중복이다. 복사본을 두면 원본이 바뀌었을 때 불일치가 생길 위험도 있다.
- **order(별도 정렬 필드)**: `timestamp`와 `source_turn_ids`(turn_id 자체가 순서)로 이미 순서를 알 수 있어 추가하지 않았다.

## 확인되지 않음

- `current_task`를 세션 진행 중 어떻게 갱신할지(세션 하나 안에 task가 여러 개일 수 있음, 이번 fixture도 UI 문제 → 모델 문제 두 task를 포함)
- `task_relevance`가 task 1개 기준 단일 값으로 충분한지, task별로 나눠 저장해야 하는지
- retention_action을 item 단위로만 정할지, item 그룹(의존관계로 묶인 단위) 단위로 정해야 하는지
