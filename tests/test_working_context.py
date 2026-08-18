"""src/working_context.py 테스트."""

from __future__ import annotations

import unittest

from src.working_context import build_working_context, turn_coverage

SESSION = {
    "turns": [
        {"turn_id": 0, "speaker": "user", "timestamp": "t0", "text": "keep me verbatim"},
        {"turn_id": 1, "speaker": "assistant", "timestamp": "t1", "text": "compress me please"},
        {"turn_id": 2, "speaker": "user", "timestamp": "t2", "text": "externalize me"},
        {"turn_id": 3, "speaker": "assistant", "timestamp": "t3", "text": "discard me"},
    ]
}

ANALYSIS = {
    "items": [
        {
            "item_id": "i1",
            "category": "current_state",
            "summary": "keep summary",
            "source_turn_ids": [0],
            "retention_action": "KEEP",
        },
        {
            "item_id": "i2",
            "category": "evidence",
            "summary": "compressed summary",
            "source_turn_ids": [1],
            "retention_action": "COMPRESS",
        },
        {
            "item_id": "i3",
            "category": "evidence",
            "summary": "external summary",
            "source_turn_ids": [2],
            "retention_action": "EXTERNALIZE",
        },
        {
            "item_id": "i4",
            "category": "evidence",
            "summary": "discard summary",
            "source_turn_ids": [3],
            "retention_action": "DISCARD",
        },
    ]
}


class BuildWorkingContextTest(unittest.TestCase):
    def test_keep_includes_original_text(self) -> None:
        result = build_working_context(ANALYSIS, SESSION)
        self.assertIn("keep me verbatim", result["text"])

    def test_compress_includes_summary_not_original(self) -> None:
        result = build_working_context(ANALYSIS, SESSION)
        self.assertIn("compressed summary", result["text"])
        self.assertNotIn("compress me please", result["text"])

    def test_externalize_includes_reference_and_stores_original(self) -> None:
        result = build_working_context(ANALYSIS, SESSION)
        self.assertNotIn("externalize me", result["text"])
        self.assertIn("i3", result["external_store"])
        self.assertIn("externalize me", result["external_store"]["i3"]["original_texts"])

    def test_discard_appears_nowhere(self) -> None:
        result = build_working_context(ANALYSIS, SESSION)
        self.assertNotIn("discard me", result["text"])
        self.assertNotIn("i4", result["external_store"])
        self.assertNotIn("i4", result["included_item_ids"])

    def test_action_counts(self) -> None:
        result = build_working_context(ANALYSIS, SESSION)
        self.assertEqual(
            result["action_counts"],
            {"KEEP": 1, "COMPRESS": 1, "EXTERNALIZE": 1, "DISCARD": 1},
        )


class TurnCoverageTest(unittest.TestCase):
    def test_keep_and_compress_are_in_context(self) -> None:
        coverage = turn_coverage(ANALYSIS)
        self.assertEqual(coverage["in_context_turn_ids"], {0, 1})

    def test_externalize_is_retrievable_not_in_context(self) -> None:
        coverage = turn_coverage(ANALYSIS)
        self.assertEqual(coverage["retrievable_turn_ids"], {2})
        self.assertNotIn(2, coverage["in_context_turn_ids"])

    def test_discard_is_in_neither_set(self) -> None:
        coverage = turn_coverage(ANALYSIS)
        self.assertNotIn(3, coverage["in_context_turn_ids"])
        self.assertNotIn(3, coverage["retrievable_turn_ids"])


if __name__ == "__main__":
    unittest.main()
