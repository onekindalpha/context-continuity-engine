"""3-way benchmark용 context 3종을 실제로 생성한다.

Session A (full_history): 관련 문서/코드/테스트 전문을 그대로 이어붙인 것 - 아무 판단 없이 전부.
Session B (generic_summary): 각 파일을 앞부분 N자로만 균일하게 자른 것 - baseline.generic_summary와 같은 사상.
Session C (cce_working_context): 이 대화에서 실제로 오간 token-efficiency 논의를 turn 단위로 옮겨 적은 뒤,
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
    "docs/results.md",
    "docs/decisions/0009-baseline-design.md",
    "docs/decisions/0010-reconstruction-test-method.md",
    "src/working_context.py",
    "src/baseline.py",
]
# src/context_analysis.py, tests/*.py는 여기 안 넣는다. 셋 다 read_file tool로 언제든
# 읽을 수 있고, Groq 계정 TPM(tokens per minute) 한도(무료 tier 기준 8000)를 넘기면
# 요청 자체가 413/rate_limit_exceeded로 거부되기 때문이다 - 실제로 겪은 문제(2회차 실행에서
# "Requested 9545, Limit 8000" 오류). 이 project의 실제 수정 지점도 working_context.py의
# KEEP 처리 로직이라(이 대화에서 실제로 그렇게 결론 냈다), context_analysis.py 전문을
# 안 줘도 task 수행에 필요한 정보는 남아있다.

GENERIC_SUMMARY_MAX_CHARS_PER_FILE = 200

TASK_INSTRUCTION = (Path(__file__).resolve().parent / "task.md").read_text(encoding="utf-8")

# 이 대화에서 실제로 오간, token-efficiency 관련 논의를 turn 단위로 옮겨 적은 것.
# 요약/각색이 아니라 실제 conversation 내용을 그대로 옮긴 것 - CCE가 raw 입력으로 받는
# "채팅 화면을 그대로 복사한 텍스트"에 해당한다.
REAL_DEV_LOG_RAW = """\
user: 결과보고서에 토큰 효율성이 한계라고 했나? 고칠 방법은 없는거야?
assistant: SUMMARY_MAX_CHARS를 120에서 40으로 줄이는 개선을 이미 시도했습니다. 결과: 제안 방식 token이 581에서 462로 줄었고, baseline_recency_truncation과의 격차가 47%에서 17%로 좁혀졌습니다. 하지만 baseline_generic_summary(326 token)보다는 여전히 많이 씁니다.
assistant: 원인을 코드로 추적했습니다. src/working_context.py에서 KEEP action은 원본 turn 전문을 그대로 넣습니다(자르지 않음). 반면 baseline_generic_summary는 모든 turn을 예외 없이 40자로 자릅니다. KEEP 항목이 길면 거기서 baseline보다 token을 더 쓰게 됩니다.
user: 그럼 KEEP도 자르면 되는거 아니야?
assistant: 가능하지만 위험이 있습니다. 지금 reconstruction test가 7/7 PASS인 이유 중 하나가 "KEEP 항목은 원문 그대로 유지한다"는 규칙 덕분일 수 있습니다. KEEP 텍스트를 무작정 자르면 정답이 되는 문장이 잘려나가서 다시 FAIL이 늘어날 위험이 있습니다.
assistant: 이전에 SUMMARY_MAX_CHARS만 조정했을 때는 reconstruction PASS 수가 그대로였습니다(COMPRESS 대상 항목이 정답 turn과 안 겹쳤기 때문). 이번엔 다릅니다 - KEEP 항목 중에 실제로 정답 turn과 겹치는 게 있어서, 자르는 방식에 따라 PASS/FAIL이 바뀔 수 있습니다.
assistant: 시도한다면: KEEP 항목에도 길이 상한을 두되(COMPRESS의 40자보다는 넉넉하게, 예: 150~200자), 자른 뒤에 reconstruction test를 반드시 재실행해서 7/7이 유지되는지 확인해야 합니다. 확인 안 하고 token만 줄이면 안 됩니다.
user: SUMMARY_MAX_CHARS를 또 만지는 것 말고, KEEP 텍스트 자체에 별도 길이 상한을 추가하는 방향으로 해줘. 그리고 반드시 테스트랑 reconstruction 둘 다 통과하는지 확인하고.
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
