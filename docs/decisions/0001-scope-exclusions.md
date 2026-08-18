# 0001. 범위 제외

## 상태

확정

## 배경

선행기술 조사에서 GCC, CompactionRL, SWE Context Bench, 6개 코딩 에이전트, 5개 handoff 프로젝트를 확인했다. 조사 결과는 별도 문서에 있다.

## 결정

다음 기능은 오늘 구현 범위에서 제외한다.

| 항목 | 이유 |
|---|---|
| MCP 서버화 | 배포 형태 결정 전, 핵심 로직 검증이 우선 |
| Vector DB | 대상 문제가 검색이 아니라 현재 세션의 선별/압축/재구성 |
| Knowledge Graph | 대상 문제가 다중 세션 지식 축적이 아니라 단일 세션 연속성 |
| Team Memory | 대상 사용자가 개인 개발자, 팀 공유는 범위 밖 |
| IDE extension | 실시간 연동 전, CLI 단위 검증이 우선 |
| multi-agent | 단일 세션 문제 해결이 우선 |
| RL 기반 정책 학습 | CompactionRL 검증 결과, 자체 ablation 기준 RL 학습 유무 차이가 크지 않음. 강한 non-RL 베이스라인과 비교한 근거도 없음 |
| real-time hooks | 특정 에이전트(Claude Code 등) 종속 위험. 독립 CLI로 먼저 검증 |
| multi-provider integration | 단일 모델 기준 검증이 먼저, 확장은 이후 판단 |

## 재검토 조건

MVP의 reconstruction accuracy와 token efficiency 측정이 끝난 후 재검토한다.
