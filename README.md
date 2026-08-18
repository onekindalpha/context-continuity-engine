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

## 설치

저장소 폴더에서 한 번만:

```bash
pip install -e .
```

그러면 `context-continuity-engine` 명령이 어디서나(폴더 이동 없이) 바로 실행된다. `python3 -m src.cli` 형태로 실행해도 동일하게 동작한다(설치 없이 쓰고 싶을 때).

## 실제 사용법

세션이 길어져서 새 세션으로 넘어가야 할 때, 채팅 화면을 그대로 복사해서 파일로 저장한 뒤:

```bash
context-continuity-engine session.txt --raw | pbcopy   # macOS: Working Context를 클립보드로 바로 복사
context-continuity-engine session.txt --raw             # 표준출력으로 텍스트 확인
context-continuity-engine session.txt --raw --json      # 전체 분석 결과를 JSON으로 확인
```

`--raw`는 "user: 내용", "assistant: 내용" 정도의 화자 표시만 있으면 되는 느슨한 형식이다 — 채팅 화면 복사 텍스트에 그대로 쓸 수 있다(근거: `docs/decisions/0012-raw-text-input.md`). `[timestamp] speaker:` 같은 엄격한 형식으로 이미 정리된 파일이면 `--raw`를 빼도 된다.

새 세션 맨 앞에 붙여넣으면 된다. 요약 통계(token 감소율, retention_action 분포)는 표준에러로 따로 출력된다. 근거는 `docs/decisions/0011-single-command-cli.md` 참조.

## 예제 데이터

`examples/groq_model_migration_session/` — 실제 개발 세션에서 추출한 session log. 원본 정보(session.txt/md/json)와 추출 정보(annotations.json) 구분은 해당 디렉토리의 README 참조.

## 라이선스

Apache 2.0
