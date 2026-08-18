"""src/cli.py 테스트."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from src.cli import _summary_line, build_parser, run

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "examples" / "groq_model_migration_session" / "session.json"


class BuildParserTest(unittest.TestCase):
    def test_requires_session_log_argument(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([])

    def test_json_flag_defaults_to_false(self) -> None:
        parser = build_parser()
        args = parser.parse_args([str(FIXTURE)])
        self.assertFalse(args.json)


class RunTest(unittest.TestCase):
    def test_run_produces_working_context_text(self) -> None:
        result = run(FIXTURE)
        self.assertIn("text", result["working_context"])
        self.assertGreater(len(result["working_context"]["text"]), 0)

    def test_run_raises_on_missing_file(self) -> None:
        with self.assertRaises(ValueError):
            run(REPO_ROOT / "examples" / "does_not_exist.json")

    def test_summary_line_mentions_turn_count(self) -> None:
        result = run(FIXTURE)
        line = _summary_line(result)
        self.assertIn(f"turn {result['session']['turn_count']}개", line)


class MainCliTest(unittest.TestCase):
    def _run_cli(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "src.cli", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

    def test_default_output_is_working_context_text(self) -> None:
        proc = self._run_cli([str(FIXTURE)])
        self.assertEqual(proc.returncode, 0)
        self.assertGreater(len(proc.stdout.strip()), 0)
        self.assertIn("token", proc.stderr)

    def test_json_flag_outputs_valid_json(self) -> None:
        proc = self._run_cli([str(FIXTURE), "--json"])
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIn("analysis", payload)
        self.assertIn("working_context", payload)

    def test_missing_file_returns_nonzero(self) -> None:
        proc = self._run_cli(["does_not_exist.json"])
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
