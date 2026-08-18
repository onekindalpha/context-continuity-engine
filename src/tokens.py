"""Token 수와 비용 계산.

평가 목적: 제안 방식이 실제로 비용을 줄이는지 판단하려면 분석 단계의 비용까지
포함한 전체 token을 재야 한다(docs/evaluation.md).

의존성: 표준 라이브러리만 사용한다. tiktoken을 쓰지 않는 이유는
docs/decisions/0007-token-counting-method.md 참조.
"""

from __future__ import annotations

import re
from typing import Any

# 근사 계수. 정확한 tokenizer가 아니다. 한계는 0007 결정 문서에 기록.
CHARS_PER_TOKEN_LATIN = 4.0
CHARS_PER_TOKEN_CJK = 1.5

CJK_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")


def count_tokens(text: str) -> int:
    """문자 종류별 근사 계수로 token 수를 추정한다.

    한국어/한자/일본어는 라틴 문자보다 token당 문자 수가 적다. 두 그룹을
    나눠 세면 단일 계수보다 오차가 작다.
    """
    if not text:
        return 0
    cjk_chars = len(CJK_RE.findall(text))
    other_chars = len(text) - cjk_chars
    estimate = cjk_chars / CHARS_PER_TOKEN_CJK + other_chars / CHARS_PER_TOKEN_LATIN
    return max(1, round(estimate))


def compute_cost(
    input_tokens: int,
    output_tokens: int,
    pricing: dict[str, float] | None,
) -> float | None:
    """pricing이 없으면 None을 반환한다(비용 계산 생략, token 수만 보고).

    pricing 단위: 1M token당 가격. docs/evaluation.md의 식과 동일하다.
    """
    if not pricing:
        return None
    input_price = pricing.get("input_price_per_1m")
    output_price = pricing.get("output_price_per_1m")
    if input_price is None or output_price is None:
        return None
    return (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price


def usage_report(
    label: str,
    context_text: str,
    analysis_input_tokens: int = 0,
    analysis_output_tokens: int = 0,
    pricing: dict[str, float] | None = None,
) -> dict[str, Any]:
    """한 방식(baseline 또는 proposed)의 token 사용량을 정리한다.

    analysis_* 는 context를 만들기 위해 추가로 쓴 token이다. 규칙 기반
    구현에서는 0이다(LLM 호출 없음). LLM 기반 구현으로 바꾸면 여기에 실제
    사용량이 들어가고, 그때 비용 우위가 유지되는지 다시 판단해야 한다.
    """
    context_tokens = count_tokens(context_text)
    total_input = context_tokens + analysis_input_tokens
    total_tokens = total_input + analysis_output_tokens
    return {
        "label": label,
        "context_tokens": context_tokens,
        "analysis_input_tokens": analysis_input_tokens,
        "analysis_output_tokens": analysis_output_tokens,
        "total_input_tokens": total_input,
        "total_tokens": total_tokens,
        "cost": compute_cost(total_input, analysis_output_tokens, pricing),
    }
