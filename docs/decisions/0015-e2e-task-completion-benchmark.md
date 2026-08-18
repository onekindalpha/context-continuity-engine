# 0015. End-to-End Task Completion Benchmark

## 상태

확정(harness 구현 완료). 실제 실행은 네트워크가 되는 환경(사용자 로컬 머신)에서 해야 한다 — sandbox에서는 `api.groq.com`이 네트워크 허용 목록에 없어 자체 실행이 불가능함을 확인했다(403).

## 결정

`docs/results.md`의 reconstruction test(내용이 context에 "있는지"만 확인하는 근사 지표, `docs/decisions/0010`)보다 엄격한 최종 지표로, 실제 LLM이 실제 coding task를 완수하는지를 실제로 측정하는 벤치마크를 `experiments/e2e_benchmark/`에 추가했다. `src/`(핵심 파이프라인, 테스트 94개)와는 완전히 분리된 별도 디렉토리다 — 이 실험이 실패해도 기존에 검증된 CLI/파이프라인엔 영향이 없다.

설계:

- **task**: 이 프로젝트의 실제 미해결 과제(COMPRESS를 baseline_generic_summary(326 token)보다 효율적으로 만들되 reconstruction 7/7 유지)를 그대로 쓴다. 조작된 예제가 아니다.
- **3 조건**: Session A(관련 문서/코드/테스트 전문을 이어붙인 것), Session B(각 파일을 200자로 균일 절삭), Session C(이 문제에 대한 실제 대화를 CCE 자신의 `--raw` 파이프라인으로 압축한 실제 출력 — dogfooding).
- **격리**: 조건마다 독립된 `git worktree`에서 실행해 서로 영향을 주지 않는다.
- **실제 tool call**: Groq API(OpenAI 호환 tool-calling)로 `read_file`/`write_file`/`list_files`/`run_tests`/`run_comparison`을 실제로 호출하며 실제 파일을 수정한다. 임의 shell 실행은 허용하지 않는다(사용자 로컬 머신에서 실행되므로, prompt injection에 의한 위험 동작을 막기 위해 tool을 이 5개로 제한했다).
- **판정**: LLM의 자기 보고를 신뢰하지 않는다. harness가 worktree에서 직접 테스트와 비교 스크립트를 실행해서 판정한다.
- **기록**: JSON(`results/*.json`, `results/summary.json`) + Markdown(`results/summary.md`) 둘 다 생성한다.

## 이유

사용자가 제안한 설계: "최종 핵심 지표를 '새 세션이 실제 task를 성공적으로 이어갔는가'로 바꿔라. Generic Summary보다 CCE가 token이 더 많아도 괜찮다. 실험 결과가 CCE 우위를 증명하지 못하면 그대로 기록하고 알고리즘을 억지로 유리하게 바꾸지 마라." — reconstruction test는 "정답 turn의 내용이 있는지"만 보는 근사 지표라는 한계가 있었는데(`docs/decisions/0010`), 이건 실제 downstream 작업 성공 여부를 직접 본다는 점에서 훨씬 엄격하고 설득력 있는 증거다.

## 범위

- 실행은 사용자 로컬 머신에서 해야 한다(네트워크 제약, 위 참조).
- `GROQ_API_KEY`는 환경변수로만 전달한다. 코드/커밋에 절대 포함하지 않는다.
- fixture 1개, task 1개, 조건당 실행 1회 기준. 모델 비결정성을 감안한 반복 실행은 하지 않았다.

## 알려진 한계

- `estimated_cost_usd_approx`는 하드코딩된 근사 단가 기준이다. 실제 청구액이 아니다.
- `approx_re_explanation_turns`는 tool 호출 실패 횟수로 근사한 것이다 — 완전 자동 실행이라 실제 사용자가 없으므로 "재설명 요청"을 직접 측정할 수 없다.
- Session A/B는 파일 원문을 이어붙인 것이고 Session C는 대화 압축본이라, "무엇을 memory로 주는가"의 성격이 다르다. agent가 `read_file`로 현재 코드는 언제든 읽을 수 있으므로, 이 벤치마크가 실제로 비교하는 것은 "이전 판단/실패 이력의 보존 여부"이지 "코드 원문 접근 가능 여부"가 아니다 — README에 명시했다.
- 결과가 CCE에 유리하게 나오지 않을 수 있다. 그 경우에도 그대로 기록한다(AGENTS.md 규칙 7).
