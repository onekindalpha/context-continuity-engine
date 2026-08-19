"""주어진 token budget 안에서 context를 만드는 두 가지 방식.

- `generic_summary_under_budget`: turn마다 같은 글자 수로 자른다(구조 무시).
  budget에 맞추기 위해 turn당 글자 수를 이분 탐색으로 조정한다.
- `structured_summary_under_budget`: CCE의 category / importance /
  task_relevance / depends_on을 이용해 **무엇을 먼저 넣을지** 정하고,
  각 항목은 category를 드러내는 핵심 문장만 남긴다.

두 방식 모두 같은 SessionLog와 같은 budget을 받는다. 차이는 오직
"같은 예산을 어떻게 배분하는가"뿐이다 - 이게 이 실험의 질문이다.

`src/`는 건드리지 않는다. 기존 파이프라인/테스트에 영향이 없도록 실험
디렉토리 안에서만 동작한다.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.tokens import count_tokens  # noqa: E402
from src.context_analysis import (  # noqa: E402
    FAILURE_PATTERNS,
    DECISION_PATTERNS,
    EVIDENCE_PATTERNS,
    GOAL_PATTERNS,
    NEXT_ACTION_PATTERNS,
    CURRENT_STATE_PATTERNS,
)

# 질문 7개가 필요로 하는 정보 종류 기준의 우선순위.
# 낮을수록 먼저 넣는다. reconstruction 질문(목표/상태/결정/근거/실패/이유/다음)에
# 직접 대응하는 category를 앞에 둔다.
CATEGORY_PRIORITY = {
    "goal": 0,
    "next_action": 1,
    "current_state": 2,
    "decision": 3,
    "failure": 4,
    "evidence": 5,
}

CATEGORY_PATTERNS = {
    "failure": FAILURE_PATTERNS,
    "decision": DECISION_PATTERNS,
    "evidence": EVIDENCE_PATTERNS,
    "goal": GOAL_PATTERNS,
    "next_action": NEXT_ACTION_PATTERNS,
    "current_state": CURRENT_STATE_PATTERNS,
}

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。])\s+|\n+")


def _split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return parts or [text.strip()]


def _cut_at_word_boundary(text: str, max_chars: int) -> str:
    """max_chars 안에서 단어 경계로 자른다. 공백이 없으면 글자 수로 자른다."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_chars:
        return collapsed
    cut = collapsed.rfind(" ", 0, max_chars)
    if cut <= 0:
        cut = max_chars
    return collapsed[:cut].rstrip() + "..."


def informative_excerpt(text: str, category: str, max_chars: int) -> str:
    """category를 드러내는 문장을 우선 남긴다(앞 N자 자르기가 아니라).

    이유: 기존 `_make_summary`는 turn의 **앞부분**만 남긴다. 그런데 개발 대화에서
    핵심(무엇이 실패했는지, 무엇을 결정했는지)은 문장 중간이나 뒤에 오는 경우가
    많다. category 분류를 유발한 패턴이 들어있는 문장을 고르면, 같은 글자 수로
    더 많은 판단 정보를 남길 수 있다.
    """
    sentences = _split_sentences(text)
    patterns = CATEGORY_PATTERNS.get(category, [])

    def score(s: str) -> tuple[int, int]:
        hits = sum(1 for p in patterns if re.search(p, s, flags=re.IGNORECASE))
        # 동점이면 정보 밀도(영문 식별자/숫자 포함 여부)가 높은 쪽을 선호
        dense = len(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}|[0-9]+", s))
        return (hits, dense)

    best = max(sentences, key=score)
    if score(best) == (0, 0):
        best = sentences[0]
    return _cut_at_word_boundary(best, max_chars)


