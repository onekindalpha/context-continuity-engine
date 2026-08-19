# End-to-End Task Completion Benchmark

`docs/results.md`의 reconstruction test(7문항, "내용이 있는지"만 확인)보다 더 엄격한 기준으로
CCE를 검증한다: **새 세션이 실제 코딩 task를 실제로 완수하는가**를 실제 LLM tool-calling +
실제 파일 변경 + 실제 테스트 실행으로 측정한다.

이건 `docs/results.md`의 측정을 대체하지 않는다 — 그 측정(reconstruction test)은 보조 지표로
계속 유지되고, 이 벤치마크가 최종 핵심 지표(task success)를 추가로 제공한다.

## 왜 별도 디렉토리인가

`src/`(핵심 파이프라인, 테스트 94개)와 완전히 분리했다. 이 실험이 실패하거나 미완성이어도
기존에 검증된 CLI/파이프라인에는 전혀 영향이 없다.

## 사전 조건

- **네트워크가 되는 환경에서 실행해야 한다.** 이 코드를 만든 sandbox 환경은 `api.groq.com`과
  `generativelanguage.googleapis.com` 둘 다 네트워크 허용 목록에 없어 자체적으로 실행이
  불가능했다 — 로컬 머신(Terminal.app)에서 실행하세요.
- API 키는 둘 중 하나(**이 키들을 코드나 커밋에 절대 넣지 마세요.** 환경변수로만 전달합니다):
  - Groq(기본값): `export GROQ_API_KEY=...` (Groq 콘솔에서 발급)
  - Gemini(대안): `export LLM_PROVIDER=gemini` + `export GEMINI_API_KEY=...` (Google AI Studio에서 발급).
    Groq 무료 tier(분당 6,000~8,000 token)가 이 벤치마크 규모에 비해 작아 재시도가 오래 걸릴 때
    대안으로 추가했다 — Gemini Flash-Lite 계열 무료 tier는 분당 약 250,000 token으로 더 여유롭다
    (2026-08 웹 검색으로 확인한 수치, provider 정책은 바뀔 수 있다). 둘 다 OpenAI 호환
    chat/completions 형식이라 harness의 tool-calling 로직은 그대로 재사용한다.
- Python 3.9+, 표준 라이브러리만 사용(추가 설치 불필요).

## 실행

```bash
# Groq (기본값)
export GROQ_API_KEY=여기에_본인_키
bash experiments/e2e_benchmark/run_all.sh

# 또는 Gemini
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=여기에_본인_키
bash experiments/e2e_benchmark/run_all.sh
```

3단계를 순서대로 실행한다: context 3종 생성 → Session A/B/C 각각 독립 git worktree에서 실제
tool-calling 실행(각 조건당 최대 25 round) → 결과 리포트 생성.

개별 조건만 실행하려면: `python3 experiments/e2e_benchmark/harness.py --condition a` (a=원본 전체,
b=generic summary, c=CCE Working Context).

## 무엇을 실제로 하는가

각 조건마다:

1. 현재 커밋에서 독립된 `git worktree`를 만든다(서로 완전히 격리됨, 서로의 결과에 영향 없음).
2. LLM에게 해당 조건의 context(Session A/B/C)와 task(`task.md` — 실제 미해결 과제)를 준다.
3. LLM이 `read_file`/`write_file`/`list_files`/`run_tests`/`run_comparison` tool을 실제로
   호출하며 `src/context_analysis.py`, `src/working_context.py`를 실제로 고친다.
4. harness가 LLM의 "다 됐습니다"라는 말을 믿지 않고, worktree에서 직접
   `python3 -m unittest discover -s tests`와 `scripts/run_comparison.py`를 실행해서
   실제로 조건을 만족하는지 판정한다.
5. 결과(성공 여부, token 사용량, tool 호출 횟수, 비용 근사치, 소요 시간)를 JSON으로 남긴다.

## 결과 읽는 법

`results/summary.md`에 조건별 비교표가 생긴다. `task_success`가 최종 핵심 지표다 — 세 조건이
같은 task를 받고 같은 tool을 쓰지만, 시작할 때 주어지는 memory(context)만 다르다.

## 정직하게 밝히는 한계

- 실행 1회 기준이다(모델 비결정성 때문에 여러 번 돌려야 신뢰도가 올라간다 — 아직 안 함).
- `estimated_cost_usd_approx`는 `harness.py`에 하드코딩된 근사 단가다. 실제 청구액이 아니다
  (`LLM_PRICE_INPUT_PER_1M`, `LLM_PRICE_OUTPUT_PER_1M` 환경변수로 조정 가능).
- Session A/B는 저장소 파일 원문을 이어붙인 것이고 Session C는 이 문제에 대한 실제 대화를
  CCE로 압축한 것이다 — "무엇을 memory로 주는가"의 성격이 다르다. agent가 `read_file`로 현재
  코드는 언제든 다시 읽을 수 있으므로, 이 실험이 실제로 비교하는 것은 "이전 판단/실패 이력이
  보존되는가"이지 "코드 원문 접근 가능 여부"가 아니다.
- fixture 1개, task 1개로 측정한 결과다. `docs/results.md`의 일반화 한계와 동일하게 적용된다.
- 이 실험 자체가 CCE 우위를 증명하지 못하면(예: task_success가 세 조건 다 false이거나, A/B가
  더 낫게 나오면) 그 결과를 그대로 기록한다. 유리하게 조정하지 않는다(AGENTS.md 규칙 7).
