# 0011. 단일 명령 CLI

## 상태

확정

## 결정

`python3 -m src.cli <session_log>` 명령 하나로 ingest → Task Context Analysis → Working Context 생성까지 실행하고, 결과 텍스트를 표준출력으로 낸다. `src/cli.py`에 구현했다.

## 이유

지금까지는 `scripts/run_context_analysis.py`, `scripts/run_comparison.py`를 fixture 경로에 맞춰 각각 실행해야 했다. 실제로 오늘 쓴 세션을 새 세션에 이어붙이려면, 세션 로그 파일 하나를 명령 하나로 처리해서 바로 붙여넣을 텍스트를 얻을 수 있어야 한다. 표준출력으로 내는 이유는 `python3 -m src.cli session.txt | pbcopy`처럼 클립보드로 바로 연결할 수 있게 하기 위함이다.

## 범위

- 입력: TXT/Markdown/JSON 형식 session log 파일 1개(기존 ingest가 지원하는 형식 그대로).
- 출력: Working Context 텍스트(표준출력) + 요약 통계(표준에러 — token 감소율, retention_action 분포).
- `--json` 옵션으로 전체 분석 결과(JSON)를 대신 출력할 수 있다.

## 범위에 포함하지 않음

Claude Code, Cursor 등 실제 코딩 에이전트와의 실시간 연동은 포함하지 않는다. IDE extension, real-time hook은 `docs/decisions/0001-scope-exclusions.md`에서 이미 제외했다. 이 CLI는 세션 로그 파일을 손으로 저장한 뒤 수동으로 실행하는 것을 전제로 한다.
