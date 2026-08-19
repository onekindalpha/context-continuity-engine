"""핵심 실험: 동일한 token budget에서 task-aware structured context가
generic summary보다 reconstruction quality를 높이는가?

기존 `scripts/run_comparison.py`는 각 방식이 **자기 마음대로 정한 크기**의 context를
만들고 그걸 비교했다(generic 326 / CCE 486). 크기가 다르면 "구조가 좋아서 이긴 건지
token을 더 써서 이긴 건지" 구분할 수 없다.

이 실험은 **budget을 고정**하고 두 방식을 같은 예산 안에서 겨루게 한다. budget을
여러 단계로 낮춰 가며 측정해서, 예산이 줄어들 때 어느 방식이 먼저 무너지는지 본다.

평가는 `content_recall.py`(내용어 보존율) - 기존 turn_id 포함 여부 지표로는
generic summary가 어떤 budget에서도 항상 만점이라 비교가 불가능하기 때문이다.
그 이유는 `content_recall.py` docstring에 적어뒀다.

실행: python3 experiments/budget_reconstruction/run_budget_experiment.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))

from src.ingest import ingest_file  # noqa: E402
from src.context_analysis import build_analysis  # noqa: E402
from src.reconstruction_test import build_ground_truth  # noqa: E402
from src.tokens import count_tokens  # noqa: E402

from content_recall import evaluate  # noqa: E402
from budget_compress import (  # noqa: E402
    generic_summary_under_budget,
    structured_summary_under_budget,
)

FIXTURE = REPO_ROOT / "examples/groq_model_migration_session/session.txt"
EXAMPLE = REPO_ROOT / "examples/groq_model_migration_session/task_context_analysis.example.json"
OUT_DIR = HERE / "results"

# generic summary의 현재 크기(326)를 기준점으로 두고 아래위로 훑는다.
BUDGETS = [500, 400, 326, 260, 200, 150, 100]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ingested = ingest_file(FIXTURE)
    if not ingested["ok"]:
        raise SystemExit(f"ingest 실패: {ingested['error']}")
    session = ingested["session"]
    analysis = build_analysis(session)

    example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    truth_turn_ids = build_ground_truth(example)
    turns_by_id = {t["turn_id"]: t for t in session["turns"]}
    ground_truth_texts = {
        q: " ".join(turns_by_id[t]["text"] for t in sorted(ids) if t in turns_by_id)
        for q, ids in truth_turn_ids.items()
    }

    rows = []
    for budget in BUDGETS:
        generic = generic_summary_under_budget(session, budget)
        structured = structured_summary_under_budget(analysis, session, budget)

        g_eval = evaluate(generic["text"], ground_truth_texts)
        s_eval = evaluate(structured["text"], ground_truth_texts)

        rows.append(
            {
                "budget_tokens": budget,
                "generic_summary": {
                    "actual_tokens": count_tokens(generic["text"]),
                    **g_eval,
                },
                "cce_structured": {
                    "actual_tokens": count_tokens(structured["text"]),
                    "included_categories": structured["included_categories"],
                    **s_eval,
                },
            }
        )

    payload = {
        "fixture": FIXTURE.parent.name,
        "turn_count": len(session["turns"]),
        "metric": "content_recall (내용어 보존율) - experiments/budget_reconstruction/content_recall.py",
        "questions": list(ground_truth_texts.keys()),
        "budgets": BUDGETS,
        "rows": rows,
    }
    (OUT_DIR / "budget_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = render_markdown(payload)
    (OUT_DIR / "budget_results.md").write_text(md, encoding="utf-8")
    print(md)


def render_markdown(payload: dict) -> str:
    lines = [
        "# 동일 token budget에서의 reconstruction 비교",
        "",
        f"fixture: `{payload['fixture']}`, turn 수: {payload['turn_count']}",
        "",
        "코드 실행 결과다. 실행: `python3 experiments/budget_reconstruction/run_budget_experiment.py`",
        "",
        "지표: **content recall**(정답 turn의 내용어가 context 텍스트에 실제로 남아있는 비율). "
        "기존 `src/reconstruction_test.py`의 turn_id 포함 여부 지표는 generic summary가 "
        "turn을 절대 버리지 않기 때문에 어떤 budget에서도 항상 7/7이 나와 비교에 쓸 수 없다 "
        "— 그 이유는 `content_recall.py`에 기록했다.",
        "",
        "| budget(token) | generic 실제 token | generic mean recall | generic PASS | CCE 실제 token | CCE mean recall | CCE PASS |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in payload["rows"]:
        g, s = r["generic_summary"], r["cce_structured"]
        lines.append(
            f"| {r['budget_tokens']} | {g['actual_tokens']} | {g['mean_recall']} | "
            f"{g['counts']['PASS']}/7 | {s['actual_tokens']} | {s['mean_recall']} | "
            f"{s['counts']['PASS']}/7 |"
        )
    lines.append("")
    lines.append("## 질문별 상세 (budget=326, generic summary의 현재 크기 기준)")
    lines.append("")
    target = next((r for r in payload["rows"] if r["budget_tokens"] == 326), None)
    if target:
        lines.append("| 질문 | generic recall | generic 판정 | CCE recall | CCE 판정 |")
        lines.append("|---|---|---|---|---|")
        for q in payload["questions"]:
            g = target["generic_summary"]["per_question"][q]
            s = target["cce_structured"]["per_question"][q]
            lines.append(
                f"| {q} | {g['recall']} | {g['verdict']} | {s['recall']} | {s['verdict']} |"
            )
    lines.append("")
    lines.append("## 한계 (정직하게)")
    lines.append("")
    lines.append(
        "- content recall은 내용어가 **남아있는지**를 보는 것이지 의미를 이해했는지가 아니다. "
        "여전히 근사 지표다.\n"
        "- 불용어 목록과 PASS 임계값(0.5)은 사람이 정한 값이다. 값이 바뀌면 절대 점수는 바뀐다 — "
        "그래서 이 실험은 같은 지표로 두 방식을 비교하는 용도로만 읽어야 한다.\n"
        "- fixture 1개 기준이다. `docs/results.md`의 일반화 한계가 그대로 적용된다.\n"
        "- 결과가 CCE에 불리하게 나오면 그대로 기록한다(AGENTS.md 규칙 7)."
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
