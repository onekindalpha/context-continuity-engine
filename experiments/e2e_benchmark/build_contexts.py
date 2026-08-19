"""3-way benchmark용 context 3종을 실제로 생성한다.

Session A (full_history): 관련 문서/코드/테스트 전문을 그대로 이어붙인 것 - 아무 판단 없이 전부.
Session B (generic_summary): 각 파일을 앞부분 N자로만 균일하게 자른 것 - baseline.generic_summary와 같은 사상.
Session C (cce_working_context): 아래 REAL_DEV_LOG_RAW(이 task를 다루는 가상의 이전 세션 대화 -
    실제로 이 벤치마크를 위해 구성했다. 이 대화 자체의 축어적 기록이 아니다 - 정직하게 밝혀둔다)를
    이 프로젝트 자신의 --raw 파이프라인에 그대로 통과시켜 만든 실제 Working Context 출력.

세 조건 모두 마지막에 동일한 task 지시문(task.md)을 이어붙인다 - context만 다르고 task는 같아야
비교가 성립한다.

실행: python3 experiments/e2e_benchmark/build_contexts.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.ingest import ingest_json  # noqa: E402
from src.context_analysis import build_analysis  # noqa: E402
from src.working_context import build_working_context  # noqa: E402
from src.raw_text_convert import convert as convert_raw_text  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "contexts"

FULL_HISTORY_FILES = [
    "src/context_analysis.py",
    "tests/test_context_analysis.py",
    "docs/decisions/0006-rule-based-extractor-baseline.md",
]
# task가 "_make_summary의 단어 경계 절삭 버그를 고쳐라"로 바뀌면서(task.md 참조), 이 task와
# 직접 관련된 파일로 교체했다: 고칠 파일 자체, 기존 테스트 패턴(비슷한 테스트를 어떻게
# 써왔는지), 그리고 "summary는 원문 앞부분을 잘라낸 값"이라는 기존 한계를 명시한 결정 문서.
# Gemini(LLM_PROVIDER=gemini) 무료 tier가 분당 250,000 token으로 Groq보다 여유로워
# 이전처럼 파일 수를 극단적으로 줄일 필요는 없지만, 그래도 task와 무관한 파일은 넣지 않는다.

GENERIC_SUMMARY_MAX_CHARS_PER_FILE = 200

TASK_INSTRUCTION = (Path(__file__).resolve().parent / "task.md").read_text(encoding="utf-8")

# 이 benchmark를 위해 구성한 예시 대화다 - task.md의 실제 버그(_make_summary의 단어 경계
# 절삭)를 발견하고 고치기로 결정하는 과정을 담았다. 실제 개발 논의를 반영해서 만들었지만,
# "이 대화"(session 전체) 자체의 축어적 transcript는 아니다 - 정직하게 밝혀둔다. CCE가
# raw 입력으로 받는 "채팅 화면을 그대로 복사한 텍스트" 형식과 동일한 형태로 작성했다.
REAL_DEV_LOG_RAW = """\
user: COMPRESS 요약이 이상하게 나와. "longish"라는 단어가 요약에서 "long"으로 잘려서 나왔어 - 원문에 없던 다른 단어처럼 보여.
assistant: 확인했습니다. src/context_analysis.py의 _make_summary가 SUMMARY_MAX_CHARS(40자) 위치에서 그냥 글자 수로 자르고 있습니다. 예: "uses a longish word"를 40자에서 자르면 "uses a long"이 됩니다 - "longish"가 "long"이라는 다른 단어처럼 보이는 원인입니다.
user: 그럼 단어 경계에서 자르게 고쳐줘. 근데 기존 테스트는 절대 깨면 안돼.
assistant: 방법은 40자 이내에서 마지막 공백을 찾아 그 위치에서 자르는 것입니다. 표준 라이브러리만 쓰는 이 프로젝트 원칙상 정규식이나 str.rfind(' ', 0, 40)이면 충분합니다.
assistant: 주의할 점이 하나 있습니다: 원문에 공백이 아예 없으면(예: 40자 넘는 URL이나 긴 토큰 하나) 공백을 못 찾아서 빈 문자열이 될 수 있습니다 - 그 경우엔 기존 방식(그냥 40자에서 자르기)으로 반드시 fallback해야 합니다. 이 fallback을 빠뜨리면 그 경우에 요약이 아예 빈 문자열이 되는 새 버그가 생깁니다.
user: 그 fallback까지 반영해서 고쳐줘. 그리고 새로 테스트 하나 추가해서 이 동작(단어 경계 절삭 + 공백 없을 때 fallback)을 둘 다 검증해. 기존 테스트 전부 통과하는지도 꼭 확인하고.
"""


def build_full_history_context() -> str:
    parts = []
    for rel in FULL_HISTORY_FILES:
        p = REPO_ROOT / rel
        parts.append(f"=== {rel} (전문) ===\n{p.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)


def build_generic_summary_context() -> str:
    parts = []
    for rel in FULL_HISTORY_FILES:
        p = REPO_ROOT / rel
        text = p.read_text(encoding="utf-8")
        collapsed = " ".join(text.split())
        truncated = collapsed[:GENERIC_SUMMARY_MAX_CHARS_PER_FILE]
        if len(collapsed) > GENERIC_SUMMARY_MAX_CHARS_PER_FILE:
            truncated += "..."
        parts.append(f"=== {rel} (앞부분 {GENERIC_SUMMARY_MAX_CHARS_PER_FILE}자만) ===\n{truncated}")
    return "\n\n".join(parts)


def build_cce_context() -> dict:
    converted = convert_raw_text(REAL_DEV_LOG_RAW)
    ingest_result = ingest_json(json.dumps(converted, ensure_ascii=False))
    if not ingest_result["ok"]:
        raise RuntimeError(f"ingest 실패: {ingest_result['error']}")
    session = ingest_result["session"]
    analysis = build_analysis(session)
    wc = build_working_context(analysis, session)
    return {"text": wc["text"], "action_counts": wc["action_counts"], "warnings": converted["warnings"]}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    full_history = build_full_history_context()
    generic_summary = build_generic_summary_context()
    cce = build_cce_context()

    (OUT_DIR / "session_a_full_history.txt").write_text(
        full_history + "\n\n=== TASK ===\n" + TASK_INSTRUCTION, encoding="utf-8"
    )
    (OUT_DIR / "session_b_generic_summary.txt").write_text(
        generic_summary + "\n\n=== TASK ===\n" + TASK_INSTRUCTION, encoding="utf-8"
    )
    (OUT_DIR / "session_c_cce_working_context.txt").write_text(
        cce["text"] + "\n\n=== TASK ===\n" + TASK_INSTRUCTION, encoding="utf-8"
    )
    (OUT_DIR / "session_c_meta.json").write_text(
        json.dumps({"action_counts": cce["action_counts"], "warnings": cce["warnings"]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    def tok(path: Path) -> int:
        from src.tokens import count_tokens

        return count_tokens(path.read_text(encoding="utf-8"))

    print("생성 완료. 대략적인 context 크기(근사 token, 근거: docs/decisions/0007):")
    print(f"  session_a_full_history:        {tok(OUT_DIR / 'session_a_full_history.txt')}")
    print(f"  session_b_generic_summary:     {tok(OUT_DIR / 'session_b_generic_summary.txt')}")
    print(f"  session_c_cce_working_context: {tok(OUT_DIR / 'session_c_cce_working_context.txt')}")


if __name__ == "__main__":
    main()
