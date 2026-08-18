#!/usr/bin/env bash
# 3분 데모용 단일 실행 명령.
# 사전 조건: export GROQ_API_KEY=... (Groq 콘솔에서 발급, 이 저장소 어디에도 커밋하지 말 것)
#
# 이 스크립트는 실제 네트워크(Groq API)가 필요하다. sandbox에서는 api.groq.com이
# 막혀 있어 실행할 수 없다 - 반드시 사용자 로컬 머신에서 실행해야 한다.
set -euo pipefail
cd "$(dirname "$0")/../.."

if [ -z "${GROQ_API_KEY:-}" ]; then
  echo "GROQ_API_KEY 환경변수가 필요합니다. export GROQ_API_KEY=... 후 다시 실행하세요."
  exit 1
fi

echo "1/3: context 3종 생성 중..."
python3 experiments/e2e_benchmark/build_contexts.py

echo ""
echo "2/3: 3-way benchmark 실행 중 (Session A/B/C, 각각 독립 git worktree + 실제 Groq tool-calling)..."
python3 experiments/e2e_benchmark/harness.py --condition all

echo ""
echo "3/3: 결과 리포트 생성 중..."
python3 experiments/e2e_benchmark/build_report.py

echo ""
echo "완료: experiments/e2e_benchmark/results/summary.md, summary.json"
