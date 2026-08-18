"""Reconstruction Test: 고정된 7개 질문에 각 context가 답할 근거를
포함하는지 기계적으로 확인한다.

평가 목적: retention_action이 실제로 "작업 연속성"을 보존하는지 확인해야
한다(docs/evaluation.md). LLM으로 의미를 판정하지 않는다 — 이 환경에 LLM
API 자격증명이 없고, 판정 기준을 재현 가능하게 유지하기 위함이다
(docs/decisions/0006 연장선, 상세 이유는 0010 참조).

방법(근사): 사람이 직접 만든 예시(task_context_analysis.example.json)를
정답으로 삼는다. 질문이 어떤 category의 어떤 turn에서 답을 얻어야 하는지는
그 예시의 category와 depends_on으로 정한다. 이후 각 context 방식(baseline
recency truncation, baseline generic summary, 제안 Working Context)이 그
turn의 내용을 직접 포함하는지(in_context) 또는 나중에 조회 가능한지
(retrievable)만 본다.

한계: turn 내용이 "포함되어 있다"는 것과 "그 내용으로 실제 질문에 답할 수
있다"는 것은 다르다. 이 test는 전자만 확인한다. 후자(의미적 답변 가능
여부)는 사람 또는 LLM 판정이 필요하며, 이 단계에서는 하지 않는다.
"""

from __future__ import annotations

from typing import Any

QUESTIONS = [
    "현재 작업의 목표는?",
    "현재 상태는?",
    "핵심 결정은?",
    "결정 근거는?",
    "실패한 접근은?",
    "실패 이유는?",
    "다음 작업은?",
]

_QUESTION_CATEGORY = {
    "현재 작업의 목표는?": "goal",
    "현재 상태는?": "current_state",
    "핵심 결정은?": "decision",
    "결정 근거는?": "decision",
    "실패한 접근은?": "failure",
    "실패 이유는?": "failure",
    "다음 작업은?": "next_action",
}

# "근거"/"이유" 질문은 해당 category 항목 자신이 아니라, 그 항목이
# 의존하는(depends_on) 항목의 turn을 정답으로 본다. 결정/실패의 이유는
# 보통 그 결정/실패가 참조한 근거(evidence/current_state 등)에 있다는
# 가정이다 — 이 가정은 검증되지 않았다.
_USE_DEPENDENCY = {
    "결정 근거는?": True,
    "실패 이유는?": True,
}


def build_ground_truth(example: dict[str, Any]) -> dict[str, set[int]]:
    """사람이 만든 예시에서 질문별 정답 turn_id 집합을 만든다."""
    items_by_id = {item["item_id"]: item for item in example["items"]}

    def turns_of(item: dict[str, Any]) -> set[int]:
        return set(item["source_turn_ids"])

    ground_truth: dict[str, set[int]] = {}
    for question, category in _QUESTION_CATEGORY.items():
        matching = [item for item in example["items"] if item["category"] == category]
        if _USE_DEPENDENCY.get(question):
            turns: set[int] = set()
            for item in matching:
                for dep_id in item.get("depends_on", []):
                    dep = items_by_id.get(dep_id)
                    if dep:
                        turns |= turns_of(dep)
            ground_truth[question] = turns
        else:
            turns = set()
            for item in matching:
                turns |= turns_of(item)
            ground_truth[question] = turns
    return ground_truth


def evaluate_context(
    context_result: dict[str, Any], ground_truth: dict[str, set[int]]
) -> dict[str, dict[str, Any]]:
    """질문마다 PASS(즉시 답변 가능)/RETRIEVABLE(조회하면 가능)/FAIL/NO_GROUND_TRUTH를 매긴다."""
    in_context = context_result.get("in_context_turn_ids", set())
    retrievable = context_result.get("retrievable_turn_ids", set())

    results: dict[str, dict[str, Any]] = {}
    for question, truth_turns in ground_truth.items():
        if not truth_turns:
            results[question] = {"verdict": "NO_GROUND_TRUTH", "matched_turn_ids": []}
            continue
        matched_in_context = truth_turns & in_context
        matched_retrievable = (truth_turns & retrievable) - matched_in_context
        if matched_in_context:
            results[question] = {
                "verdict": "PASS",
                "matched_turn_ids": sorted(matched_in_context),
            }
        elif matched_retrievable:
            results[question] = {
                "verdict": "RETRIEVABLE",
                "matched_turn_ids": sorted(matched_retrievable),
            }
        else:
            results[question] = {"verdict": "FAIL", "matched_turn_ids": []}
    return results


def run_reconstruction_test(
    example: dict[str, Any], methods: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """methods: {method_name: context_result} → 방법별/질문별 결과 + 요약."""
    ground_truth = build_ground_truth(example)
    results = {
        name: evaluate_context(result, ground_truth) for name, result in methods.items()
    }
    summary = {}
    for name, per_question in results.items():
        counts = {"PASS": 0, "RETRIEVABLE": 0, "FAIL": 0, "NO_GROUND_TRUTH": 0}
        for verdict in per_question.values():
            counts[verdict["verdict"]] += 1
        summary[name] = counts
    return {
        "ground_truth_turn_ids": {q: sorted(t) for q, t in ground_truth.items()},
        "results": results,
        "summary": summary,
    }
