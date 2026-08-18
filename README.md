# context-continuity-engine

AI coding session의 context가 한계에 도달했을 때, 현재 작업에 필요한 context를 보존하고 불필요한 context를 줄여 작업 연속성과 token 효율을 확보하는 도구.

## 문서

- 문제 정의: [docs/problem.md](docs/problem.md)
- 평가 방법: [docs/evaluation.md](docs/evaluation.md)
- 아키텍처: [docs/architecture.md](docs/architecture.md)
- 결정 기록: [docs/decisions/](docs/decisions/)
- AI 작업 규칙: [AGENTS.md](AGENTS.md)

## 상태

`src/ingest.py` 구현됨(TXT/Markdown/JSON session log → 공통 내부 표현). 이후 단계(Task Context Analysis 등)는 미구현. 실행: `python3 -m unittest discover -s tests`

## 예제 데이터

`examples/groq_model_migration_session/` — 실제 개발 세션에서 추출한 session log. 원본 정보(session.txt/md/json)와 추출 정보(annotations.json) 구분은 해당 디렉토리의 README 참조.

## 라이선스

Apache 2.0
