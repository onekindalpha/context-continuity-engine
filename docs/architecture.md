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
| Task Context Analysis | - | 미구현 |
| Keep/Compress/Externalize | - | 미구현 |
| Reconstruction Test | - | 미구현 |
| Token Comparison | - | 미구현 |

## ingest 출력 schema

`docs/decisions/0003-ingest-output-schema.md` 참조.

## 원본 정보와 추출 정보

`examples/groq_model_migration_session/`에 두 종류의 데이터를 분리해서 둔다.

- 원본 정보(`session.txt`, `session.md`, `session.json`): 실제 세션에서 추출한 발화. `src/ingest.py`가 읽는 대상.
- 추출 정보(`annotations.json`): 사람이 turn을 사건 유형으로 분류한 참고 데이터. ingest 코드가 생성하거나 읽지 않는다. 이후 Reconstruction Test 단계의 ground truth로 사용할 목적으로 미리 준비해 둔다.
