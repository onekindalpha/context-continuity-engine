"""src/ingest.py 테스트.

평가 목적: ingest 출력 schema(ok/session/error, turns[])가 TXT/Markdown/JSON
입력에서 일관되게 나오는지 검증한다. 이후 단계(Task Context Analysis 등)가
이 schema에 의존하므로 여기서 계약을 고정한다.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from src.ingest import ingest_file, ingest_json, ingest_markdown, ingest_txt

FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "groq_model_migration_session"
)
EXPECTED_TURN_COUNT = 20


class TxtInputTest(unittest.TestCase):
    def test_valid_txt_produces_expected_turns(self) -> None:
        result = ingest_file(FIXTURE_DIR / "session.txt")
        self.assertTrue(result["ok"], result.get("error"))
        session = result["session"]
        self.assertEqual(session["source_format"], "txt")
        self.assertEqual(session["turn_count"], EXPECTED_TURN_COUNT)
        first = session["turns"][0]
        self.assertEqual(first["speaker"], "user")
        self.assertEqual(first["timestamp"], "2026-08-17T12:59:02Z")
        self.assertEqual(first["text"], "근데 pdf 안넣어져")
        last = session["turns"][-1]
        self.assertIn("전체 방향을 먼저 설명", last["text"])


class MarkdownInputTest(unittest.TestCase):
    def test_valid_markdown_produces_expected_turns(self) -> None:
        result = ingest_file(FIXTURE_DIR / "session.md")
        self.assertTrue(result["ok"], result.get("error"))
        session = result["session"]
        self.assertEqual(session["source_format"], "markdown")
        self.assertEqual(session["turn_count"], EXPECTED_TURN_COUNT)
        first = session["turns"][0]
        self.assertEqual(first["speaker"], "user")
        self.assertEqual(first["text"], "근데 pdf 안넣어져")


class JsonInputTest(unittest.TestCase):
    def test_valid_json_produces_expected_turns(self) -> None:
        result = ingest_file(FIXTURE_DIR / "session.json")
        self.assertTrue(result["ok"], result.get("error"))
        session = result["session"]
        self.assertEqual(session["source_format"], "json")
        self.assertEqual(session["session_id"], "groq-model-migration-2026-08-17")
        self.assertEqual(session["turn_count"], EXPECTED_TURN_COUNT)

    def test_txt_and_json_fixtures_hold_same_content(self) -> None:
        txt_turns = ingest_file(FIXTURE_DIR / "session.txt")["session"]["turns"]
        json_turns = ingest_file(FIXTURE_DIR / "session.json")["session"]["turns"]
        self.assertEqual(len(txt_turns), len(json_turns))
        for txt_turn, json_turn in zip(txt_turns, json_turns):
            self.assertEqual(txt_turn["speaker"], json_turn["speaker"])
            self.assertEqual(txt_turn["text"], json_turn["text"])


class InvalidJsonTest(unittest.TestCase):
    def test_malformed_json_returns_error(self) -> None:
        result = ingest_json('{"turns": [')
        self.assertFalse(result["ok"])
        self.assertIsNone(result["session"])
        self.assertIn("invalid JSON", result["error"])

    def test_non_object_json_returns_error(self) -> None:
        result = ingest_json("[1, 2, 3]")
        self.assertFalse(result["ok"])
        self.assertIn("invalid JSON", result["error"])


class EmptySessionTest(unittest.TestCase):
    def test_empty_json_turns_is_ok_with_warning(self) -> None:
        result = ingest_json('{"turns": []}')
        self.assertTrue(result["ok"], result.get("error"))
        session = result["session"]
        self.assertEqual(session["turn_count"], 0)
        self.assertIn("session has no turns", session["warnings"])

    def test_empty_txt_is_ok_with_warning(self) -> None:
        result = ingest_txt("")
        self.assertTrue(result["ok"], result.get("error"))
        session = result["session"]
        self.assertEqual(session["turn_count"], 0)
        self.assertIn("session has no turns", session["warnings"])

    def test_empty_markdown_is_ok_with_warning(self) -> None:
        result = ingest_markdown("")
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["session"]["turn_count"], 0)


class MissingRequiredFieldTest(unittest.TestCase):
    def test_json_turn_missing_text_returns_error(self) -> None:
        result = ingest_json('{"turns": [{"speaker": "user"}]}')
        self.assertFalse(result["ok"])
        self.assertIsNone(result["session"])
        self.assertIn("missing required field: text at turn 0", result["error"])

    def test_json_turn_missing_speaker_returns_error(self) -> None:
        result = ingest_json('{"turns": [{"text": "hello"}]}')
        self.assertFalse(result["ok"])
        self.assertIn("missing required field: speaker at turn 0", result["error"])

    def test_json_missing_turns_key_returns_error(self) -> None:
        result = ingest_json('{"session_id": "x"}')
        self.assertFalse(result["ok"])
        self.assertIn("missing required field: turns", result["error"])


class UnknownSpeakerTest(unittest.TestCase):
    def test_unrecognized_speaker_normalizes_to_unknown(self) -> None:
        result = ingest_json('{"turns": [{"speaker": "system", "text": "note"}]}')
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["session"]["turns"][0]["speaker"], "unknown")


class FileHandlingTest(unittest.TestCase):
    def test_missing_file_returns_error(self) -> None:
        result = ingest_file(FIXTURE_DIR / "does_not_exist.json")
        self.assertFalse(result["ok"])
        self.assertIn("file not found", result["error"])

    def test_unsupported_extension_returns_error(self) -> None:
        result = ingest_file(Path(__file__))  # this .py file itself
        self.assertFalse(result["ok"])
        self.assertIn("unsupported file extension", result["error"])


if __name__ == "__main__":
    unittest.main()
