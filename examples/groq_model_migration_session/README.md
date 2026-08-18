# groq_model_migration_session

## 원본 정보와 추출 정보 구분

- `session.txt`, `session.md`, `session.json` — 원본 정보. 동일한 실제 대화 내용을 세 형식으로 표현한다. 세 파일의 발화 내용은 같다(형식만 다름). ingest.py가 읽는 대상.
- `annotations.json` — 추출 정보(분석용). 사람이 각 turn을 13개 사건 유형(User Goal, Decision, Error 등)으로 분류한 결과. ingest.py는 이 파일을 읽지 않는다. Reconstruction Test 단계에서 ground truth로 사용할 목적으로 미리 만들어 둔다.
- `task_context_analysis.example.json` — 추출 정보(제품용). `docs/decisions/0004-task-context-analysis-schema.md`의 6개 category(goal/decision/failure/evidence/current_state/next_action) schema를 사람이 직접 채운 예시. `annotations.json`과 목적이 다르다 — 13개 사건 유형은 사람이 원본을 이해하기 위한 분석용이고, 이 파일은 이후 Keep/Compress/Externalize 단계가 실제로 입력받을 최소 구조다.

## 출처

실제 개발 세션(2026-08-17 ~ 2026-08-18)에서 추출했다. 새로 작성한 대화 내용은 없다. 생략된 구간은 발화 텍스트 안에 `(...)`로 표시했다.

내용: Study Documentation Agent 레포에 문서 업로드 기능을 통합하는 과정. UI 배치 실패(별도 버튼 → 사용자 거부 → dropzone 통합)와 Groq 모델 deprecation 오류(원인 확인 → 기본값 교체 → 커밋) 두 사건을 포함한다.

## 포함된 사건 유형

User Goal, Initial Approach, Tool/Framework usage, Decision, Failed Approach, Error, Root Cause, User Feedback, Changed Approach, Evidence, Validation, Current State, Next Action.

turn_id별 매핑은 `annotations.json` 참조.

## 생성된 파일(코드 실행 결과)

- `context_analysis.json`, `context_analysis.md` — `scripts/run_context_analysis.py` 실행 결과. `src/context_analysis.py`(규칙 기반 추출기)가 `session.json`에서 만든 ContextItem 목록.
- `comparison_result.json`, `comparison_result.md` — `scripts/run_comparison.py` 실행 결과. baseline(recency truncation, generic summary)과 제안 방식(Working Context)의 token 사용량 및 reconstruction test(7개 질문) 결과 비교.

이 두 쌍은 코드가 생성한다. `task_context_analysis.example.json`은 사람이 손으로 만든 것이고, reconstruction test의 정답(ground truth)으로 쓰인다 — 서로 바꿔 쓰지 않는다.
