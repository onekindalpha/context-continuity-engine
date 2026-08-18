"""src/baseline.py 테스트."""

from __future__ import annotations

import unittest

from src.baseline import generic_summary, recency_truncation


def _session(n_turns: int) -> dict:
    return {
        "turns": [
            {
                "turn_id": i,
                "speaker": "user" if i % 2 == 0 else "assistant",
                "timestamp": f"2026-01-01T00:00:{i:02d}Z",
                "text": f"turn {i} content " * 3,
            }
            for i in range(n_turns)
        ]
    }


class RecencyTruncationTest(unittest.TestCase):
    def test_keeps_only_last_n_turns(self) -> None:
        session = _session(10)
        result = recency_truncation(session, keep_last_n_turns=3)
        self.assertEqual(result["in_context_turn_ids"], {7, 8, 9})
        self.assertEqual(result["dropped_turn_ids"], set(range(7)))
        self.assertEqual(result["retrievable_turn_ids"], set())

    def test_dropped_turns_are_not_retrievable(self) -> None:
        session = _session(5)
        result = recency_truncation(session, keep_last_n_turns=2)
        # 버려진 turn은 어디에도 없다 — retrieval 경로가 없다.
        self.assertFalse(result["dropped_turn_ids"] & result["retrievable_turn_ids"])

    def test_keep_more_than_available_keeps_all(self) -> None:
        session = _session(3)
        result = recency_truncation(session, keep_last_n_turns=10)
        self.assertEqual(result["in_context_turn_ids"], {0, 1, 2})
        self.assertEqual(result["dropped_turn_ids"], set())

    def test_text_contains_only_kept_turns(self) -> None:
        session = _session(4)
        result = recency_truncation(session, keep_last_n_turns=1)
        self.assertIn("turn 3 content", result["text"])
        self.assertNotIn("turn 0 content", result["text"])


class GenericSummaryTest(unittest.TestCase):
    def test_all_turns_present_but_truncated(self) -> None:
        session = _session(3)
        result = generic_summary(session, max_chars_per_turn=10)
        self.assertEqual(result["in_context_turn_ids"], {0, 1, 2})
        self.assertEqual(result["dropped_turn_ids"], set())

    def test_short_turn_not_truncated(self) -> None:
        session = {
            "turns": [
                {"turn_id": 0, "speaker": "user", "timestamp": "t", "text": "짧음"}
            ]
        }
        result = generic_summary(session, max_chars_per_turn=100)
        self.assertIn("짧음", result["text"])
        self.assertNotIn("…", result["text"])

    def test_long_turn_is_truncated_with_marker(self) -> None:
        session = _session(1)
        result = generic_summary(session, max_chars_per_turn=5)
        self.assertIn("…", result["text"])


if __name__ == "__main__":
    unittest.main()
