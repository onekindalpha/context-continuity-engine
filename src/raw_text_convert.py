"""느슨한 형식의 대화 텍스트를 ingest_json이 받는 형식으로 변환한다.

평가 목적: TXT 형식(`[timestamp] speaker:`)은 채팅 화면에서 그대로 복사한
텍스트의 실제 모습이 아니다. 사용자가 매번 정확한 형식으로 손으로 맞추는
수고를 없애려면, "화자: 내용" 정도의 느슨한 표시만으로도 동작하는 변환기가
따로 있어야 한다.

이 모듈은 `src/ingest.py`의 엄격한 형식 요구사항을 바꾸지 않는다. 그 앞에
붙는 별도 전처리 단계다(docs/decisions/0012).

지원 형식: 한 줄이 "화자:" 또는 "화자："로 시작하면 새 turn이 시작된다.
화자 별칭은 SPEAKER_ALIASES에 등록된 것만 인식한다. 그 외 줄은 직전
turn에 이어붙인다. 첫 turn 이전 내용은 버리고 warnings에 남긴다.

의존성: 표준 라이브러리만 사용한다.
"""

from __future__ import annotations

import re
from typing import Any

SPEAKER_ALIASES = {
    "user": "user",
    "나": "user",
    "사용자": "user",
    "질문": "user",
    "me": "user",
    "assistant": "assistant",
    "claude": "assistant",
    "클로드": "assistant",
    "ai": "assistant",
    "답변": "assistant",
    "gpt": "assistant",
    "chatgpt": "assistant",
}

_SPEAKER_RE = re.compile(
    r"^(?P<speaker>" + "|".join(re.escape(k) for k in SPEAKER_ALIASES) + r")\s*[:：]\s*(?P<rest>.*)$",
    re.IGNORECASE,
)


def convert(text: str) -> dict[str, Any]:
    """느슨한 형식 텍스트를 {"turns": [...], "warnings": [...]}로 변환한다."""
    turns: list[dict[str, str]] = []
    warnings: list[str] = []
    current_speaker: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_speaker is None:
            return
        body = "\n".join(current_lines).strip()
        if body:
            turns.append({"speaker": current_speaker, "text": body})

    for line in text.splitlines():
        match = _SPEAKER_RE.match(line.strip())
        if match:
            flush()
            current_speaker = SPEAKER_ALIASES[match.group("speaker").lower()]
            rest = match.group("rest")
            current_lines = [rest] if rest else []
            continue
        if current_speaker is not None:
            current_lines.append(line)
        elif line.strip():
            warnings.append("첫 화자 표시 이전 내용 무시됨")
    flush()

    if not turns:
        warnings.append("인식된 turn 없음 — '화자: 내용' 형식으로 최소 한 줄 필요")

    return {"turns": turns, "warnings": warnings}
