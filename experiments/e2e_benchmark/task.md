# Benchmark task (실제 미해결 과제)

이 프로젝트가 실제로 아직 풀지 못한 문제를 그대로 벤치마크 task로 쓴다. 조작된 예제가 아니다 — `docs/results.md`의 "다음 개선 과제"에 실제로 등록된 항목이다.

## 지시문 (LLM에게 그대로 전달되는 문장)

> `context-continuity-engine` 프로젝트에서 `src/context_analysis.py`와 `src/working_context.py`를 수정해서, `examples/groq_model_migration_session` fixture 기준으로 `scripts/run_comparison.py` 실행 결과의 `proposed_working_context` token 사용량을 `baseline_generic_summary`(326 token) 미만으로 줄여라. 단, 다음 두 조건을 반드시 지켜야 한다:
> 1. `python3 -m unittest discover -s tests`가 전부 통과해야 한다(기존 테스트를 깨면 안 된다).
> 2. reconstruction test 7문항 중 7문항 PASS(`comparison_result.json`의 `results.proposed_working_context.summary`)를 유지해야 한다 — token을 줄이려고 정답을 지우면 안 된다.
> 코드를 수정한 뒤 `python3 scripts/run_comparison.py`를 실행해서 결과를 직접 확인하고, 조건을 만족했다고 판단되면 종료해라.

## 판정 기준 (자동, harness.py가 실행)

작업이 끝난 뒤(또는 최대 turn 수 도달 후) harness가 해당 worktree에서 직접 실행해서 판정한다 — LLM의 자기 보고를 믿지 않는다.

1. `python3 -m unittest discover -s tests` exit code == 0
2. `scripts/run_comparison.py` 실행 후 `comparison_result.json`에서:
   - `token_usage.proposed_working_context.tokens` < 326
   - `results` 요약에서 proposed_working_context PASS 수 == 7

두 조건을 모두 만족해야 `task_success = true`.

## 왜 이 task인가

- 실제로 존재하는, 아직 안 풀린 문제다(`docs/results.md` "다음 개선 과제" 참조) — 조작 없음.
- Context 의존성이 명확하다: 이 task를 제대로 풀려면 "SUMMARY_MAX_CHARS를 이미 120→40으로 낮춰봤지만 그것만으로는 부족했다", "KEEP 항목이 원문 그대로라 길다", "무작정 KEEP을 자르면 reconstruction이 깨질 수 있다"는 사전 지식이 있어야 한다. Context가 부실하면 이미 시도했던 접근(SUMMARY_MAX_CHARS 재조정)을 또 시도하거나, reconstruction을 깨뜨리면서 token만 줄이는 실수를 할 가능성이 높다 — 이게 정확히 "failed approach 재사용 여부", "decisions retained" 측정 포인트다.
