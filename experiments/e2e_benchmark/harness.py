"""3-way end-to-end task-completion benchmark harness.

이 스크립트는 네트워크(Groq API)가 필요하므로 sandbox가 아니라 실제 네트워크가
되는 환경(사용자 로컬 머신)에서 실행해야 한다.

각 condition(a/b/c)마다:
  1. 현재 커밋에서 독립된 git worktree를 만든다(서로 영향 없음).
  2. contexts/session_*.txt를 "이전 세션에서 이어받은 메모리"로 LLM에게 준다.
  3. LLM이 read_file/write_file/run_tests/run_comparison tool을 실제로 호출하며
     작업한다(최대 MAX_TOOL_ROUNDS회).
  4. 종료 후 harness가 직접 worktree에서 테스트/비교 스크립트를 실행해서
     task_success를 판정한다 - LLM의 자기 보고를 믿지 않는다.
  5. 결과를 results/<condition>.json 에 기록한다.

사용법:
  export GROQ_API_KEY=...
  python3 experiments/e2e_benchmark/harness.py --condition a
  python3 experiments/e2e_benchmark/harness.py --condition all

의존성: 표준 라이브러리만 사용한다(urllib). pip install 불필요.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.tokens import count_tokens  # noqa: E402
EXP_DIR = Path(__file__).resolve().parent
CONTEXTS_DIR = EXP_DIR / "contexts"
WORKTREES_DIR = EXP_DIR / "worktrees"
RESULTS_DIR = EXP_DIR / "results"

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_TOOL_ROUNDS = 25

# 대략적인 Groq 가격(USD/1M token) - 실제 청구 금액이 아니라 근사 추정치다.
# 모델/시점에 따라 실제 가격은 다를 수 있다. 정확한 수치는 https://groq.com/pricing 확인.
APPROX_PRICE_PER_1M_INPUT = float(os.environ.get("GROQ_PRICE_INPUT_PER_1M", "0.10"))
APPROX_PRICE_PER_1M_OUTPUT = float(os.environ.get("GROQ_PRICE_OUTPUT_PER_1M", "0.50"))

CONDITIONS = {
    "a": ("session_a_full_history.txt", "full_history"),
    "b": ("session_b_generic_summary.txt", "generic_summary"),
    "c": ("session_c_cce_working_context.txt", "cce_working_context"),
}

SYSTEM_PROMPT = """당신은 context-continuity-engine 저장소를 고치는 코딩 에이전트입니다.
사용자 메시지에 이전 세션에서 이어받은 메모리(memory)와 지금 해야 할 task가 함께 들어있습니다.
반드시 read_file로 실제 코드를 먼저 확인한 뒤에 write_file로 수정하세요. 짐작으로 고치지 마세요.
수정 후에는 run_tests와 run_comparison을 반드시 호출해서 결과를 직접 확인하세요.
조건을 만족했다고 판단되면 tool 호출 없이 최종 메시지로 결과를 요약하고 끝내세요."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "저장소 안의 파일 하나를 읽는다. path는 저장소 루트 기준 상대 경로.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "저장소 안의 파일 하나를 전체 내용으로 덮어쓴다. path는 저장소 루트 기준 상대 경로.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "디렉토리 안의 파일 목록을 본다. path 생략 시 저장소 루트.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "python3 -m unittest discover -s tests 를 실제로 실행하고 결과를 반환한다.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_comparison",
            "description": "python3 scripts/run_comparison.py 를 실제로 실행하고 comparison_result.json 요약을 반환한다.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _safe_path(worktree: Path, rel_path: str) -> Path:
    target = (worktree / rel_path).resolve()
    if not str(target).startswith(str(worktree.resolve())):
        raise ValueError(f"허용되지 않은 경로: {rel_path}")
    return target


def make_worktree(condition_name: str) -> Path:
    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
    path = WORKTREES_DIR / condition_name
    if path.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(path)], cwd=REPO_ROOT, check=False)
        shutil.rmtree(path, ignore_errors=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(path), head], cwd=REPO_ROOT, check=True
    )
    return path


def remove_worktree(path: Path) -> None:
    subprocess.run(["git", "worktree", "remove", "--force", str(path)], cwd=REPO_ROOT, check=False)


