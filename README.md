# context-continuity-engine

AI coding session의 context가 한계에 도달했을 때, 현재 작업에 필요한 context를 보존하고 불필요한 context를 줄여 작업 연속성과 token 효율을 확보하는 도구.

## 문서

- 문제 정의: [docs/problem.md](docs/problem.md)
- 평가 방법: [docs/evaluation.md](docs/evaluation.md)
- 아키텍처: [docs/architecture.md](docs/architecture.md)
- 결정 기록: [docs/decisions/](docs/decisions/)
- AI 작업 규칙: [AGENTS.md](AGENTS.md)

## 상태

전체 파이프라인(ingest → Task Context Analysis → Working Context → baseline 비교 → reconstruction test → token 비교)이 규칙 기반 baseline 수준으로 구현됨. 상세는 [docs/architecture.md](docs/architecture.md) 참조. 실행: `python3 -m unittest discover -s tests`

비교 실행: `python3 scripts/run_comparison.py` → `examples/groq_model_migration_session/comparison_result.md`에서 실제 token/reconstruction 결과 확인.

## 예제 데이터

`examples/groq_model_migration_session/` — 실제 개발 세션에서 추출한 session log. 원본 정보(session.txt/md/json)와 추출 정보(annotations.json) 구분은 해당 디렉토리의 README 참조.

## 라이선스

MIT
