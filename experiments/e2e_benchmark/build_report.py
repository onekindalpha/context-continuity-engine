"""results/{full_history,generic_summary,cce_working_context}.json 3개를 모아
하나의 Markdown/JSON 비교 리포트로 만든다.

실행: python3 experiments/e2e_benchmark/build_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
ORDER = ["full_history", "generic_summary", "cce_working_context"]
LABELS = {
    "full_history": "Session A (원본 전체)",
    "generic_summary": "Session B (Generic Summary)",
    "cce_working_context": "Session C (CCE Working Context)",
}


def load_results() -> dict:
    out = {}
    for name in ORDER:
        p = RESULTS_DIR / f"{name}.json"
        if p.exists():
            out[name] = json.loads(p.read_text(encoding="utf-8"))
    return out


def render_markdown(results: dict) -> str:
    lines = ["# End-to-End Task Completion Benchmark 결과", ""]
    lines.append(
        "task: `experiments/e2e_benchmark/task.md` — 실제 미해결 과제(COMPRESS를 baseline_generic_summary보다 "
        "token 효율적으로 만들되 reconstruction 7/7 유지). harness가 LLM 자기 보고가 아니라 실제 테스트/비교 스크립트 "
        "실행으로 직접 판정했다."
    )
    lines.append("")
    lines.append(
        "| 조건 | task_success | tests_pass | 최종 token | reconstruction PASS | tool calls | input tok | output tok | 예상 비용(USD, 근사) | 소요 시간(s) | round 수 |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for name in ORDER:
        r = results.get(name)
        if not r:
            lines.append(f"| {LABELS[name]} | (미실행) | - | - | - | - | - | - | - | - | - |")
            continue
        total_calls = sum(r["tool_call_counts"].values())
        lines.append(
            f"| {LABELS[name]} | {'✅' if r['task_success'] else '❌'} | "
            f"{'OK' if r['tests_pass'] else 'FAIL'} | {r['proposed_working_context_tokens']} | "
            f"{r['reconstruction_pass_count']}/7 | {total_calls} | {r['input_tokens']} | {r['output_tokens']} | "
            f"${r['estimated_cost_usd_approx']} | {r['wall_clock_seconds']} | {r['rounds_used']}/{r['max_rounds']} |"
        )
    lines.append("")
    lines.append("## 한계 (정직하게 기록)")
    lines.append("")
    lines.append(
        "- `estimated_cost_usd_approx`는 harness.py에 하드코딩된 근사 단가 기준이다 - 실제 청구액이 아니다.\n"
        "- `approx_re_explanation_turns`는 tool 호출이 실패한 횟수로 근사한 것이다 - 실제 '재설명 요청'을 직접 측정한 게 아니다(완전 자동 실행이라 실제 사용자가 없다).\n"
        "- fixture 1개, task 1개, 각 조건 1회 실행 기준이다. 모델의 비결정성(temperature=0.2라도 완전히 결정적이지 않음)을 감안하면 여러 번 반복 실행해 분산을 봐야 신뢰도가 올라간다 - 이번엔 1회만 실행했다.\n"
        "- Session A/B는 저장소 파일을 직접 이어붙인 것이고 Session C는 이 문제에 대한 실제 대화를 CCE로 압축한 것이라, "
        "'무엇을 memory로 주는가'의 성격 자체가 다르다(파일 원문 vs 논의 요약). 에이전트가 read_file tool로 실제 코드는 "
        "언제든 다시 읽을 수 있으므로, 이 실험이 실제로 비교하는 것은 '이전 판단/실패 이력이 보존되는가'이지 "
        "'코드 원문 접근 가능 여부'가 아니다."
    )
    return "\n".join(lines)


def main() -> None:
    results = load_results()
    if not results:
        print("results/*.json 이 없습니다. 먼저 harness.py를 실행하세요.")
        return
    (RESULTS_DIR / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    md = render_markdown(results)
    (RESULTS_DIR / "summary.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
