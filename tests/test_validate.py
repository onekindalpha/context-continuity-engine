"""src/validate.py 테스트."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.ingest import ingest_file
from src.validate import validate_analysis

FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "groq_model_migration_session"
)


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _load_session() -> dict:
    # validate_analysis expects ingest OUTPUT (has turn_id per turn), not the
    # raw session.json input file.
    result = ingest_file(FIXTURE_DIR / "session.json")
    assert result["ok"], result["error"]
    return result["session"]


class ValidAnalysisTest(unittest.TestCase):
    def test_hand_built_example_is_valid(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        session = _load_session()
        result = validate_analysis(analysis, session=session)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["errors"], [])

    def test_valid_without_session_argument(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        result = validate_analysis(analysis)
        self.assertTrue(result["ok"], result["errors"])


class MissingFieldTest(unittest.TestCase):
    def test_missing_top_level_field(self) -> None:
        result = validate_analysis({"schema_version": "1", "items": []})
        self.assertFalse(result["ok"])
        self.assertIn("missing required field: session_id", result["errors"])

    def test_missing_item_field(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        del analysis["items"][0]["summary"]
        result = validate_analysis(analysis)
        self.assertFalse(result["ok"])
        self.assertTrue(any("missing required field: summary" in e for e in result["errors"]))


class InvalidCategoryTest(unittest.TestCase):
    def test_unknown_category_rejected(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        analysis["items"][0]["category"] = "dependency"
        result = validate_analysis(analysis)
        self.assertFalse(result["ok"])
        self.assertTrue(any("invalid category" in e for e in result["errors"]))


class DanglingDependencyTest(unittest.TestCase):
    def test_depends_on_unknown_item_rejected(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        analysis["items"][0]["depends_on"] = ["item-9999"]
        result = validate_analysis(analysis)
        self.assertFalse(result["ok"])
        self.assertTrue(any("unknown item_id" in e for e in result["errors"]))

    def test_self_dependency_rejected(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        analysis["items"][0]["depends_on"] = [analysis["items"][0]["item_id"]]
        result = validate_analysis(analysis)
        self.assertFalse(result["ok"])
        self.assertTrue(any("references itself" in e for e in result["errors"]))


class DuplicateItemIdTest(unittest.TestCase):
    def test_duplicate_item_id_rejected(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        analysis["items"][1]["item_id"] = analysis["items"][0]["item_id"]
        result = validate_analysis(analysis)
        self.assertFalse(result["ok"])
        self.assertTrue(any("duplicate item_id" in e for e in result["errors"]))


class OutOfRangeTurnIdTest(unittest.TestCase):
    def test_turn_id_out_of_session_range_rejected(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        session = _load_session()
        analysis["items"][0]["source_turn_ids"] = [9999]
        result = validate_analysis(analysis, session=session)
        self.assertFalse(result["ok"])
        self.assertTrue(any("out of range" in e for e in result["errors"]))

    def test_turn_id_out_of_range_ignored_without_session(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        analysis["items"][0]["source_turn_ids"] = [9999]
        result = validate_analysis(analysis)
        self.assertTrue(result["ok"], result["errors"])


class CycleDetectionTest(unittest.TestCase):
    def test_two_item_cycle_rejected(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        a, b = analysis["items"][0], analysis["items"][1]
        a["depends_on"] = [b["item_id"]]
        b["depends_on"] = [a["item_id"]]
        result = validate_analysis(analysis)
        self.assertFalse(result["ok"])
        self.assertTrue(any("cycle" in e for e in result["errors"]))


class InvalidScoreTest(unittest.TestCase):
    def test_importance_out_of_unit_range_rejected(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        analysis["items"][0]["importance"] = 1.5
        result = validate_analysis(analysis)
        self.assertFalse(result["ok"])
        self.assertTrue(any("importance" in e for e in result["errors"]))

    def test_null_scores_are_allowed(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        result = validate_analysis(analysis)
        self.assertTrue(result["ok"], result["errors"])


class InvalidRetentionActionTest(unittest.TestCase):
    def test_unknown_retention_action_rejected(self) -> None:
        analysis = _load("task_context_analysis.example.json")
        analysis["items"][0]["retention_action"] = "MAYBE"
        result = validate_analysis(analysis)
        self.assertFalse(result["ok"])
        self.assertTrue(any("invalid retention_action" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
