"""Task Context Analysis 출력 schema validator.

평가 목적: 실제 추출기(LLM 또는 규칙 기반)를 만들기 전에 schema 정합성 검사를
먼저 확보한다. LLM 호출, relevance scoring, compaction은 포함하지 않는다.

검사 대상 schema: docs/decisions/0004-task-context-analysis-schema.md,
docs/decisions/0005-retention-reason-field.md.
"""

from __future__ import annotations

from typing import Any

ALLOWED_CATEGORIES = {
    "goal",
    "decision",
    "failure",
    "evidence",
    "current_state",
    "next_action",
}
ALLOWED_RETENTION_ACTIONS = {"KEEP", "COMPRESS", "EXTERNALIZE", "DISCARD"}
REQUIRED_ITEM_FIELDS = (
    "item_id",
    "category",
    "summary",
    "timestamp",
    "source_turn_ids",
    "depends_on",
    "importance",
    "task_relevance",
    "retention_action",
    "retention_reason",
)
REQUIRED_DOC_FIELDS = ("schema_version", "session_id", "items")


def _is_unit_score(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0.0 <= value <= 1.0


def validate_analysis(data: dict[str, Any], session: dict[str, Any] | None = None) -> dict[str, Any]:
    """TaskContextAnalysis 문서를 검사한다.

    session을 주면 source_turn_ids가 실제 SessionLog의 turn 범위 안에 있는지도 확인한다.
    session을 주지 않으면 이 검사는 건너뛴다.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return {"ok": False, "errors": ["top-level value must be an object"]}

    for field in REQUIRED_DOC_FIELDS:
        if field not in data:
            errors.append(f"missing required field: {field}")
    if errors:
        return {"ok": False, "errors": errors}

    items = data["items"]
    if not isinstance(items, list):
        return {"ok": False, "errors": ["'items' must be a list"]}

    max_turn_id: int | None = None
    if session is not None:
        turns = session.get("turns", [])
        if turns:
            max_turn_id = max(t["turn_id"] for t in turns)
        else:
            max_turn_id = -1

    seen_ids: set[str] = set()
    valid_items: dict[str, dict[str, Any]] = {}

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"item at index {index}: must be an object")
            continue

        for field in REQUIRED_ITEM_FIELDS:
            if field not in item:
                errors.append(f"item at index {index}: missing required field: {field}")

        item_id = item.get("item_id")
        if not item_id or not isinstance(item_id, str):
            errors.append(f"item at index {index}: item_id must be a non-empty string")
        elif item_id in seen_ids:
            errors.append(f"duplicate item_id: {item_id}")
        else:
            seen_ids.add(item_id)
            valid_items[item_id] = item

        category = item.get("category")
        if category not in ALLOWED_CATEGORIES:
            errors.append(f"item {item_id or index}: invalid category: {category!r}")

        source_turn_ids = item.get("source_turn_ids")
        if not isinstance(source_turn_ids, list) or not source_turn_ids:
            errors.append(f"item {item_id or index}: source_turn_ids must be a non-empty list")
        else:
            for tid in source_turn_ids:
                if not isinstance(tid, int):
                    errors.append(f"item {item_id or index}: source_turn_ids must contain ints, got {tid!r}")
                elif max_turn_id is not None and not (0 <= tid <= max_turn_id):
                    errors.append(
                        f"item {item_id or index}: source_turn_id {tid} out of range "
                        f"(session has turn_id 0..{max_turn_id})"
                    )

        depends_on = item.get("depends_on")
        if not isinstance(depends_on, list):
            errors.append(f"item {item_id or index}: depends_on must be a list")
        elif item_id in depends_on:
            errors.append(f"item {item_id or index}: depends_on references itself")

        retention_action = item.get("retention_action")
        if retention_action is not None and retention_action not in ALLOWED_RETENTION_ACTIONS:
            errors.append(f"item {item_id or index}: invalid retention_action: {retention_action!r}")

        for score_field in ("importance", "task_relevance"):
            value = item.get(score_field)
            if value is not None and not _is_unit_score(value):
                errors.append(f"item {item_id or index}: {score_field} must be null or a number in [0, 1]")

    # depends_on dangling reference check (needs full id set first).
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("item_id")
        depends_on = item.get("depends_on")
        if not isinstance(depends_on, list):
            continue
        for dep in depends_on:
            if dep not in seen_ids:
                errors.append(f"item {item_id}: depends_on references unknown item_id: {dep!r}")

    cycle = _find_cycle(valid_items)
    if cycle:
        errors.append(f"dependency cycle detected: {' -> '.join(cycle)}")

    return {"ok": len(errors) == 0, "errors": errors}


def _find_cycle(items: dict[str, dict[str, Any]]) -> list[str] | None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {item_id: WHITE for item_id in items}
    path: list[str] = []

    def visit(item_id: str) -> list[str] | None:
        color[item_id] = GRAY
        path.append(item_id)
        for dep in items[item_id].get("depends_on", []):
            if dep not in items:
                continue
            if color.get(dep) == GRAY:
                cycle_start = path.index(dep)
                return path[cycle_start:] + [dep]
            if color.get(dep) == WHITE:
                result = visit(dep)
                if result:
                    return result
        path.pop()
        color[item_id] = BLACK
        return None

    for item_id in items:
        if color[item_id] == WHITE:
            result = visit(item_id)
            if result:
                return result
    return None
