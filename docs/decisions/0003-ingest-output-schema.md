# 0003. ingest 출력 schema

## 상태

확정

## 평가 목적

이후 단계(Task Context Analysis, Keep/Compress/Externalize, Reconstruction Test)가 공통 입력 형식에 의존한다. 형식을 먼저 고정해야 각 단계를 독립적으로 개발/테스트할 수 있다.

## 결정

### IngestResult

```
{
  "ok": bool,
  "session": SessionLog | null,
  "error": string | null
}
```

실패 시 예외를 던지지 않고 `ok=False`와 `error` 메시지를 반환한다. 근거: 기존 레포(Study Documentation Agent)의 `tools/document_ingest.py`가 사용한 안전 실패 패턴과 동일.

### SessionLog

```
{
  "schema_version": "1",
  "source_format": "txt" | "markdown" | "json",
  "session_id": string | null,
  "turns": [Turn, ...],
  "turn_count": int,
  "warnings": [string, ...]
}
```

### Turn

```
{
  "turn_id": int,        # 0부터 시작, 등장 순서
  "speaker": "user" | "assistant" | "unknown",
  "timestamp": string | null,
  "text": string
}
```

## 형식별 파싱 규칙

- TXT: `[timestamp] SPEAKER:` 줄을 turn 구분자로 사용한다.
- Markdown: `### SPEAKER — timestamp` 줄을 turn 구분자로 사용한다.
- JSON: 최상위 객체에 `turns`(list) 필수. 각 turn 객체에 `speaker`, `text` 필수, `timestamp`는 선택.

## speaker 정규화

`user`, `assistant`만 그대로 인정한다. 그 외 값은 `unknown`으로 정규화한다.

이유: 이후 단계에서 speaker 값을 분기 조건으로 사용할 가능성이 있다. 정의되지 않은 값을 그대로 통과시키면 이후 단계에서 예상 못 한 분기가 생긴다.

## 필수 필드 누락 처리

JSON 입력에서 turn에 `speaker` 또는 `text`가 없거나 빈 문자열이면 전체 ingest를 실패로 처리한다(부분 스킵이 아님).

이유: 조용히 건너뛰면 이후 단계가 어떤 turn이 빠졌는지 알 수 없다. 실패로 처리하면 원본 데이터 문제를 입력 단계에서 바로 알 수 있다.

## 빈 세션 처리

`turns`가 빈 리스트이거나 구분자가 하나도 없는 TXT/Markdown은 실패가 아니라 `ok=True, turn_count=0`으로 처리하고 `warnings`에 기록한다.

이유: 빈 세션은 잘못된 입력이 아니라 유효한 경계 케이스다. `잘못된 JSON`, `필수 필드 누락`과는 다른 실패 범주로 구분해야 테스트가 명확해진다.

## 오늘 구현하지 않는 것

turn 내용에 대한 의미 분석(카테고리 태깅, relevance 판단, 의존성 분석)은 이 모듈의 책임이 아니다. `examples/groq_model_migration_session/annotations.json`은 사람이 미리 만든 참고 데이터이며 ingest 코드가 생성하지 않는다.
