# groq_model_migration_session

## 원본 정보와 추출 정보 구분

- `session.txt`, `session.md`, `session.json` — 원본 정보. 동일한 실제 대화 내용을 세 형식으로 표현한다. 세 파일의 발화 내용은 같다(형식만 다름). ingest.py가 읽는 대상.
- `annotations.json` — 추출 정보. 사람이 각 turn을 사건 유형(User Goal, Decision, Error 등)으로 분류한 결과. ingest.py는 이 파일을 읽지 않는다. Reconstruction Test 단계에서 ground truth로 사용할 목적으로 미리 만들어 둔다.

## 출처

실제 개발 세션(2026-08-17 ~ 2026-08-18)에서 추출했다. 새로 작성한 대화 내용은 없다. 생략된 구간은 발화 텍스트 안에 `(...)`로 표시했다.

내용: Study Documentation Agent 레포에 문서 업로드 기능을 통합하는 과정. UI 배치 실패(별도 버튼 → 사용자 거부 → dropzone 통합)와 Groq 모델 deprecation 오류(원인 확인 → 기본값 교체 → 커밋) 두 사건을 포함한다.

## 포함된 사건 유형

User Goal, Initial Approach, Tool/Framework usage, Decision, Failed Approach, Error, Root Cause, User Feedback, Changed Approach, Evidence, Validation, Current State, Next Action.

turn_id별 매핑은 `annotations.json` 참조.

## 사용 범위(오늘)

`src/ingest.py`는 `session.txt` / `session.md` / `session.json`을 파싱해 공통 내부 표현으로 변환하는 것까지만 한다. `annotations.json`을 이용한 자동 평가(Task Context Analysis, Reconstruction Test)는 오늘 구현 범위에 없다.
