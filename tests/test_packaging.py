"""pyproject.toml 패키징 설정 테스트.

pip install -e . 로 설치했을 때 만들어지는 `context-continuity-engine` 콘솔 스크립트가
가리키는 entry point(src.cli:main)가 실제로 존재하고 호출 가능한지 확인한다.
TOML 파서 의존성을 피하기 위해 파일 내용은 문자열로만 확인한다(decision 참조는
docs/decisions/0013-packaging.md).
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class PyprojectTest(unittest.TestCase):
    def test_pyproject_declares_console_script_entry_point(self) -> None:
        content = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("context-continuity-engine = \"src.cli:main\"", content)

    def test_entry_point_target_is_importable_and_callable(self) -> None:
        from src.cli import main

        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()
