"""src/raw_text_convert.py 테스트."""

from __future__ import annotations

import unittest

from src.raw_text_convert import convert


class ConvertTest(unittest.TestCase):
    def test_basic_two_turns(self) -> None:
        text = "user: 안녕\nassistant: 네 안녕하세요"
        result = convert(text)
        self.assertEqual(
            result["turns"],
            [
                {"speaker": "user", "text": "안녕"},
                {"speaker": "assistant", "text": "네 안녕하세요"},
            ],
        )
        self.assertEqual(result["warnings"], [])

    def test_korean_aliases_recognized(self) -> None:
        text = "나: 질문입니다\n클로드: 답변입니다"
        result = convert(text)
        self.assertEqual(result["turns"][0]["speaker"], "user")
        self.assertEqual(result["turns"][1]["speaker"], "assistant")

    def test_full_width_colon_recognized(self) -> None:
        text = "user：안녕"
        result = convert(text)
        self.assertEqual(result["turns"][0]["text"], "안녕")

    def test_multiline_turn_accumulates(self) -> None:
        text = "assistant: 첫 줄\n두 번째 줄\nuser: 다음 turn"
        result = convert(text)
        self.assertEqual(result["turns"][0]["text"], "첫 줄\n두 번째 줄")

    def test_content_before_first_speaker_is_warned_and_dropped(self) -> None:
        text = "아무 표시 없는 줄\nuser: 진짜 시작"
        result = convert(text)
        self.assertEqual(len(result["turns"]), 1)
        self.assertTrue(any("무시됨" in w for w in result["warnings"]))

    def test_no_recognized_speaker_gives_empty_turns_and_warning(self) -> None:
        result = convert("아무 형식도 아닌 텍스트")
        self.assertEqual(result["turns"], [])
        self.assertTrue(result["warnings"])

    def test_case_insensitive_speaker(self) -> None:
        result = convert("USER: 대문자로 시작")
        self.assertEqual(result["turns"][0]["speaker"], "user")

    def test_unrecognized_alias_line_is_not_a_new_turn(self) -> None:
        # "질문자:"는 등록된 별칭이 아니므로 새 turn으로 인식되면 안 된다.
        text = "user: 시작\n질문자: 이건 그냥 본문 안 텍스트"
        result = convert(text)
        self.assertEqual(len(result["turns"]), 1)
        self.assertIn("질문자:", result["turns"][0]["text"])


if __name__ == "__main__":
    unittest.main()
