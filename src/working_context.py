"""Working Context 생성: retention_action을 실제로 실행한다.

평가 목적: retention_action(KEEP/COMPRESS/EXTERNALIZE/DISCARD)이 계산만 되고
끝나면 token 절감 효과를 측정할 수 없다. 이 모듈이 판단을 실제 텍스트로 만든다.

실행 규칙:
- KEEP        원본 turn 전문을 넣는다.
- COMPRESS    summary만 넣는다. 원문은 넣지 않는다.
- EXTERNALIZE 참조 한 줄만 넣고, 원문은 external store에 보관한다.
- DISCARD     넣지 않는다. external store에도 넣지 않는다.

의존성: 표준 라이브러리만 사용한다.
"""

from __future__ import annotations

from typing import Any

EXTERNAL_REF_TEMPLATE = "[외부 보관: {item_id} ({category}) — 필요 시 turn {turns} 조회]"


def build_working_context(
    analysis: dict[str, Any], session: dict[str, Any]
) -> dict[str, Any]:
    """analysis의 retention_action에 따라 working context 텍스트를 만든다."""
    turns_by_id = {t["turn_id"]: t for t in session["turns"]}

    lines: list[str] = []
    external_store: dict[str, dict[str, Any]] = {}
    counts = {"KEEP": 0, "COMPRESS": 0, "EXTERNALIZE": 0, "DISCARD": 0}

    for item in analysis["items"]:
        action = item["retention_action"]
        counts[action] = counts.get(action, 0) + 1

        if action == "KEEP":
            for tid in item["source_turn_ids"]:
                turn = turns_by_id.get(tid)
                if turn:
                    lines.append(f"[{turn['speaker']}] {turn['text']}")
        elif action == "COMPRESS":
            lines.append(f"[{item['category']}] {item['summary']}")
        elif action == "EXTERNALIZE":
            lines.append(
                EXTERNAL_REF_TEMPLATE.format(
                    item_id=item["item_id"],
                    category=item["category"],
                    turns=item["source_turn_ids"],
                )
            )
            external_store[item["item_id"]] = {
                "category": item["category"],
                "summary": item["summary"],
                "source_turn_ids": item["source_turn_ids"],
                "original_texts": [
                    turns_by_id[tid]["text"] for tid in item["source_turn_ids"] if tid in turns_by_id
                ],
            }
        # DISCARD: 아무것도 하지 않는다.

    return {
        "text": "\n".join(lines),
        "external_store": external_store,
        "action_counts": counts,
        "included_item_ids": [
            item["item_id"]
            for item in analysis["items"]
            if item["retention_action"] != "DISCARD"
        ],
    }