def generic_summary_under_budget(session: dict[str, Any], budget_tokens: int) -> dict[str, Any]:
    """turn마다 동일한 글자 수로 자르되, 전체가 budget 이하가 되도록 맞춘다."""
    turns = session["turns"]

    def build(max_chars: int) -> str:
        lines = []
        for t in turns:
            collapsed = " ".join(t["text"].split())
            if len(collapsed) > max_chars:
                collapsed = collapsed[:max_chars] + "…"
            lines.append(f"[{t['speaker']}] {collapsed}")
        return "\n".join(lines)

    lo, hi, best = 1, 400, build(1)
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = build(mid)
        if count_tokens(candidate) <= budget_tokens:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return {"method": "generic_summary", "text": best, "budget_tokens": budget_tokens}


def structured_summary_under_budget(
    analysis: dict[str, Any], session: dict[str, Any], budget_tokens: int
) -> dict[str, Any]:
    """category/importance/dependency를 이용해 budget 안에서 정보를 배분한다.

    전략:
    1. DISCARD가 아닌 item을 (category 우선순위, importance 내림차순, 최신순)으로 정렬.
    2. 예산이 남는 동안 항목을 추가한다. 각 항목은 우선 짧은 excerpt(핵심 문장)로 넣는다.
    3. 모든 category가 한 번씩 들어간 뒤에도 예산이 남으면, 남은 예산으로 이미 들어간
       항목의 excerpt 길이를 늘린다(중요도 높은 것부터).
    4. depends_on으로 참조되는 항목은 우선순위를 한 단계 올린다 - 그 항목이 빠지면
       "근거는?" 질문에 답할 수 없기 때문이다.
    """
    turns_by_id = {t["turn_id"]: t for t in session["turns"]}
    items = [i for i in analysis["items"] if i.get("retention_action") != "DISCARD"]

    referenced: set[str] = set()
    for i in analysis["items"]:
        for dep in i.get("depends_on", []) or []:
            referenced.add(dep)

    def sort_key(item: dict[str, Any]) -> tuple:
        cat_rank = CATEGORY_PRIORITY.get(item["category"], 9)
        if item["item_id"] in referenced:
            cat_rank -= 1  # 다른 항목이 근거로 참조하면 먼저 넣는다
        return (cat_rank, -(item.get("importance") or 0.0), -(item.get("turn_id") or 0))

    ordered = sorted(items, key=sort_key)

    def text_of(item: dict[str, Any]) -> str:
        parts = [
            turns_by_id[t]["text"] for t in item["source_turn_ids"] if t in turns_by_id
        ]
        return " ".join(parts)

    SHORT, STEP, MAX_CHARS = 70, 60, 400
    lengths: dict[str, int] = {}
    selected: list[dict[str, Any]] = []

    def render(sel: list[dict[str, Any]], lens: dict[str, int]) -> str:
        return "\n".join(
            f"[{i['category']}] {informative_excerpt(text_of(i), i['category'], lens[i['item_id']])}"
            for i in sel
        )

    # 1단계: 우선순위 순으로 넣을 수 있는 만큼 넣는다.
    for item in ordered:
        trial_sel = selected + [item]
        trial_lens = dict(lengths)
        trial_lens[item["item_id"]] = SHORT
        if count_tokens(render(trial_sel, trial_lens)) <= budget_tokens:
            selected, lengths = trial_sel, trial_lens

    # 2단계: 예산이 남으면 중요한 항목부터 길이를 늘린다.
    improved = True
    while improved:
        improved = False
        for item in selected:
            iid = item["item_id"]
            if lengths[iid] >= MAX_CHARS:
                continue
            trial_lens = dict(lengths)
            trial_lens[iid] = lengths[iid] + STEP
            if count_tokens(render(selected, trial_lens)) <= budget_tokens:
                lengths = trial_lens
                improved = True

    return {
        "method": "cce_structured",
        "text": render(selected, lengths),
        "budget_tokens": budget_tokens,
        "included_item_ids": [i["item_id"] for i in selected],
        "included_categories": sorted({i["category"] for i in selected}),
    }
