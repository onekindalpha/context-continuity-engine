# 0005. retention_reason 필드 추가

## 상태

확정. 0004의 schema를 수정한다.

## 배경

Task Context Analysis 실제 동작 단계로 넘어가기 전에 "왜 이 item을 KEEP/COMPRESS/EXTERNALIZE/DISCARD 했는가"를 사람이 확인할 수 있어야 한다는 요구가 있었다. 0004의 schema에는 `retention_action` 값만 있고 그 근거를 담을 필드가 없었다.

## 결정

`ContextItem`에 `retention_reason: string | null` 필드를 추가한다.

```
ContextItem:
  ...
  retention_action: "KEEP" | "COMPRESS" | "EXTERNALIZE" | "DISCARD" | null
  retention_reason: string | null   # 신규
```

`retention_action`이 null이 아니면 `retention_reason`도 값을 가져야 한다. 어떤 신호(task_relevance, importance, dependency 여부)로 그 판단을 내렸는지 짧게 적는다.

## 범위를 retention_reason으로 제한한 이유

`importance`, `task_relevance`에도 근거 필드를 둘 수 있지만 추가하지 않았다. 이번 요구가 명시적으로 요청한 것은 retention 판단(KEEP/COMPRESS/EXTERNALIZE/DISCARD)의 설명 가능성이다. 요청 범위를 넘는 필드를 미리 추가하지 않는다(AGENTS.md 규칙: 근거 없이 기능을 늘리지 않는다).

## 영향받는 문서/파일

- `docs/decisions/0004-task-context-analysis-schema.md`의 schema 정의는 그대로 두고, 이 문서가 그 내용을 수정한다(문서 자체는 다시 쓰지 않음).
- `src/validate.py`: `retention_reason`을 필수 필드에 포함.
- `examples/groq_model_migration_session/task_context_analysis.example.json`: 각 item에 `retention_reason: null` 추가(이 예시는 retention_action 자체도 아직 계산 전이므로 null 유지).