def _call_groq_via_curl(body: bytes, api_key: str) -> dict:
    """curl로 호출한다. Cloudflare가 urllib의 TLS/UA 지문을 봇으로 오판해 1010으로
    막는 경우가 있는데, curl은 실제 브라우저와 지문이 비슷해 이 문제를 우회할 수 있다."""
    proc = subprocess.run(
        [
            "curl", "-sS", "--fail-with-body", "-X", "POST", GROQ_API_URL,
            "-H", f"Authorization: Bearer {api_key}",
            "-H", "Content-Type: application/json",
            "--data-binary", "@-",
        ],
        input=body,
        capture_output=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Groq API 호출 실패(curl exit {proc.returncode}): {proc.stdout.decode('utf-8', errors='replace')} "
            f"{proc.stderr.decode('utf-8', errors='replace')}"
        )
    return json.loads(proc.stdout.decode("utf-8"))


def _call_groq_via_urllib(body: bytes, api_key: str) -> dict:
    req = urllib.request.Request(
        GROQ_API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "curl/8.5.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Groq API 오류 {e.code}: {detail}") from e


def call_groq(messages: list[dict], api_key: str) -> dict:
    body = json.dumps(
        {"model": GROQ_MODEL, "messages": messages, "tools": TOOLS, "tool_choice": "auto", "temperature": 0.2}
    ).encode("utf-8")
    if shutil.which("curl"):
        return _call_groq_via_curl(body, api_key)
    return _call_groq_via_urllib(body, api_key)


MAX_READ_FILE_CHARS = 6000  # Groq 계정 TPM(무료 tier 8000) 초과를 막기 위한 상한
SAFE_REQUEST_TOKEN_BUDGET = 6500  # 매 요청마다 이 아래로 유지 - 초기 context가 작아도
# tool 호출이 쌓이면서 대화가 커지면 나중 round에서 똑같이 413이 날 수 있어서 매 round마다 확인한다.


def _estimate_messages_tokens(messages: list[dict]) -> int:
    total = 0
    for m in messages:
        content = m.get("content") or ""
        if isinstance(content, str):
            total += count_tokens(content)
        for tc in m.get("tool_calls") or []:
            total += count_tokens(json.dumps(tc))
    return total


def _trim_messages_to_budget(messages: list[dict], budget: int = SAFE_REQUEST_TOKEN_BUDGET) -> list[dict]:
    """system(index 0)과 최초 context(index 1)는 실험 조건 자체라 항상 유지한다.
    예산을 넘으면 가장 오래된 (assistant + 그 뒤에 딸린 tool 결과들) 묶음 단위로 통째로 지운다.
    tool_call_id는 반드시 자신을 만든 assistant 메시지와 함께 있어야 하므로 절대 개별 메시지
    단위로 지우면 안 된다(그러면 API가 잘못된 message sequence로 거부한다)."""
    while _estimate_messages_tokens(messages) > budget and len(messages) > 3:
        # index 2가 항상 그룹의 시작(assistant)이어야 정상 시퀀스다.
        group_end = 3
        while group_end < len(messages) and messages[group_end].get("role") == "tool":
            group_end += 1
        del messages[2:group_end]
    return messages


