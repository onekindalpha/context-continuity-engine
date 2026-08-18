# 아키텍처

## 파이프라인

```
Session Log
  ↓
Task Context Analysis   (미구현)
  ↓
Keep / Compress / Externalize   (미구현)
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
| Task Context Analysis | - | schema만 확정(구현 없음) |
| Keep/Compress/Externalize | - | 미구현 |
| Reconstruction Test | - | 미구현 |
| Token Comparison | - | 미구현 |

## ingest 출력 schema

`docs/decisions/0003-ingest-output-schema.md` 참조.

## Task Context Analysis 출력 schema

`docs/decisions/0004-task-context-analysis-schema.md` 참조. `annotations.json`(13개 사건 유형, 원본 분석용)과 이 schema(6개 category, 제품용)는 다른 목적을 가진다. 후자만 이후 단계(Keep/Compress/Externalize)의 입력이 된다.

## 원본 정보와 추출 정보

`examples/groq_model_migration_session/`에 세 층위의 데이터를 분리해서 둔다.

- 원본 정보(`session.txt`, `session.md`, `session.json`): 실제 세션에서 추출한 발화. `src/ingest.py`가 읽는 대상.
- 추출 정보 — 분석용(`annotations.json`): 사람이 turn을 13개 사건 유형으로 분류한 참고 데이터. 코드가 생성하거나 읽지 않는다.
- 추출 정보 — 제품용(`task_context_analysis.example.json`): 6개 category(goal/decision/failure/evidence/current_state/next_action) schema로 사람이 직접 만든 예시. 실제 분석 단계가 구현되면 이 schema를 채우는 코드로 대체한다.
