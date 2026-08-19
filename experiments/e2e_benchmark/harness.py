"""3-way end-to-end task-completion benchmark harness.

이 스크립트는 실제 LLM API 네트워크 호출이 필요하므로 sandbox가 아니라 실제
네트워크가 되는 환경(사용자 로컬 머신)에서 실행해야 한다. Groq와 Gemini 둘 다
OpenAI 호환 chat/completions 형식이라 LLM_PROVIDER 환경변수로 고른다.

각 condition(a/b/c)마다:
  1. 현재 커밋에서 독립된 git worktree를 만든다(서로 영향 없음).
  2. contexts/session_*.txt를 "이전 세션에서 이어받은 메모리"로 LLM에게 준다.
  3. LLM이 read_file/write_file/run_tests/run_comparison tool을 실제로 호출하며
     작업한다(최대 MAX_TOOL_ROUNDS회).
  4. 종료 후 harness가 직접 worktree에서 테스트/비교 스크립트를 실행해서
     task_success를 판정한다 - LLM의 자기 보고를 믿지 않는다.
  5. 결과를 results/<condition>.json 에 기록한다.

사용법:
  # Groq (기본값)
  export GROQ_API_KEY=...
  python3 experiments/e2e_benchmark/harness.py --condition all

  # Gemini (Groq 무료 tier TPM이 부족할 때 대안 - 2026-08 기준 무료 tier가 더 넉넉함)
  export LLM_PROVIDER=gemini
  export GEMINI_API_KEY=...
  python3 experiments/e2e_benchmark/harness.py --condition all

의존성: 표준 라이브러리만 사용한다(urllib). pip install 불필요.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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

MAX_TOOL_ROUNDS = 25

# provider 선택: LLM_PROVIDER=groq(기본) 또는 LLM_PROVIDER=gemini.
# 둘 다 OpenAI 호환 chat/completions 형식이라 tool-calling 루프 코드는 공유한다.
# Gemini를 추가한 이유: Groq 무료 tier가 분당 6000~8000 token으로 이 벤치마크 규모에
# 비해 작아 재시도가 오래 걸렸다. Gemini 2.5 Flash-Lite 무료 tier는 분당 250,000 token으로
# 훨씬 여유롭다(2026-08 기준, 웹 검색으로 확인 - 두 값 다 사용 시점에 바뀔 수 있다).
PROVIDER = os.environ.get("LLM_PROVIDER", "groq").lower()

_PROVIDER_DEFAULTS = {
    "groq": {
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "openai/gpt-oss-20b",
        "api_key_env": "GROQ_API_KEY",
        "price_input_per_1m": 0.10,
        "price_output_per_1m": 0.50,
    },
    "gemini": {
        "api_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "model": "gemini-2.5-flash-lite",
        "api_key_env": "GEMINI_API_KEY",
        "price_input_per_1m": 0.10,
        "price_output_per_1m": 0.40,
    },
}
if PROVIDER not in _PROVIDER_DEFAULTS:
    raise SystemExit(f"알 수 없는 LLM_PROVIDER: {PROVIDER} (groq 또는 gemini만 지원)")

_CFG = _PROVIDER_DEFAULTS[PROVIDER]
MODEL = os.environ.get("LLM_MODEL", _CFG["model"])
API_URL = _CFG["api_url"]
API_KEY_ENV = _CFG["api_key_env"]

# 대략적인 가격(USD/1M token) - 실제 청구 금액이 아니라 근사 추정치다.
# 모델/시점에 따라 실제 가격은 다를 수 있다. 정확한 수치는 각 provider의 공식 pricing 페이지 확인.
APPROX_PRICE_PER_1M_INPUT = float(os.environ.get("LLM_PRICE_INPUT_PER_1M", _CFG["price_input_per_1m"]))
APPROX_PRICE_PER_1M_OUTPUT = float(os.environ.get("LLM_PRICE_OUTPUT_PER_1M", _CFG["price_output_per_1m"]))

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
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "지금 이 tool을 호출하는 이유(한 줄, 선택)"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_comparison",
            "description": "python3 scripts/run_comparison.py 를 실제로 실행하고 comparison_result.json 요약을 반환한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "지금 이 tool을 호출하는 이유(한 줄, 선택)"}
                },
            },
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


class LLMRateLimitError(RuntimeError):
    """429 rate limit - 재시도로 해결 가능(TPM/RPM 롤링 윈도우가 지나면 풀림).
    retry_after가 None이면 서버가 정확한 대기 시간을 안 알려준 것 - 이 경우 호출부가
    지수 백오프(exponential backoff)로 대체한다. Groq는 "try again in Ns" 형식으로
    정확한 시간을 주는 걸 실제로 확인했지만, Gemini의 정확한 에러 문구는 아직
    실사용으로 확인하지 못했다 - 확인 안 된 형식을 억지로 파싱하지 않고 None으로 둔다."""

    def __init__(self, message: str, retry_after: float | None):
        super().__init__(message)
        self.retry_after = retry_after


class LLMToolCallGenerationError(RuntimeError):
    """400 tool_use_failed 계열 - 모델이 tool call 인자를 잘못된 JSON으로 생성했을 때.
    Groq에서 실제로 겪은 사례: run_tests처럼 인자가 없는 함수인데도 모델이 이상한
    문자열을 arguments로 생성해서 서버가 파싱에 실패, 요청 자체가 400으로 거부됨.
    일시적인 생성 실패인 경우가 많아 짧게 재시도하면 넘어가는 경우가 많다."""


def _parse_retry_after(error_text: str) -> float | None:
    """Groq는 "try again in 29.73s" 형식을 실제로 확인했다. 다른 provider가 이
    형식을 안 쓰면 None을 반환하고, 호출부가 지수 백오프로 대체한다."""
    m = re.search(r"try again in ([0-9.]+)s", error_text)
    return float(m.group(1)) if m else None


def _classify_error(status: int, body_text: str) -> Exception:
    if status == 429:
        return LLMRateLimitError(body_text, _parse_retry_after(body_text))
    if status == 400 and "tool_use_failed" in body_text:
        return LLMToolCallGenerationError(body_text)
    return RuntimeError(f"{PROVIDER} API 오류 {status}: {body_text}")


def _call_llm_via_curl(body: bytes, api_key: str) -> dict:
    """curl로 호출한다. Cloudflare가 urllib의 TLS/UA 지문을 봇으로 오판해 1010으로
    막는 경우가 있는데(Groq에서 실제로 겪음), curl은 실제 브라우저와 지문이 비슷해
    이 문제를 우회할 수 있다."""
    marker = "__HTTP_STATUS__:"
    proc = subprocess.run(
        [
            "curl", "-sS", "-X", "POST", API_URL,
            "-H", f"Authorization: Bearer {api_key}",
            "-H", "Content-Type: application/json",
            "--data-binary", "@-",
            "-w", f"\n{marker}%{{http_code}}",
        ],
        input=body,
        capture_output=True,
        timeout=120,
    )
    stdout = proc.stdout.decode("utf-8", errors="replace")
    body_text, _, status_str = stdout.rpartition(f"\n{marker}")
    status = int(status_str.strip()) if status_str.strip().isdigit() else 0
    if status < 200 or status >= 300:
        raise _classify_error(status, body_text)
    return json.loads(body_text)


def _call_llm_via_urllib(body: bytes, api_key: str) -> dict:
    req = urllib.request.Request(
        API_URL,
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
        raise _classify_error(e.code, detail) from e


MAX_RATE_LIMIT_RETRIES = 10
MAX_TOOL_GEN_RETRIES = 8


def call_llm(messages: list[dict], api_key: str) -> dict:
    body = json.dumps(
        {"model": MODEL, "messages": messages, "tools": TOOLS, "tool_choice": "auto", "temperature": 0.0}
    ).encode("utf-8")
    caller = _call_llm_via_curl if shutil.which("curl") else _call_llm_via_urllib
    rate_limit_attempts = 0
    tool_gen_attempts = 0
    last_err: Exception | None = None
    while rate_limit_attempts < MAX_RATE_LIMIT_RETRIES and tool_gen_attempts < MAX_TOOL_GEN_RETRIES:
        try:
            return caller(body, api_key)
        except LLMRateLimitError as e:
            rate_limit_attempts += 1
            # retry_after를 서버가 안 줬으면(Gemini 등 미확인 형식) 지수 백오프로 대체.
            wait = (e.retry_after + 2) if e.retry_after is not None else min(2 ** rate_limit_attempts, 60)
            print(f"    (rate limit - {wait:.0f}초 대기 후 재시도 {rate_limit_attempts}/{MAX_RATE_LIMIT_RETRIES})")
            time.sleep(wait)
            last_err = e
        except LLMToolCallGenerationError as e:
            tool_gen_attempts += 1
            print(f"    (tool call 생성 실패 - 3초 후 재시도 {tool_gen_attempts}/{MAX_TOOL_GEN_RETRIES})")
            time.sleep(3)
            last_err = e
    raise RuntimeError(f"재시도 한도 초과: {last_err}")


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
        resp = call_llm(messages, api_key)
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
        "provider": PROVIDER,
        "model": MODEL,
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

    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        print(f"{API_KEY_ENV} 환경변수가 없습니다. export {API_KEY_ENV}=... 로 설정하세요.")
        print(f"(현재 LLM_PROVIDER={PROVIDER}. groq/gemini를 바꾸려면 LLM_PROVIDER 환경변수를 설정하세요.)")
        return 1
    print(f"provider={PROVIDER}, model={MODEL}")

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
