"""src/reconstruction_test.py 테스트."""

from __future__ import annotations

import unittest

from src.reconstruction_test import (
    build_ground_truth,
    evaluate_context,
    run_reconstruction_test,
)

EXAMPLE = {
    "items": [
        {
            "item_id": "g1",
            "category": "goal",
            "source_turn_ids": [1],
            "depends_on": [],
        },
        {
            "item_id": "e1",
            "category": "evidence",
            "source_turn_ids": [2],
            "depends_on": [],
        },
        {
            "item_id": "d1",
            "category": "decision",
            "source_turn_ids": [3],
            "depends_on": ["e1"],
        },
        {
            "item_id": "f1",
            "category": "failure",
            "source_turn_ids": [4],
            "depends_on": ["e1"],
        },
        {
            "item_id": "n1",
            "category": "next_action",
            "source_turn_ids": [5],
            "depends_on": [],
        },
    ]
}


class BuildGroundTruthTest(unittest.TestCase):
    def test_goal_maps_to_its_own_turn(self) -> None:
        gt = build_ground_truth(EXAMPLE)
        self.assertEqual(gt["현재 작업의 목표는?"], {1})

    def test_decision_reason_maps_to_dependency_turn(self) -> None:
        gt = build_ground_truth(EXAMPLE)
        # "결정 근거는?"은 d1 자신(turn 3)이 아니라 d1이 의존하는 e1(turn 2)이다.
        self.assertEqual(gt["결정 근거는?"], {2})

    def test_current_state_missing_from_example_is_empty(self) -> None:
        gt = build_ground_truth(EXAMPLE)
        self.assertEqual(gt["현재 상태는?"], set())


class EvaluateContextTest(unittest.TestCase):
    def test_in_context_turn_gives_pass(self) -> None:
        gt = {"q": {1, 2}}
        result = evaluate_context({"in_context_turn_ids": {2}, "retrievable_turn_ids": set()}, gt)
        self.assertEqual(result["q"]["verdict"], "PASS")

    def test_retrievable_only_gives_retrievable(self) -> None:
        gt = {"q": {1, 2}}
        result = evaluate_context({"in_context_turn_ids": set(), "retrievable_turn_ids": {1}}, gt)
        self.assertEqual(result["q"]["verdict"], "RETRIEVABLE")

    def test_neither_gives_fail(self) -> None:
        gt = {"q": {1, 2}}
        result = evaluate_context({"in_context_turn_ids": {9}, "retrievable_turn_ids": set()}, gt)
        self.assertEqual(result["q"]["verdict"], "FAIL")

    def test_empty_ground_truth_gives_no_ground_truth(self) -> None:
        gt = {"q": set()}
        result = evaluate_context({"in_context_turn_ids": {9}, "retrievable_turn_ids": set()}, gt)
        self.assertEqual(result["q"]["verdict"], "NO_GROUND_TRUTH")

    def test_in_context_takes_priority_over_retrievable(self) -> None:
        gt = {"q": {1, 2}}
        result = evaluate_context(
            {"in_context_turn_ids": {1}, "retrievable_turn_ids": {2}}, gt
        )
        self.assertEqual(result["q"]["verdict"], "PASS")
        self.assertEqual(result["q"]["matched_turn_ids"], [1])


class RunReconstructionTestTest(unittest.TestCase):
    def test_summary_counts_match_results(self) -> None:
        methods = {
            "m1": {"in_context_turn_ids": {1, 2, 3, 4, 5}, "retrievable_turn_ids": set()}
        }
        out = run_reconstruction_test(EXAMPLE, methods)
        total = sum(out["summary"]["m1"].values())
        self.assertEqual(total, len(out["results"]["m1"]))
        self.assertEqual(out["summary"]["m1"]["PASS"] + out["summary"]["m1"]["NO_GROUND_TRUTH"], total)


if __name__ == "__main__":
    unittest.main()