def execute_tool(worktree: Path, name: str, args: dict) -> str:
    if name == "read_file":
        p = _safe_path(worktree, args["path"])
        if not p.exists():
            return f"파일 없음: {args['path']}"
        content = p.read_text(encoding="utf-8")
        if len(content) > MAX_READ_FILE_CHARS:
            return (
                content[:MAX_READ_FILE_CHARS]
                + f"\n\n...[중략: 전체 {len(content)}자 중 앞 {MAX_READ_FILE_CHARS}자만 표시됨 - "
                "TPM 한도 보호. 특정 부분이 더 필요하면 list_files로 구조를 먼저 보고 판단할 것]"
            )
        return content
    if name == "write_file":
        p = _safe_path(worktree, args["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args["content"], encoding="utf-8")
        return f"저장됨: {args['path']} ({len(args['content'])}자)"
    if name == "list_files":
        rel = args.get("path", ".")
        p = _safe_path(worktree, rel)
        if not p.is_dir():
            return f"디렉토리 아님: {rel}"
        return "\n".join(sorted(x.name for x in p.iterdir()))
    if name == "run_tests":
        proc = subprocess.run(
            ["python3", "-m", "unittest", "discover", "-s", "tests"],
            cwd=worktree, capture_output=True, text=True, timeout=120,
        )
        return f"returncode={proc.returncode}\n{proc.stdout[-1200:]}\n{proc.stderr[-500:]}"
    if name == "run_comparison":
        proc = subprocess.run(
            ["python3", "scripts/run_comparison.py"],
            cwd=worktree, capture_output=True, text=True, timeout=120,
        )
        result_path = worktree / "examples/groq_model_migration_session/comparison_result.json"
        summary = result_path.read_text(encoding="utf-8") if result_path.exists() else "결과 파일 없음"
        return f"returncode={proc.returncode}\n{proc.stdout[-300:]}\n{proc.stderr[-500:]}\n\n결과 JSON:\n{summary[:1800]}"
    return f"알 수 없는 tool: {name}"


def run_condition(cond_key: str, api_key: str) -> dict[str, Any]:
    context_file, cond_name = CONDITIONS[cond_key]
    context_text = (CONTEXTS_DIR / context_file).read_text(encoding="utf-8")

    worktree = make_worktree(cond_name)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context_text},
    ]

    tool_call_counts: dict[str, int] = {}
    prompt_tokens_total = 0
    completion_tokens_total = 0
    invalid_tool_calls = 0  # re-explanation turn 근사 지표
    started = time.time()
    rounds_used = 0

    for round_i in range(MAX_TOOL_ROUNDS):
        rounds_used = round_i + 1
        messages = _trim_messages_to_budget(messages)
        resp = call_groq(messages, api_key)
        usage = resp.get("usage", {})
        prompt_tokens_total += usage.get("prompt_tokens", 0)
        completion_tokens_total += usage.get("completion_tokens", 0)

        choice = resp["choices"][0]
        msg = choice["message"]
        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            break

        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            tool_call_counts[fn_name] = tool_call_counts.get(fn_name, 0) + 1
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
                result = execute_tool(worktree, fn_name, args)
            except Exception as exc:  # noqa: BLE001
                invalid_tool_calls += 1
                result = f"에러: {exc}"
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

    elapsed = time.time() - started

    # harness가 직접 최종 판정 (LLM 자기 보고 신뢰 안 함)
    tests_proc = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "tests"],
        cwd=worktree, capture_output=True, text=True, timeout=120,
    )
    tests_pass = tests_proc.returncode == 0

    comparison_proc = subprocess.run(
        ["python3", "scripts/run_comparison.py"],
        cwd=worktree, capture_output=True, text=True, timeout=120,
    )
    result_path = worktree / "examples/groq_model_migration_session/comparison_result.json"
    proposed_tokens = None
    reconstruction_pass = None
    if result_path.exists():
        data = json.loads(result_path.read_text(encoding="utf-8"))
        proposed_tokens = data["token_usage"]["proposed_working_context"]["context_tokens"]
        per_question = data["reconstruction_test"]["results"]["proposed_working_context"]
        reconstruction_pass = sum(1 for v in per_question.values() if v["verdict"] == "PASS")

    task_success = bool(
        tests_pass and proposed_tokens is not None and proposed_tokens < 326 and reconstruction_pass == 7
    )

    diff_proc = subprocess.run(
        ["git", "diff", "--stat"], cwd=worktree, capture_output=True, text=True
    )

    estimated_cost_usd = (
        prompt_tokens_total / 1_000_000 * APPROX_PRICE_PER_1M_INPUT
        + completion_tokens_total / 1_000_000 * APPROX_PRICE_PER_1M_OUTPUT
    )

    result = {
        "condition": cond_name,
        "model": GROQ_MODEL,
        "task_success": task_success,
        "tests_pass": tests_pass,
        "proposed_working_context_tokens": proposed_tokens,
        "reconstruction_pass_count": reconstruction_pass,
        "rounds_used": rounds_used,
        "max_rounds": MAX_TOOL_ROUNDS,
        "tool_call_counts": tool_call_counts,
        "approx_re_explanation_turns": invalid_tool_calls,
        "input_tokens": prompt_tokens_total,
        "output_tokens": completion_tokens_total,
        "total_tokens": prompt_tokens_total + completion_tokens_total,
        "estimated_cost_usd_approx": round(estimated_cost_usd, 6),
        "wall_clock_seconds": round(elapsed, 1),
        "diff_stat": diff_proc.stdout,
        "final_message": messages[-1].get("content") if messages[-1].get("role") == "assistant" else None,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / f"{cond_name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", choices=["a", "b", "c", "all"], default="all")
    parser.add_argument("--keep-worktrees", action="store_true", help="종료 후 worktree를 지우지 않는다(diff 직접 확인용)")
    args = parser.parse_args()

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY 환경변수가 없습니다. export GROQ_API_KEY=... 로 설정하세요.")
        return 1

    keys = ["a", "b", "c"] if args.condition == "all" else [args.condition]
    for k in keys:
        print(f"=== condition {k} ({CONDITIONS[k][1]}) 실행 ===")
        result = run_condition(k, api_key)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not args.keep_worktrees:
            remove_worktree(WORKTREES_DIR / CONDITIONS[k][1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
