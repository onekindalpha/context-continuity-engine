"""fixture에 대해 Task Context Analysis를 실행하고 결과를 저장한다.

사용법: python3 scripts/run_context_analysis.py

입력: examples/groq_model_migration_session/session.json
출력: examples/groq_model_migration_session/context_analysis.json
      examples/groq_model_migration_session/context_analysis.md

LLM을 호출하지 않는다(docs/decisions/0006). 규칙 기반 결과를 그대로 저장한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.context_analysis import build_analysis  # noqa: E402
from src.ingest import ingest_file  # noqa: E402
from src.validate import validate_analysis  # noqa: E402

FIXTURE_DIR = ROOT / "examples" / "groq_model_migration_session"

RETENTION_ORDER = ["KEEP", "COMPRESS", "EXTERNALIZE", "DISCARD"]
CATEGORY_LABELS = {
    "goal": "goal",
    "decision": "decision",
    "failure": "failure",
    "evidence": "evidence",
    "current_state": "current_state",
    "next_action": "next_action",
}


def _load_manual_example() -> dict:
    return json.loads((FIXTURE_DIR / "task_context_analysis.example.json").read_text(encoding="utf-8"))


def _load_session_raw_turns() -> dict[int, dict]:
    session_json = json.loads((FIXTURE_DIR / "session.json").read_text(encoding="utf-8"))
    return {i: t for i, t in enumerate(session_json["turns"])}


def _manual_category_by_turn(manual: dict) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for item in manual["items"]:
        for tid in item["source_turn_ids"]:
            mapping[tid] = item["category"]
    return mapping


def render_markdown(analysis: dict, session: dict, validation: dict, manual: dict) -> str:
    lines: list[str] = []
    lines.append("# Task Context Analysis 결과 (규칙 기반 baseline)")
    lines.append("")
    lines.append(
        "생성 방식: `src/context_analysis.py`(규칙 기반, LLM 미사용, docs/decisions/0006 참조). "
        "입력: `session.json`(20 turn). schema: `docs/decisions/0004`, `0005`."
    )
    lines.append("")
    lines.append(f"- item 수: {len(analysis['items'])}")
    lines.append(f"- schema validator 결과: ok={validation['ok']}, errors={validation['errors']}")
    lines.append(f"- current_task(자동 추정, 첫 현재-episode item 요약): {analysis['current_task']}")
    lines.append("")

    lines.append("## item 목록")
    lines.append("")
    lines.append(
        "| item_id | category | source_turn_ids | importance | task_relevance | retention_action | retention_reason |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for item in analysis["items"]:
        lines.append(
            f"| {item['item_id']} | {item['category']} | {item['source_turn_ids']} | "
            f"{item['importance']:.1f} | {item['task_relevance']:.1f} | {item['retention_action']} | "
            f"{item['retention_reason']} |"
        )
    lines.append("")

    lines.append("## retention_action 분포")
    lines.append("")
    counts = {k: 0 for k in RETENTION_ORDER}
    for item in analysis["items"]:
        counts[item["retention_action"]] += 1
    lines.append("| action | 개수 |")
    lines.append("|---|---|")
    for action in RETENTION_ORDER:
        lines.append(f"| {action} | {counts[action]} |")
    lines.append("")
    lines.append(
        "episode 경계(가장 최근 1시간 이상 간격) 이전 item은 대부분 EXTERNALIZE/COMPRESS/DISCARD로, "
        "이후(현재 task로 추정된 episode) item은 대부분 KEEP으로 갈렸다. 실제 값은 위 표 참조."
    )
    lines.append("")

    lines.append("## dependency 그래프")
    lines.append("")
    any_deps = False
    for item in analysis["items"]:
        if item["depends_on"]:
            any_deps = True
            lines.append(f"- {item['item_id']} → {item['depends_on']}")
    if not any_deps:
        lines.append("(연결된 dependency 없음)")
    lines.append("")

    lines.append("## 수동 예시(task_context_analysis.example.json)와 비교")
    lines.append("")
    lines.append(
        "수동 예시는 사람이 20개 turn을 14개 item으로 정리한 것이다(일부는 여러 turn을 하나로 합침, "
        "일부 turn은 의도적으로 제외). 규칙 기반 결과는 turn 단위로만 분류한다(합치지 않음). "
        "아래 표는 turn 단위로 두 결과를 비교한다."
    )
    lines.append("")
    manual_by_turn = _manual_category_by_turn(manual)
    auto_by_turn: dict[int, str] = {}
    for item in analysis["items"]:
        for tid in item["source_turn_ids"]:
            auto_by_turn[tid] = item["category"]

    lines.append("| turn_id | 수동(원본) category | 자동(규칙 기반) category | 일치? |")
    lines.append("|---|---|---|---|")
    match_count = 0
    compared_count = 0
    for tid in range(session["turn_count"]):
        manual_cat = manual_by_turn.get(tid, "(미포함)")
        auto_cat = auto_by_turn.get(tid, "(미포함)")
        if manual_cat == "(미포함)" and auto_cat == "(미포함)":
            mark = "-"
        else:
            compared_count += 1
            mark = "일치" if manual_cat == auto_cat else "불일치"
            if mark == "일치":
                match_count += 1
        lines.append(f"| {tid} | {manual_cat} | {auto_cat} | {mark} |")
    lines.append("")
    lines.append(
        f"두 결과 중 하나라도 item을 만든 turn 기준: {compared_count}개 중 {match_count}개 category 일치."
    )
    lines.append("")

    lines.append("## 관찰된 한계(정직하게 기록)")
    lines.append("")
    lines.append(
        "- turn 2(실제 goal 발화)를 규칙이 놓쳤다. GOAL_PATTERNS 키워드가 실제 표현과 맞지 않았다."
    )
    lines.append(
        "- turn 5는 본문 대부분이 decision(작업 계획 발표)이지만 괄호 안 'git log' 언급 때문에 "
        "evidence로 분류됐다. 우선순위 규칙이 turn 안의 지배적 의미가 아니라 첫 매치를 따른다."
    )
    lines.append(
        "- turn 6, turn 11은 검증 성공 맥락에서 '에러'/'unsupported file type' 단어가 나와 "
        "failure로 잘못 분류됐다(실제로는 오류 처리가 의도대로 동작했음을 확인하는 evidence)."
    )
    lines.append(
        "- turn 8(실제 changed_approach 결정)을 규칙이 놓쳤다. 실제 문장이 영어 진행 서술이라 "
        "한국어 DECISION_PATTERNS와 맞지 않았다."
    )
    lines.append(
        "- turn 12, turn 18(커밋 로그 원문)은 커밋 해시는 있지만 '완료' 계열 문구가 같은 turn에 "
        "없어 current_state 규칙(해시+문구 동시 조건)을 통과하지 못했다."
    )
    lines.append(
        "- 이번 실행 결과에는 decision category item이 하나도 없다(0개). DECISION_PATTERNS가 "
        "매치한 turn이 없었기 때문이다(turn 5는 evidence 규칙에 먼저 걸렸고, turn 8은 규칙 자체가 매치 안 됨). "
        "decision이 dependency 연결의 핵심 축(failure/current_state가 decision을 참조)인데 decision이 "
        "없으니 연쇄적으로 dependency edge도 2개뿐이고 EXTERNALIZE도 0개다. 카테고리 분류 실패가 "
        "dependency, retention_action까지 하류로 영향을 준 사례다."
    )
    lines.append(
        "- 결론: schema와 파이프라인(추출 → task_relevance → dependency → importance → retention_action)은 "
        "정상 동작하고 validator를 통과하지만, 규칙 기반 분류 자체의 의미 정확도는 낮다(turn 기준 18개 중 7개 일치). "
        "docs/decisions/0006에서 예정한 대로 다음 단계는 LLM 기반 추출기다."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    result = ingest_file(FIXTURE_DIR / "session.json")
    if not result["ok"]:
        raise SystemExit(f"ingest failed: {result['error']}")
    session = result["session"]

    analysis = build_analysis(session)
    validation = validate_analysis(analysis, session=session)
    manual = _load_manual_example()

    (FIXTURE_DIR / "context_analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (FIXTURE_DIR / "context_analysis.md").write_text(
        render_markdown(analysis, session, validation, manual), encoding="utf-8"
    )

    print(f"items: {len(analysis['items'])}")
    print(f"validator ok: {validation['ok']}")
    if validation["errors"]:
        print("validator errors:", validation["errors"])


if __name__ == "__main__":
    main()
