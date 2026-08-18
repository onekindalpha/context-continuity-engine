"""src/context_analysis.py 테스트."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.context_analysis import build_analysis, classify_turn
from src.ingest import ingest_file
from src.validate import validate_analysis

FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "groq_model_migration_session"
)


class ClassifyTurnTest(unittest.TestCase):
    def test_failure_keyword_detected(self) -> None:
        self.assertEqual(
            classify_turn("user", "Error code: 404, model not found", is_last_turn=False),
            "failure",
        )

    def test_current_state_needs_hash_and_phrase_together(self) -> None:
        self.assertEqual(
            classify_turn("assistant", "커밋 완료했습니다 (abc1234)", is_last_turn=False),
            "current_state",
        )

    def test_hash_alone_is_not_current_state(self) -> None:
        # 해시만 있고 "완료" 계열 문구가 없으면 current_state로 분류하지 않는다.
        result = classify_turn("user", "commit abc1234 added feature x", is_last_turn=False)
        self.assertNotEqual(result, "current_state")

    def test_last_user_turn_is_next_action(self) -> None:
        self.assertEqual(
            classify_turn("user", "아무 키워드도 없는 문장", is_last_turn=True),
            "next_action",
        )

    def test_short_user_turn_falls_back_to_evidence(self) -> None:
        self.assertEqual(classify_turn("user", "음 그렇군요", is_last_turn=False), "evidence")

    def test_unmatched_long_turn_returns_none(self) -> None:
        text = "이 문장은 어떤 규칙 키워드에도 걸리지 않도록 일부러 길게 작성한 일반 서술문입니다"
        self.assertIsNone(classify_turn("assistant", text, is_last_turn=False))

    def test_decision_keyword_detected_for_assistant(self) -> None:
        self.assertEqual(
            classify_turn("assistant", "이 방식으로 진행하기로 결정합니다", is_last_turn=False),
            "decision",
        )


class BuildAnalysisOnFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        result = ingest_file(FIXTURE_DIR / "session.json")
        assert result["ok"], result["error"]
        cls.session = result["session"]
        cls.analysis = build_analysis(cls.session)

    def test_output_is_schema_valid(self) -> None:
        result = validate_analysis(self.analysis, session=self.session)
        self.assertTrue(result["ok"], result["errors"])

    def test_deterministic_across_runs(self) -> None:
        second = build_analysis(self.session)
        self.assertEqual(self.analysis, second)

    def test_every_item_has_provenance(self) -> None:
        for item in self.analysis["items"]:
            self.assertTrue(item["source_turn_ids"])
            for tid in item["source_turn_ids"]:
                self.assertTrue(0 <= tid <= self.session["turn_count"] - 1)

    def test_every_retention_action_has_reason(self) -> None:
        for item in self.analysis["items"]:
            self.assertIsNotNone(item["retention_action"])
            self.assertTrue(item["retention_reason"])

    def test_importance_and_task_relevance_are_not_always_equal(self) -> None:
        # importance와 task_relevance를 같은 점수로 취급하지 않는다는 요구 조건 확인.
        differing = [
            item
            for item in self.analysis["items"]
            if item["importance"] != item["task_relevance"]
        ]
        self.assertTrue(differing, "importance와 task_relevance가 모든 item에서 동일함")

    def test_items_with_dependents_are_not_discarded(self) -> None:
        dependent_targets = {
            dep for item in self.analysis["items"] for dep in item["depends_on"]
        }
        for item in self.analysis["items"]:
            if item["item_id"] in dependent_targets:
                self.assertNotEqual(item["retention_action"], "DISCARD")


if __name__ == "__main__":
    unittest.main()
