# 문제 정의

## 핵심 문제

AI coding session이 길어지면 context가 증가한다. context가 한계에 도달하면 compaction 또는 session rotation이 발생한다. 이 과정에서 현재 작업에 필요한 context가 손실될 수 있다. 동시에 불필요한 context가 다음 작업에 포함되면 input token 비용이 증가한다.

## 목표

1. 현재 작업에 필요한 context를 보존한다.
2. 불필요한 context를 줄인다.
3. context가 줄어든 뒤 작업 상태가 복원되는지 검증한다.
4. 같은 작업을 수행하는 데 필요한 input token을 줄인다.

## 판단 기준

시스템의 목표는 context를 줄이는 것이 아니다. 작업 상태를 유지하면서 불필요한 context token을 줄이는 것이다.

- context를 줄였지만 작업 상태가 복원되지 않으면 실패로 판단한다.
- context를 유지했지만 token이 줄지 않으면 목표를 달성하지 못한 것으로 판단한다.
- 두 조건을 모두 만족하는 경우에만 제안 방식을 채택한다.

## 선행기술과의 관계

기존 코딩 에이전트(Claude Code, Cursor, Codex CLI, Gemini CLI, GitHub Copilot, OpenCode, Aider)의 compaction은 recency 기준 또는 검증되지 않은 요약 기준으로 동작한다. 압축 전후 상태 복원 정확도를 측정하는 사례는 확인되지 않았다.

연구 단계에서 관련 문제를 다루는 사례가 있다.

- Git Context Controller(GCC): context를 git 커밋 형태로 외부화하고 재조회하는 구조를 제공한다. 의사결정 간 의존성은 다루지 않는다. 복원 정확도를 별도로 측정하지 않는다.
- CompactionRL: 압축 정책을 강화학습으로 훈련한다. 코드와 checkpoint를 공개하지 않는다. 사용자가 보존 결정을 확인하거나 수정할 수 없다.
- SWE Context Bench: 과거의 다른 작업 경험을 재사용했을 때의 성능을 측정한다. 현재 세션의 context 예산 관리를 다루지 않는다.

이 프로젝트는 다음 세 가지에 집중한다.

- recency와 관계없이 현재 작업에 필요한 context를 판단한다.
- 서로 의존하는 결정, 실패, 근거를 함께 보존한다.
- 압축 전후 상태 복원 정확도를 직접 측정한다.

## 오늘 구현 범위

```
Session Log
  ↓
Task Context Analysis
  ↓
Keep / Compress / Externalize
  ↓
Working Context
  ↓
Reconstruction Test
  ↓
Token Comparison
```

입력: TXT, Markdown, JSON 형식 session log.

Baseline: recency truncation, generic summary.

Proposed: task-aware context preservation.

## 오늘 구현하지 않는 것

MCP, Vector DB, Knowledge Graph, Team Memory, IDE extension, multi-agent, RL, real-time hooks, multi-provider integration.

## 확인되지 않음

- task-aware 분류의 실제 정확도. 측정 전.
- 제안 방식이 실제로 비용을 줄이는지. 실험 결과로 판단한다.
- 대회 제출 마감일.
