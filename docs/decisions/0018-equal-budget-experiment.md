# 0018. 동일 token budget 실험: 구조가 실제로 이득인가

## 상태

2026-08-19 실행 완료. 결과는 `experiments/budget_reconstruction/results/`에 있다.

## 문제

`docs/results.md`의 기존 비교에서 generic summary는 326 token, CCE는 486 token이었고
둘 다 reconstruction 7/7이었다. 이 비교로는 아무것도 결론지을 수 없다:

- CCE가 더 많은 token을 썼으므로, 같은 점수가 나온 건 당연할 수도 있다.
- "구조 덕분에 잘한 것"인지 "예산을 더 써서 잘한 것"인지 **구분이 불가능**하다.

핵심 질문을 다시 세웠다: **동일한 token budget에서 task-aware structured context가
generic summary보다 정보를 더 잘 보존하는가?**

## 먼저 발견한 지표의 결함

실험을 짜면서 기존 지표를 쓸 수 없다는 걸 확인했다. `src/reconstruction_test.py`는
"정답 turn이 context에 있는가"를 **turn_id 포함 여부**로 판정한다. 그런데
`src/baseline.py`의 `generic_summary`는 모든 turn을 길이만 자를 뿐 **버리지 않는다**.
따라서 `in_context_turn_ids`가 항상 전체 집합이고, turn당 5자로 자르든 200자로
자르든 **언제나 7/7 PASS**가 나온다.

즉 기존 지표로는 "예산을 줄이면 정보가 사라진다"는 사실 자체를 측정할 수 없다.
`docs/decisions/0010`에 적어둔 "내용이 있는지만 확인한다"는 한계의 구체적 귀결이다.

그래서 **content recall** 지표를 새로 만들었다
(`experiments/budget_reconstruction/content_recall.py`): 정답 turn의 내용어가
후보 context **텍스트에 실제로 남아있는 비율**을 센다. 텍스트가 잘려 내용어가
사라지면 점수를 잃는다 — 원래 재려던 것이 이것이다.

## 무엇을 바꿨나 (COMPRESS 개선)

기존 `_make_summary`는 turn의 **앞 40자**를 남긴다. 개발 대화에서 핵심(무엇이
실패했는지, 무엇을 결정했는지)은 문장 중간이나 뒤에 오는 경우가 많아 앞부분만
남기면 판단 정보가 사라진다.

`informative_excerpt`는 category 분류를 유발한 패턴이 들어있는 **문장**을 골라
남긴다. 그리고 budget 배분에 category 우선순위 / importance / `depends_on`을 쓴다:

- reconstruction 7문항에 직접 대응하는 category(goal, next_action, current_state,
  decision, failure)를 evidence보다 먼저 넣는다.
- 다른 항목이 `depends_on`으로 참조하는 항목은 우선순위를 한 단계 올린다 — 그
  항목이 빠지면 "근거는?" 질문에 답할 수 없기 때문이다.
- 모든 category가 한 번씩 들어간 뒤 예산이 남으면, 중요도 순으로 excerpt 길이를 늘린다.

`src/`는 건드리지 않았다. 실험 디렉토리 안에서만 동작하므로 기존 테스트 94개와
기존 결과 수치에 영향이 없다.

## 결과 (실측)

| budget(token) | generic mean recall | generic PASS | CCE mean recall | CCE PASS |
|---|---|---|---|---|
| 500 | 0.670 | 5/7 | 0.666 | 3/7 |
| 400 | 0.602 | 3/7 | 0.666 | 3/7 |
| **326** | **0.530** | 3/7 | **0.641** | 3/7 |
| 260 | 0.429 | 3/7 | 0.584 | 3/7 |
| 200 | 0.311 | 1/7 | 0.509 | 3/7 |
| 150 | 0.204 | 0/7 | 0.426 | 2/7 |
| 100 | 0.095 | 0/7 | 0.363 | 2/7 |

**해석:**

- 기존에 문제였던 지점(generic 326 token)에서, **같은 326 token 예산으로 CCE가
  0.641 vs 0.530으로 더 많은 정보를 보존한다.** 질문 7개 전부에서 CCE의 recall이
  같거나 높다(예: "다음 작업은?" 1.0 vs 0.75, "실패한 접근은?" 0.789 vs 0.605).
- **예산이 줄수록 격차가 커진다.** 200 token에서 0.509 vs 0.311, 100 token에서
  0.363 vs 0.095. generic summary는 150 token 이하에서 PASS가 0/7로 무너지지만
  CCE는 2/7을 유지한다. 압축이 심해질수록 "무엇을 남길지 고르는 것"의 가치가 커진다는
  뜻이다 — 이게 이 프로젝트가 주장하려던 바이고, 이번에 처음으로 동일 조건에서 측정됐다.

**CCE에 불리한 결과도 그대로 기록한다:**

- **budget 500에서는 generic이 근소하게 앞선다**(0.670 vs 0.666). 이 구간에서 CCE는
  예산을 다 쓰지 못한다(실제 344 token) — excerpt 길이 상한(`MAX_CHARS=400`)과
  선택된 항목 수에 걸려서다. 예산이 넉넉하면 "그냥 다 넣는" 쪽이 유리하다는 뜻이며,
  구조의 이득은 **예산이 빠듯할 때** 나타난다.
- PASS 개수(임계값 0.5 기준)로 보면 326~400 구간에서 둘 다 3/7로 같다. mean recall은
  CCE가 높지만 PASS 임계값을 넘기는 질문 수는 같다 — 임계값을 어디에 두느냐에 따라
  "이겼다"의 그림이 달라진다는 점을 숨기지 않는다.
- 이 결과는 **fixture 1개**에서 나온 것이다. 일반화할 수 없다.

## 한계

- content recall은 내용어가 남아있는지를 보는 것이지 의미를 이해했는지가 아니다.
  여전히 근사 지표다.
- 불용어 목록과 PASS 임계값(0.5)은 사람이 정한 값이다. 절대 점수는 그 값에 의존한다.
  이 실험은 **같은 지표로 두 방식을 비교**하는 용도로만 읽어야 한다.
- 한국어 어절의 조사/어미를 정규화하지 않는다(형태소 분석기 미사용, 표준 라이브러리
  원칙 유지). 이 불리함은 두 방식에 동일하게 적용된다.
- `informative_excerpt`의 문장 선택은 `src/context_analysis.py`의 정규식 패턴에
  의존한다. 패턴이 없는 표현을 쓰는 대화에서는 이득이 줄어든다(`docs/decisions/0017`
  참조).
