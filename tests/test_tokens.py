"""src/tokens.py 테스트."""

from __future__ import annotations

import unittest

from src.tokens import compute_cost, count_tokens, usage_report


class CountTokensTest(unittest.TestCase):
    def test_empty_string_is_zero(self) -> None:
        self.assertEqual(count_tokens(""), 0)

    def test_cjk_text_uses_smaller_divisor(self) -> None:
        # 같은 글자 수라도 한국어가 라틴 문자보다 token 수가 많이(더 촘촘하게) 나온다.
        cjk = "가" * 12
        latin = "a" * 12
        self.assertGreater(count_tokens(cjk), count_tokens(latin))

    def test_non_empty_short_text_is_at_least_one_token(self) -> None:
        self.assertGreaterEqual(count_tokens("a"), 1)

    def test_mixed_text_sums_both_groups(self) -> None:
        # 계산식이 실제로 두 그룹을 나눠서 더하는지 확인.
        mixed = "abcd" + "가"  # latin 4자(1 token) + cjk 1자(round(1/1.5)=1 token)
        self.assertEqual(count_tokens(mixed), 2)


class ComputeCostTest(unittest.TestCase):
    def test_no_pricing_returns_none(self) -> None:
        self.assertIsNone(compute_cost(1000, 500, None))

    def test_missing_price_key_returns_none(self) -> None:
        self.assertIsNone(compute_cost(1000, 500, {"input_price_per_1m": 1.0}))

    def test_cost_computed_from_pricing(self) -> None:
        pricing = {"input_price_per_1m": 2.0, "output_price_per_1m": 4.0}
        cost = compute_cost(1_000_000, 1_000_000, pricing)
        self.assertAlmostEqual(cost, 6.0)


class UsageReportTest(unittest.TestCase):
    def test_total_input_includes_analysis_tokens(self) -> None:
        report = usage_report("test", "abcd", analysis_input_tokens=10, analysis_output_tokens=5)
        self.assertEqual(report["total_input_tokens"], report["context_tokens"] + 10)
        self.assertEqual(report["total_tokens"], report["total_input_tokens"] + 5)

    def test_no_pricing_gives_none_cost(self) -> None:
        report = usage_report("test", "abcd")
        self.assertIsNone(report["cost"])


if __name__ == "__main__":
    unittest.main()
