"""내용 수준(content-level) reconstruction 지표.

## 왜 새 지표가 필요한가

기존 `src/reconstruction_test.py`는 "정답 turn이 context에 들어있는가"를 **turn_id
포함 여부**로 판정한다. 그런데 `src/baseline.py`의 `generic_summary`는 모든 turn을
길이만 자를 뿐 **버리지 않으므로**, `in_context_turn_ids`가 항상 전체 turn 집합이다.
즉 turn당 5자로 자르든 200자로 자르든 기존 지표에서는 언제나 7/7 PASS가 나온다.

이건 지표의 구조적 한계다(`docs/decisions/0010`에 "내용이 있는지만 확인한다"고
기록돼 있던 그 한계의 구체적 귀결이다). 이 지표로는 "같은 token budget에서 어느
방식이 정보를 더 잘 보존하는가"라는 질문에 **원리적으로 답할 수 없다.**

## 이 모듈의 방법

turn_id가 아니라 **실제 텍스트에 정보가 남아있는지**를 본다.

1. 질문마다 정답 turn들의 원문에서 내용어(content word)를 뽑는다.
   - 2자 이상 토큰, 불용어 제외, 식별자(`_make_summary` 등)와 숫자 포함.
2. 후보 context **텍스트**에 그 내용어가 몇 개나 실제로 남아있는지 센다.
3. recall = 남아있는 내용어 수 / 정답 내용어 수.
4. recall이 임계값 이상이면 PASS, 그 아래 부분 보존이면 PARTIAL, 거의 없으면 FAIL.

turn을 "포함했다"고 주장해도 텍스트가 잘려서 내용어가 사라졌으면 점수를 못 받는다.
generic summary가 40자로 자르면 그 turn의 뒷부분 내용어는 실제로 사라지므로 이제
불이익을 받는다 - 이게 원래 재려던 것이다.

## 한계 (정직하게)

- 내용어 겹침은 "의미를 이해했는가"가 아니라 "단어가 남아있는가"다. 여전히 근사치다.
  다만 turn_id 포함 여부보다는 실제 정보 보존에 훨씬 가깝다.
- 불용어 목록과 임계값은 사람이 정한 값이다. 값이 바뀌면 절대 점수는 바뀐다.
  그래서 이 실험은 **같은 지표로 두 방식을 비교**하는 용도로만 쓴다.
- 어미/조사 변형을 정규화하지 않는다(형태소 분석기를 쓰지 않음 - 표준 라이브러리
  원칙 유지). 그래서 한국어 어절은 실제보다 낮게 매칭될 수 있는데, 이 불리함은
  두 방식에 동일하게 적용된다.
"""

from __future__ import annotations

import re
from typing import Any

PASS_THRESHOLD = 0.50
PARTIAL_THRESHOLD = 0.20

# 조사/어미/기능어 위주. 내용 판별에 기여하지 않는 토큰을 뺀다.
STOPWORDS = {
    "그리고", "그런데", "그래서", "하지만", "그러면", "그럼", "이건", "이거", "저건",
    "있습니다", "없습니다", "합니다", "입니다", "됩니다", "습니다", "해서", "하는",
    "하고", "해야", "이런", "저런", "그런", "여기", "거기", "지금", "다시", "그냥",
    "네요", "때문", "경우", "정도", "생각", "확인", "가능", "부분", "내용", "사용",
    "the", "and", "for", "that", "this", "with", "you", "are", "was", "not", "but",
}

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+|[0-9]+|[가-힣]{2,}")


def content_words(text: str) -> set[str]:
    """텍스트에서 내용어 집합을 뽑는다."""
    out = set()
    for tok in TOKEN_RE.findall(text):
        low = tok.lower()
        if low in STOPWORDS:
            continue
        if len(tok) < 2:
            continue
        out.add(low)
    return out


def _present(word: str, haystack: str) -> bool:
    """haystack(소문자화된 context 텍스트)에 word가 실제로 남아있는가.

    한국어 어절은 조사가 붙어 형태가 달라지므로, 3자 이상 한글 토큰은
    앞 2자를 어간 근사로 보고 부분 일치도 허용한다. 이 완화는 두 방식에
    동일하게 적용되므로 비교의 공정성은 유지된다.
    """
    if word in haystack:
        return True
    if len(word) >= 3 and re.fullmatch(r"[가-힣]+", word):
        return word[:-1] in haystack
    return False


def recall_for_question(truth_text: str, context_text: str) -> dict[str, Any]:
    truth = content_words(truth_text)
    if not truth:
        return {"verdict": "NO_GROUND_TRUTH", "recall": None, "matched": 0, "total": 0}
    hay = context_text.lower()
    matched = {w for w in truth if _present(w, hay)}
    recall = len(matched) / len(truth)
    if recall >= PASS_THRESHOLD:
        verdict = "PASS"
    elif recall >= PARTIAL_THRESHOLD:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    return {
        "verdict": verdict,
        "recall": round(recall, 3),
        "matched": len(matched),
        "total": len(truth),
    }


def evaluate(
    context_text: str, ground_truth_texts: dict[str, str]
) -> dict[str, Any]:
    """질문별 content recall을 매기고 요약을 만든다."""
    per_question = {
        q: recall_for_question(truth, context_text)
        for q, truth in ground_truth_texts.items()
    }
    counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "NO_GROUND_TRUTH": 0}
    recalls = []
    for r in per_question.values():
        counts[r["verdict"]] += 1
        if r["recall"] is not None:
            recalls.append(r["recall"])
    mean_recall = round(sum(recalls) / len(recalls), 3) if recalls else None
    return {
        "per_question": per_question,
        "counts": counts,
        "mean_recall": mean_recall,
    }
