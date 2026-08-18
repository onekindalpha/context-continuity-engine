"""Baseline 방식 두 가지: recency truncation, generic summary.

평가 목적: 제안 방식(retention_action 기반 Working Context)이 실제로
더 나은지 판단하려면 비교 대상이 있어야 한다(docs/evaluation.md).
task_relevance/importance 계산 없이 흔히 쓰이는 두 가지 단순 방식을
baseline으로 둔다. 설계 근거는 docs/decisions/0009-baseline-design.md.

의존성: 표준 라이브러리만 사용한다.
"""

from __future__ import annotations

from typing import Any

DEFAULT_KEEP_LAST_N_TURNS = 6
DEFAULT_MAX_CHARS_PER_TURN = 40


def recency_truncation(
    session: dict[str, Any], keep_last_n_turns: int = DEFAULT_KEEP_LAST_N_TURNS
) -> dict[str, Any]:
    """최근 N개 turn만 verbatim으로 남기고 나머지는 버린다.

    task_relevance/importance를 계산하지 않는다. 시간 순서(최근 여부)만
    기준으로 삼는 sliding-window 방식이다. 버려진 turn은 어디에도
    보관되지 않는다 — 나중에 다시 조회할 방법이 없다.
    """
    turns = session["turns"]
    kept = turns[-keep_last_n_turns:] if keep_last_n_turns > 0 else []
    kept_ids = {t["turn_id"] for t in kept}
    lines = [f"[{t['speaker']}] {t['text']}" for t in kept]
    all_ids = {t["turn_id"] for t in turns}
    return {
        "method": "recency_truncation",
        "text": "\n".join(lines),
        "in_context_turn_ids": kept_ids,
        "retrievable_turn_ids": set(),
        "dropped_turn_ids": all_ids - kept_ids,
    }


def generic_summary(
    session: dict[str, Any], max_chars_per_turn: int = DEFAULT_MAX_CHARS_PER_TURN
) -> dict[str, Any]:
    """모든 turn을 동일한 길이로 잘라서 남긴다.

    task_relevance/importance와 무관하게 turn마다 같은 글자 수만 남기는
    방식이다. 의미를 이해하고 요약하는 것이 아니라 길이만 자르는 것이므로,
    잘린 지점에 따라 핵심 정보가 잘려나갈 수 있다. 이 한계는 의도적으로
    남겨둔다 — LLM 없이 규칙 기반으로 구현했기 때문이다(관련: 0006).
    """
    turns = session["turns"]
    lines = []
    for t in turns:
        text = t["text"]
        if len(text) > max_chars_per_turn:
            text = text[:max_chars_per_turn] + "…"
        lines.append(f"[{t['speaker']}] {text}")
    all_ids = {t["turn_id"] for t in turns}
    return {
        "method": "generic_summary",
        "text": "\n".join(lines),
        "in_context_turn_ids": all_ids,
        "retrievable_turn_ids": set(),
        "dropped_turn_ids": set(),
    }
