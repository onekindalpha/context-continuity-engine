# 시연 영상 스크립트 (3분 이내)

목적: 결과보고서 제출용 시연 영상. 대회 가이드 기준 3분 이내, 유튜브 업로드 후 링크 기재.

## 구성 (총 3분 목표)

### 0:00–0:25 — 문제 제시

화면: `docs/problem.md` 또는 README를 띄운다.

대사(예시, 그대로 읽지 않아도 됨):
"AI coding session이 길어지면 context가 쌓입니다. context가 한계에 도달하면 압축이나 세션 교체가 일어나는데, 이 과정에서 지금 작업에 필요한 정보가 사라지거나, 반대로 불필요한 정보가 그대로 남아 token 비용만 늘어납니다. 이 프로젝트는 필요한 context는 남기고 불필요한 context는 줄이는 도구입니다."

### 0:25–0:55 — 파이프라인 구조

화면: `docs/architecture.md`의 파이프라인 다이어그램.

대사:
"세션 로그를 받아서, 문장을 목표/현재 상태/결정/실패/근거/다음 작업 6개 category로 분류하고, 각 항목의 중요도와 현재 작업 관련도를 계산합니다. 그 값을 기준으로 그대로 유지할지, 요약할지, 외부에 보관할지, 버릴지를 규칙으로 정합니다."

### 0:55–1:40 — 실제 실행

화면: 터미널.

```bash
python3 scripts/run_context_analysis.py
python3 scripts/run_comparison.py
cat examples/groq_model_migration_session/comparison_result.md
```

대사:
"실제 개발 세션 20턴을 넣고 돌린 결과입니다. 원본은 1311 token인데, 저희 방식은 581 token으로 줄었습니다. 다만 이번 측정에서는 baseline 방식인 recency truncation(395 token)보다 오히려 더 많은 token을 썼습니다. 원인을 코드로 추적했고, 결과와 원인은 docs/results.md에 그대로 남겼습니다."

### 1:40–2:20 — 정직하게 한계 설명

화면: `docs/results.md`.

대사:
"이 프로젝트의 판정 기준은 저희가 직접 정했습니다. baseline보다 token이 늘거나 재구성 정확도가 낮으면 실패로 판단합니다. 지금 결과는 그 기준으로 보면 아직 baseline을 이기지 못했습니다. 원인은 두 가지입니다. 첫째, 규칙 기반 추출기가 목표/결정 category를 놓치는 경우가 있습니다. 둘째, 압축 시 요약 길이가 baseline의 절삭 길이보다 깁니다. 두 가지 모두 GitHub Issue로 등록해서 다음 개선 과제로 관리하고 있습니다."

### 2:20–2:50 — 저장소/테스트/거버넌스

화면: GitHub 저장소 페이지, Issues 탭, 병합된 PR, 테스트 실행 화면.

```bash
python3 -m unittest discover -s tests
```

대사:
"테스트 75개가 모두 통과합니다. 실험적인 변경은 브랜치와 PR로 나눠서 진행했고, 각 결정은 docs/decisions/ 아래에 이유와 함께 기록해뒀습니다."

### 2:50–3:00 — 마무리

대사:
"필요한 context는 남기고 불필요한 context는 줄인다는 목표에서, 지금은 baseline 대비 우위를 아직 증명하지 못한 상태입니다. 다음 단계는 요약 길이 조정과 추출기 개선입니다."

## 녹화 체크리스트

- [ ] 화면 녹화 도구 준비 (QuickTime 화면 녹화 등)
- [ ] 터미널 글씨 크기 키우기 (심사위원이 봐야 함)
- [ ] `python3 -m unittest discover -s tests` 결과가 `OK`로 끝나는 장면 포함
- [ ] `comparison_result.md` 표가 화면에 잘 보이는지 확인
- [ ] GitHub 저장소의 Issues/PR 화면 포함(팀워크 항목)
- [ ] 3분 이내로 자르기
- [ ] 유튜브 업로드(공개 또는 링크 공개) 후 링크를 결과보고서에 기재
