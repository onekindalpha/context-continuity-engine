# AGENTS.md

이 문서는 이 저장소에서 작업하는 AI 에이전트가 따르는 규칙을 정의한다.

## 프로젝트 방향

목표: 필요한 context는 남기고, 불필요한 context는 줄여 작업 연속성과 token 효율을 확보한다.

## 핵심 문제

AI coding session이 길어지면 context가 증가한다. context가 한계에 도달하면 compaction 또는 session rotation이 발생한다. 이 과정에서 현재 작업에 필요한 context가 손실될 수 있다. 동시에 불필요한 context가 다음 작업에 포함되면 input token 비용이 증가한다.

## 작업 규칙

1. 기능을 추가하기 전에 평가 목적을 docs 또는 PR에 적는다.
2. dependency를 추가하기 전에 이유를 PR 설명에 적는다.
3. 실패한 접근을 `docs/decisions/`에 기록한다.
4. 결과를 테스트로 검증한다. 테스트 없는 기능은 병합하지 않는다.
5. main에 직접 실험 코드를 넣지 않는다. 실험은 branch 또는 issue에서 진행한다.
6. 이미 구현된 기능을 다시 만들지 않는다. 추가하기 전에 기존 코드를 확인한다.
7. 근거 없는 성능 수치를 작성하지 않는다. 측정하지 않은 값은 "측정 전"으로 표시한다.

## 문장 스타일 규칙

한국어 문서에서 형용사, 부사, 지시어, 추상적 수식어를 최소화한다.

예:
- "매우 강력한 시스템" → "시스템"
- "이러한 방식" → "방식"
- "효율적으로 처리한다" → "처리한다"

문장 구성: 주체 + 행동 + 대상 + 근거 + 결과.

수식어는 의미를 추가하는 경우에만 사용한다.

적용 범위: README, Issue, PR, docs, 발표 원고.

## 범위 제외 (오늘 기준)

MCP, Vector DB, Knowledge Graph, Team Memory, IDE extension, multi-agent, RL, real-time hooks, multi-provider integration.

이유: `docs/decisions/0001-scope-exclusions.md` 참조.

## 평가 원칙

제품 평가는 다음 두 지표를 함께 본다.

- Context reconstruction accuracy
- Token efficiency

추가 지표: repeated questions, repeated failed approaches, task success.

context 분석 자체도 LLM 호출 비용을 발생시킨다. 분석 비용을 포함한 전체 token usage를 측정한다.

세부 절차는 `docs/evaluation.md`에 정의한다.
