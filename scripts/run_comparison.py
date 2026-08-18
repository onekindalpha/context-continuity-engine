"""baseline 2종과 제안 방식(Working Context)을 실제 fixture로 비교 실행한다.

평가 목적: token 절감과 reconstruction 성공률을 같은 fixture, 같은 질문
기준으로 실제로 측정해야 "context는 남기고 token은 줄인다"는 주장을
검증할 수 있다(docs/problem.md, docs/evaluation.md).

실행: python3 scripts/run_comparison.py
출력: examples/groq_model_migration_session/comparison_result.json, .md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import baseline  # noqa: E402
import reconstruction_test  # noqa: E402
import tokens  # noqa: E402
import working_context  # noqa: E402
from ingest import ingest_file  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "examples" / "groq_model_migration_session"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    ingest_result = ingest_file(FIXTURE_DIR / "session.json")
    if not ingest_result["ok"]:
        raise SystemExit(f"ingest 실패: {ingest_result['error']}")
    session = ingest_result["session"]

    analysis = load_json(FIXTURE_DIR / "context_analysis.json")
    example = load_json(FIXTURE_DIR / "task_context_analysis.example.json")

    # 1. 세 가지 방식으로 context를 만든다.
    proposed_wc = working_context.build_working_context(analysis, session)
    proposed_coverage = working_context.turn_coverage(analysis)
    recency = baseline.recency_truncation(session)
    generic = baseline.generic_summary(session)

    methods_for_test = {
        "baseline_recency_truncation": recency,
        "baseline_generic_summary": generic,
        "proposed_working_context": proposed_coverage,
    }

    # 2. reconstruction test: 7개 질문에 대해 각 방식이 답할 근거를 담고 있는지.
    recon = reconstruction_test.run_reconstruction_test(example, methods_for_test)

    # 3. token 비교: 원본 전체 대비 각 방식의 token 수.
    full_text = "\n".join(f"[{t['speaker']}] {t['text']}" for t in session["turns"])
    usage = {
        "original_full_session": tokens.usage_report("original_full_session", full_text),
        "baseline_recency_truncation": tokens.usage_report(
            "baseline_recency_truncation", recency["text"]
        ),
        "baseline_generic_summary": tokens.usage_report(
            "baseline_generic_summary", generic["text"]
        ),
        "proposed_working_context": tokens.usage_report(
            "proposed_working_context", proposed_wc["text"]
        ),
    }

    result = {
        "fixture": "groq_model_migration_session",
        "turn_count": session["turn_count"],
        "reconstruction_test": recon,
        "token_usage": usage,
        "proposed_action_counts": proposed_wc["action_counts"],
        "baseline_params": {
            "recency_truncation_keep_last_n_turns": baseline.DEFAULT_KEEP_LAST_N_TURNS,
            "generic_summary_max_chars_per_turn": baseline.DEFAULT_MAX_CHARS_PER_TURN,
        },
    }

    out_json = FIXTURE_DIR / "comparison_result.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    out_md = FIXTURE_DIR / "comparison_result.md"
    out_md.write_text(render_markdown(result), encoding="utf-8")

    print(f"작성됨: {out_json}")
    print(f"작성됨: {out_md}")


def render_markdown(result: dict) -> str:
    lines = []
    lines.append("# baseline vs 제안 방식 비교 결과")
    lines.append("")
    lines.append(f"fixture: `{result['fixture']}`, turn 수: {result['turn_count']}")
    lines.append("")
    lines.append("코드 실행 결과다. 사람이 손으로 채운 값이 아니다. 실행: `python3 scripts/run_comparison.py`")
    lines.append("")

    lines.append("## token 사용량")
    lines.append("")
    lines.append("| 방식 | context token | 비고 |")
    lines.append("|---|---|---|")
    for name, u in result["token_usage"].items():
        lines.append(f"| {name} | {u['context_tokens']} | analysis 단계 추가 token 없음(규칙 기반, LLM 미사용) |")
    lines.append("")
    orig = result["token_usage"]["original_full_session"]["context_tokens"]
    lines.append("원본 전체 대비 감소율:")
    lines.append("")
    for name, u in result["token_usage"].items():
        if name == "original_full_session":
            continue
        reduced = u["context_tokens"]
        pct = (1 - reduced / orig) * 100 if orig else 0
        lines.append(f"- {name}: {reduced}/{orig} token ({pct:.1f}% 감소)")
    lines.append("")
    lines.append(
        "token 수는 근사치다(docs/decisions/0007). 절대값이 아니라 방식 간 상대 비교로만 읽는다."
    )
    lines.append("")

    lines.append("## reconstruction test (7개 질문)")
    lines.append("")
    lines.append(
        "PASS: 즉시 답변 가능(원문 또는 요약이 context에 있음) / RETRIEVABLE: 외부 보관분을 조회하면 답변 가능 / "
        "FAIL: 어디에도 없음 / NO_GROUND_TRUTH: 사람이 만든 예시에도 해당 category 항목이 없음"
    )
    lines.append("")
    questions = reconstruction_test.QUESTIONS
    methods = list(result["reconstruction_test"]["results"].keys())
    header = "| 질문 | " + " | ".join(methods) + " |"
    sep = "|---|" + "|".join(["---"] * len(methods)) + "|"
    lines.append(header)
    lines.append(sep)
    for q in questions:
        row = [q]
        for m in methods:
            row.append(result["reconstruction_test"]["results"][m][q]["verdict"])
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("### 방식별 요약")
    lines.append("")
    lines.append("| 방식 | PASS | RETRIEVABLE | FAIL | NO_GROUND_TRUTH |")
    lines.append("|---|---|---|---|---|")
    for m in methods:
        s = result["reconstruction_test"]["summary"][m]
        lines.append(
            f"| {m} | {s['PASS']} | {s['RETRIEVABLE']} | {s['FAIL']} | {s['NO_GROUND_TRUTH']} |"
        )
    lines.append("")

    lines.append("## 제안 방식의 retention_action 분포")
    lines.append("")
    for action, count in result["proposed_action_counts"].items():
        lines.append(f"- {action}: {count}")
    lines.append("")

    lines.append("## 관찰된 한계")
    lines.append("")
    lines.append(
        "- 제안 방식의 category 추출은 규칙 기반이며 정확도가 낮다(0006 문서 기준 turn 단위 일치 7/18). "
        "goal/decision category는 이 fixture에서 자동 추출 결과에 전혀 없다 — 그 category가 필요한 질문은 "
        "ContextItem 자체가 없어 FAIL이 나올 수 있다."
    )
    lines.append(
        "- reconstruction test는 '내용이 context에 있는지'만 확인한다. 그 내용으로 실제 질문에 사람이 "
        "만족스럽게 답할 수 있는지는 확인하지 않는다(0010 문서 참조)."
    )
    lines.append(
        "- baseline_generic_summary는 모든 turn을 자르기만 하고 버리지 않으므로 reconstruction test 상 "
        "FAIL이 거의 나오지 않는다 — 대신 token 절감 효과가 제안 방식보다 작을 수 있다. token 표와 "
        "함께 봐야 한다."
    )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
