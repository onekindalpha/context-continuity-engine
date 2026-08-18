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
pip install -e .
context-continuity-engine examples/groq_model_migration_session/session.txt --raw | pbcopy
python3 scripts/run_comparison.py
cat examples/groq_model_migration_session/comparison_result.md
```

대사:
"실제 개발 세션 20턴을 넣고 돌린 결과입니다. 원본은 1311 token인데, 저희 방식은 486 token으로 줄었습니다(62.9% 감소). 재구성 테스트 7문항은 전부 통과합니다. 가장 단순한 baseline인 recency truncation은 6/7만 통과하는데, 저희는 token을 조금 더 쓰는 대신(486 vs 395) 그 baseline이 놓치는 질문까지 답합니다."

### 1:40–2:20 — 정직하게 한계 설명

화면: `docs/results.md`.

대사:
"다만 모든 baseline을 모든 지표에서 이긴 건 아닙니다. 모든 turn을 균일하게 짧게 자르기만 하는 또 다른 baseline(generic summary)은 재구성 품질은 저희와 동률(7/7)이면서 token은 더 적게 씁니다(326 vs 486). 이 프로젝트가 스스로 정한 판정 기준으로 보면, 지금은 '하나는 이기고 하나는 아직'이라는 게 정직한 상태입니다. 남은 원인은 규칙 기반 추출기의 정확도 한계이고, 다음 개선 과제로 GitHub Issue에 등록해 관리하고 있습니다."

### 2:20–2:50 — 저장소/테스트/거버넌스

화면: GitHub 저장소 페이지, Issues 탭, 병합된 PR, 테스트 실행 화면.

```bash
python3 -m unittest discover -s tests
```

대사:
"테스트 94개가 모두 통과합니다. 실험적인 변경은 브랜치와 PR로 나눠서 진행했고, 각 결정은 docs/decisions/ 아래에 이유와 함께 기록해뒀습니다."

### 2:50–3:00 — 마무리

대사:
"필요한 context는 남기고 불필요한 context는 줄인다는 목표에서, 가장 단순한 baseline 하나는 재구성 품질로 앞섰고 다른 하나는 아직입니다. 다음 단계는 규칙 기반 추출기 개선과 fixture 확대 검증입니다."

## 녹화 체크리스트

- [ ] 화면 녹화 도구 준비 (QuickTime 화면 녹화 등)
- [ ] 터미널 글씨 크기 키우기 (심사위원이 봐야 함)
- [ ] `python3 -m unittest discover -s tests` 결과가 `OK`로 끝나는 장면 포함
- [ ] `comparison_result.md` 표가 화면에 잘 보이는지 확인
- [ ] GitHub 저장소의 Issues/PR 화면 포함(팀워크 항목)
- [ ] 3분 이내로 자르기
- [ ] 유튜브 업로드(공개 또는 링크 공개) 후 링크를 결과보고서에 기재
