"""3-way benchmark용 context 3종을 실제로 생성한다.

**중요한 설계 변경(2차 실행 이후, docs/decisions/0015 참조)**

이전 버전은 Session A/B를 "저장소 파일 원문/절삭"으로, Session C만 "대화 압축본"으로
만들었다. 그러면 세 조건이 서로 다른 종류의 자료(코드 파일 vs 대화)를 받게 되어
"압축 방식의 차이"가 아니라 "자료 종류의 차이"를 비교하게 된다 - 실제로 이 한계는
README와 0015에 명시돼 있었고, 2차 실행에서 Session C만 실패한 원인을 해석할 수 없게
만든 직접적인 이유이기도 하다.

이번 버전은 셋 다 **같은 원본 대화**(`prior_session.txt`)에서 출발한다:

- Session A (full_history):    그 대화 전문을 그대로 (= 아무것도 안 버리는 조건)
- Session B (generic_summary): 같은 대화를 `src/baseline.py`의 generic_summary로 압축
- Session C (cce_working_context): 같은 대화를 CCE 파이프라인으로 압축

이제 세 조건의 차이는 오직 **"같은 대화를 어떻게 압축했는가"** 하나다. 이게 이 프로젝트가
원래 주장하려던 비교와 정확히 일치한다.

세 조건 모두 마지막에 동일한 task 지시문(task.md)을 이어붙인다 - context만 다르고 task는
같아야 비교가 성립한다.

`prior_session.txt`에 대해 정직하게 밝힐 점: 이 대화는 이 벤치마크를 위해 구성한 것이다.
task.md가 다루는 실제 버그(_make_summary의 단어 경계 절삭)를 발견하고 고치기로 결정하는
과정을 담았고, 실제 개발 논의(폐기된 textwrap 접근, 공백 없을 때의 fallback 함정)를
반영했지만, 특정 실제 세션의 축어적 transcript는 아니다.

실행: python3 experiments/e2e_benchmark/build_contexts.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.ingest import ingest_txt  # noqa: E402
from src.context_analysis import build_analysis  # noqa: E402
from src.working_context import build_working_context  # noqa: E402
from src.baseline import generic_summary  # noqa: E402
from src.tokens import count_tokens  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "contexts"

PRIOR_SESSION_RAW = (HERE / "prior_session.txt").read_text(encoding="utf-8")
TASK_INSTRUCTION = (HERE / "task.md").read_text(encoding="utf-8")


def load_session() -> dict:
    """prior_session.txt(TXT 형식 session log)를 SessionLog로 변환한다.

    세 조건이 모두 이 동일한 SessionLog에서 출발한다. TXT 형식을 쓰는 이유는
    timestamp가 있어야 CCE의 task_relevance(시간 간격 기반 episode 추정)가
    실제로 동작하기 때문이다 - timestamp 없는 평문을 넣으면 episode 경계를
    찾지 못해 모든 turn이 KEEP이 되고, 압축이 사실상 일어나지 않는다.
    (이 사실 자체가 실측으로 확인된 CCE의 한계다 - docs/decisions/0017 참조.)
    """
    ingest_result = ingest_txt(PRIOR_SESSION_RAW)
    if not ingest_result["ok"]:
        raise RuntimeError(f"ingest 실패: {ingest_result['error']}")
    session = ingest_result["session"]
    return {"session": session, "warnings": session.get("warnings", [])}


def build_full_history_context(session: dict) -> str:
    """조건 A: 대화 전문을 그대로 (압축 없음)."""
    return "\n".join(f"[{t['speaker']}] {t['text']}" for t in session["turns"])


def build_generic_summary_context(session: dict) -> dict:
    """조건 B: 같은 대화를 baseline generic_summary로 압축."""
    result = generic_summary(session)
    return {"text": result["text"], "method": result["method"]}


def build_cce_context(session: dict) -> dict:
    """조건 C: 같은 대화를 CCE 파이프라인으로 압축."""
    analysis = build_analysis(session)
    wc = build_working_context(analysis, session)
    return {"text": wc["text"], "action_counts": wc["action_counts"]}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    loaded = load_session()
    session = loaded["session"]

    full_history = build_full_history_context(session)
    generic = build_generic_summary_context(session)
    cce = build_cce_context(session)

    (OUT_DIR / "session_a_full_history.txt").write_text(
        full_history + "\n\n=== TASK ===\n" + TASK_INSTRUCTION, encoding="utf-8"
    )
    (OUT_DIR / "session_b_generic_summary.txt").write_text(
        generic["text"] + "\n\n=== TASK ===\n" + TASK_INSTRUCTION, encoding="utf-8"
    )
    (OUT_DIR / "session_c_cce_working_context.txt").write_text(
        cce["text"] + "\n\n=== TASK ===\n" + TASK_INSTRUCTION, encoding="utf-8"
    )
    (OUT_DIR / "session_c_meta.json").write_text(
        json.dumps(
            {
                "turn_count": len(session["turns"]),
                "action_counts": cce["action_counts"],
                "warnings": loaded["warnings"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    def tok(path: Path) -> int:
        return count_tokens(path.read_text(encoding="utf-8"))

    print(f"원본 대화 turn 수: {len(session['turns'])}")
    print("생성 완료. 대략적인 context 크기(근사 token, 근거: docs/decisions/0007):")
    print(f"  session_a_full_history:        {tok(OUT_DIR / 'session_a_full_history.txt')}")
    print(f"  session_b_generic_summary:     {tok(OUT_DIR / 'session_b_generic_summary.txt')}")
    print(f"  session_c_cce_working_context: {tok(OUT_DIR / 'session_c_cce_working_context.txt')}")
    print()
    print("압축만 따로(TASK 지시문 제외) 본 크기:")
    print(f"  A 대화 전문:        {count_tokens(full_history)}")
    print(f"  B generic summary:  {count_tokens(generic['text'])}")
    print(f"  C CCE:              {count_tokens(cce['text'])}")
    print()
    print(f"CCE retention_action 분포: {cce['action_counts']}")


if __name__ == "__main__":
    main()
