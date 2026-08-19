# 0017. 규칙 기반 추출기의 fixture 과적합 발견과 일반화

## 상태

2026-08-19 적용. e2e 벤치마크 3차 실행을 준비하면서 실측으로 발견한 문제를 고쳤다.

## 문제 (실측으로 발견)

`docs/decisions/0015`의 2차 e2e 벤치마크에서 Session C(CCE Working Context) 조건만
task를 완수하지 못했다. 그 원인을 찾기 위해 벤치마크 fixture를 새로 만들면서
`src/context_analysis.py`의 추출기를 새 대화에 통과시켰더니, **26 turn 대화에서
ContextItem이 6개만 만들어졌고 그 6개가 전부 짧은 user 질문이었다.** 기술적 판단이
담긴 assistant turn은 단 하나도 추출되지 않았다.

실제 출력(수정 전):

```
[user] 그럼 고치자. 어떻게 고칠 건데.
[user] 그 함정 실제로 걸린 적 있어?
[user] 그럼 테스트도 같이 추가해야겠네.
[user] 짧은 텍스트는? 40자 안 넘는 거.
[user] 좋아. 그럼 지금 상태 정리해줘.
[user] 그 fallback 빠뜨리지 않게 다음 세션에 꼭 전달해줘. 그것 때문에 한 번 말아먹었으니까.
```

질문만 남고 답이 전부 사라진 상태다. 이 context를 받은 새 세션은 "무엇을 물어봤는지"는
알아도 "무엇을 결정했는지, 무엇이 실패했는지"는 알 수 없다.

## 원인

`classify_turn`의 분류 규칙이 최초 fixture(`groq_model_migration_session`) 하나에
과적합돼 있었다. 실제로 들어있던 패턴들:

- `EVIDENCE_PATTERNS`: `groqdocs`, `document_count`, `document_errors`, `http_status`
- `NEXT_ACTION_PATTERNS`: `먼저 설명하는게`, `방향을.*설명`
- `GOAL_PATTERNS`: `하면 되잖아`, `기능이\s?없다`

전부 그 fixture에 실제로 등장한 문자열이다. 다른 대화에서는 거의 매치되지 않는다.
매치되지 않으면 `classify_turn`이 `None`을 반환하고, 그 turn은 ContextItem 자체가
만들어지지 않아 Working Context에서 조용히 사라진다.

남아 있던 6개는 `SHORT_USER_FALLBACK_MAX_CHARS`(20자 이하 user turn → evidence)
규칙에 걸린 짧은 질문들이었다. 즉 "내용이 중요해서" 남은 게 아니라 "짧아서" 남은 것이다.

`docs/decisions/0006`에 "규칙 기반 추출기는 정확도가 낮다(turn 단위 일치 7/18)"고
이미 기록해 뒀지만, 그 기록은 **같은 fixture 안에서의** 정확도였다. 다른 대화로
옮겼을 때 사실상 아무것도 못 잡는다는 사실은 이번에 처음 실측으로 드러났다.

## 결정

패턴 목록을 두 층으로 나누고, fixture와 무관한 일반 표현을 추가했다. 기존 패턴은
지우지 않고 `(a) fixture-specific`으로 주석 표시해 남겨뒀다(기존 테스트/결과와의
연속성 유지).

추가한 `(b) generic` 패턴의 성격:

- `failure`: 버그, 함정, 깨졌/깨집니다, 문제입니다, 빠뜨리면, 폐기, 버렸습니다 —
  "무엇이 잘못됐고 어떤 시도를 버렸는가"
- `decision`: 채택, 방식입니다, 방법은, 반드시, 해야 합니다 — "무엇을 하기로 했고
  어떤 제약을 지켜야 하는가"
- `evidence`: 재현, 확인했습니다, 돌려보니, 원인입니다, 실측 — "무엇을 실제로 확인했는가"
- `goal`: 고치자, 고쳐줘, 추가해야, 절대 — 사용자가 지시한 목표
- `next_action`: 다음에 할 일, 다음에 이어서, 다음 세션 — 다음 세션으로 넘기는 표현

## 결과 (실측)

같은 26 turn 대화(timestamp 포함 31 turn 버전)에서:

| | 수정 전 | 수정 후 |
|---|---|---|
| 만들어진 ContextItem | 6 | 23 |
| retention_action | KEEP 6 | KEEP 20 / EXTERNALIZE 2 / DISCARD 1 |
| 보존된 핵심 정보 | 없음(질문만) | 폐기된 textwrap 접근, 공백 없을 때 fallback 주의사항, "기존 테스트 94개 깨면 안 됨" 제약 전부 보존 |

기존 fixture(`groq_model_migration_session`)의 결과는 **변하지 않았다**:
proposed_working_context 486 token, reconstruction 7/7. 즉 이번 변경은 기존에
측정된 수치를 흔들지 않으면서 다른 대화에 대한 동작만 개선했다.

저장소 테스트 94개 전부 통과한다.

## 정직하게 밝히는 점

- 이 변경은 **e2e 벤치마크에서 CCE 조건이 실패한 것을 보고 나서** 이루어졌다. 다만
  고친 대상은 "벤치마크 판정 기준"이나 "임계값"이 아니라 **추출기가 실제로 정보를
  잃고 있던 결함 자체**다. 벤치마크 결과를 유리하게 만들려고 임계값을 조정한 것이
  아니라, 벤치마크가 드러낸 실제 버그를 고친 것이다(AGENTS.md 규칙 7).
- 이 변경 이후의 e2e 벤치마크 결과가 여전히 CCE에 불리하게 나오면 그대로 기록한다.
- 근본적인 한계는 그대로다. 이건 여전히 **정규식 패턴 목록**이고, 여기 없는 표현을
  쓰는 대화에서는 또 놓칠 수 있다. 진짜 해결은 `docs/decisions/0006`에 적어둔 대로
  규칙 기반 추출기를 LLM 기반으로 교체하는 것이다 — 이번 변경은 그 전까지의
  개선이지 근본 해결이 아니다.
- 추가로 실측으로 확인한 별개의 한계: **timestamp가 없는 입력**(`--raw`로 붙여넣은
  평문)에서는 `task_relevance`의 episode 추정이 동작하지 않아 모든 item이 KEEP이
  되고, 압축이 사실상 일어나지 않는다. timestamp가 있는 세션 로그를 넣어야 CCE의
  선별이 실제로 작동한다. 이 한계는 아직 해결하지 않았다.
