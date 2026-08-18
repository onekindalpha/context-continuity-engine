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


def turn_coverage(analysis: dict[str, Any]) -> dict[str, Any]:
    """analysis의 retention_action별로 turn_id를 in_context/retrievable로 나눈다.

    평가 목적: reconstruction test(src/reconstruction_test.py)가 baseline과
    같은 기준(turn_id 단위 포함 여부)으로 제안 방식을 비교할 수 있어야 한다.

    분류 기준:
    - KEEP, COMPRESS: working context 텍스트 안에 내용이 직접 들어간다
      (COMPRESS는 요약이지만 의미는 남는다) → in_context
    - EXTERNALIZE: 텍스트에는 참조 한 줄만 있고, 원문은 external store에
      있다 → retrievable(즉시는 아니지만 조회하면 답변 가능)
    - DISCARD, 그리고 애초에 ContextItem으로 추출되지 않은 turn: 아무 데도
      없다 → 둘 다 아님

    한계: 추출기가 모든 turn에 대해 ContextItem을 만들지는 않는다
    (docs/decisions/0006 관찰된 한계 참조). ContextItem이 없는 turn은
    이 함수 결과에 전혀 나타나지 않으며, 호출하는 쪽에서 "커버 안 됨"으로
    처리해야 한다.
    """
    in_context: set[int] = set()
    retrievable: set[int] = set()
    for item in analysis["items"]:
        action = item["retention_action"]
        if action in ("KEEP", "COMPRESS"):
            in_context.update(item["source_turn_ids"])
        elif action == "EXTERNALIZE":
            retrievable.update(item["source_turn_ids"])
        # DISCARD: 아무 집합에도 넣지 않는다.
    return {"in_context_turn_ids": in_context, "retrievable_turn_ids": retrievable}
