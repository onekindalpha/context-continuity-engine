# 아키텍처

## 파이프라인

```
Session Log
  ↓
Task Context Analysis   (구현됨 — 규칙 기반 baseline)
  ↓
Keep / Compress / Externalize   (retention_action 결정까지 구현됨, 실행은 미구현)
  ↓
Working Context   (미구현)
  ↓
Reconstruction Test   (미구현)
  ↓
Token Comparison   (미구현)
```

## 구현 상태

| 단계 | 모듈 | 상태 |
|---|---|---|
| Session Log ingest | `src/ingest.py` | 구현됨 |
| schema validator | `src/validate.py` | 구현됨 |
| Task Context Analysis(추출 + task_relevance + dependency + importance + retention_action 판단) | `src/context_analysis.py` | 구현됨(규칙 기반, LLM 미사용) |
| Working Context 생성(retention_action 실행) | - | 미구현 |
| Baseline(recency truncation, generic summary) | - | 미구현 |
| Reconstruction Test | - | 미구현 |
| Token Comparison | - | 미구현 |

## ingest 출력 schema

`docs/decisions/0003-ingest-output-schema.md` 참조.

## Task Context Analysis 출력 schema

`docs/decisions/0004-task-context-analysis-schema.md`, `docs/decisions/0005-retention-reason-field.md` 참조. `annotations.json`(13개 사건 유형, 원본 분석용)과 이 schema(6개 category, 제품용)는 다른 목적을 가진다. 후자만 이후 단계(Keep/Compress/Externalize)의 입력이 된다.

## Task Context Analysis 구현

`src/context_analysis.py`가 SessionLog를 받아 ContextItem 목록을 만든다. 규칙 기반이며 LLM을 호출하지 않는다. 이유: `docs/decisions/0006-rule-based-extractor-baseline.md`.

단계:
1. turn별 category 분류(키워드/정규식 규칙, 우선순위 순서로 첫 매치 채택)
2. task_relevance 계산(가장 최근 1시간 이상 시간 간격을 "현재 task 경계"로 추정)
3. dependency 연결(category별 허용된 선행 category 중 가장 가까운 item 참조)
4. importance 계산(category 기본값 + 다른 item의 dependency 대상이면 보너스)
5. retention_action 결정(규칙 트리, `docs/decisions/0004` 4절 근거 그대로 구현)

실행: `python3 scripts/run_context_analysis.py` → `examples/groq_model_migration_session/context_analysis.json`, `context_analysis.md` 생성.

fixture 실행 결과(정직하게 기록): schema validator는 통과하지만, 사람이 만든 예시(`task_context_analysis.example.json`)와 category 단위로 비교하면 18개 비교 대상 turn 중 7개만 일치한다. 상세 원인은 `context_analysis.md`의 "관찰된 한계" 절 참조. 다음 단계는 LLM 기반 추출기다(`docs/decisions/0006`).

## 원본 정보와 추출 정보

`examples/groq_model_migration_session/`에 데이터를 층위별로 분리해서 둔다.

- 원본 정보(`session.txt`, `session.md`, `session.json`): 실제 세션에서 추출한 발화. `src/ingest.py`가 읽는 대상.
- 추출 정보 — 분석용(`annotations.json`): 사람이 turn을 13개 사건 유형으로 분류한 참고 데이터. 코드가 생성하거나 읽지 않는다.
- 추출 정보 — 제품용, 사람이 만든 예시(`task_context_analysis.example.json`): schema 설계 검증용으로 사람이 직접 채운 값. importance/task_relevance/retention_action은 아직 null.
- 추출 정보 — 제품용, 코드가 생성한 결과(`context_analysis.json`, `context_analysis.md`): `src/context_analysis.py` 규칙 기반 baseline의 실제 실행 결과.
