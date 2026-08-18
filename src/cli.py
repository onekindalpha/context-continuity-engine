"""단일 명령 CLI: session log 하나를 받아 Working Context를 만든다.

평가 목적: ingest → Task Context Analysis → Working Context 생성을 명령 하나로
끝내야 실제로 매일 쓸 수 있다(docs/decisions/0011). 표준출력으로 텍스트를 내는
이유는 `python3 -m src.cli session.txt | pbcopy`처럼 클립보드로 바로 연결하기
위함이다.

범위: 실제 코딩 에이전트와의 실시간 연동은 하지 않는다(0001, 0011).
세션 로그 파일을 손으로 저장한 뒤 이 명령을 수동으로 실행하는 것을 전제로 한다.

의존성: 표준 라이브러리만 사용한다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.context_analysis import build_analysis
from src.ingest import ingest_file
from src.tokens import count_tokens
from src.working_context import build_working_context


def run(path: Path) -> dict[str, Any]:
    """session log 파일 하나를 ingest → 분석 → Working Context까지 처리한다."""
    ingest_result = ingest_file(path)
    if not ingest_result["ok"]:
        raise ValueError(f"ingest 실패: {ingest_result['error']}")
    session = ingest_result["session"]
    analysis = build_analysis(session)
    working_context = build_working_context(analysis, session)
    return {"session": session, "analysis": analysis, "working_context": working_context}


def _original_text(session: dict[str, Any]) -> str:
    return "\n".join(f"[{t['speaker']}] {t['text']}" for t in session["turns"])


def _summary_line(result: dict[str, Any]) -> str:
    session = result["session"]
    wc = result["working_context"]
    original_tokens = count_tokens(_original_text(session))
    wc_tokens = count_tokens(wc["text"])
    reduction = (1 - wc_tokens / original_tokens) * 100 if original_tokens else 0.0
    counts = wc["action_counts"]
    return (
        f"turn {session['turn_count']}개 → Working Context {wc_tokens} token "
        f"(원본 {original_tokens} token 대비 {reduction:.1f}% 감소). "
        f"KEEP {counts['KEEP']} / COMPRESS {counts['COMPRESS']} / "
        f"EXTERNALIZE {counts['EXTERNALIZE']} / DISCARD {counts['DISCARD']}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="context-continuity-engine",
        description="session log(.txt/.md/.json)를 받아 Working Context를 만든다.",
    )
    parser.add_argument("session_log", type=Path, help="session log 파일 경로")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Working Context 텍스트 대신 전체 분석 결과를 JSON으로 표준출력에 낸다",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.session_log.exists():
        print(f"파일 없음: {args.session_log}", file=sys.stderr)
        return 1

    try:
        result = run(args.session_log)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    wc = result["working_context"]

    if args.json:
        payload = {
            "analysis": result["analysis"],
            "working_context": {
                "text": wc["text"],
                "action_counts": wc["action_counts"],
                "included_item_ids": wc["included_item_ids"],
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(wc["text"])

    print(_summary_line(result), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
