"""Session log ingest.

TXT, Markdown, JSON 형식의 session log를 공통 내부 표현(SessionLog)으로 변환한다.

평가 목적: 이후 모든 단계(Task Context Analysis, Baseline, Reconstruction Test)가
이 모듈의 출력에 의존한다. 이 모듈은 구조 파싱만 담당한다.

이 모듈이 하지 않는 것:
- relevance scoring
- dependency analysis
- compaction (keep/compress/externalize/discard)
- LLM 호출

의존성: 표준 라이브러리만 사용한다(json, re, dataclasses, pathlib). 추가 dependency 없음.

스키마: docs/architecture.md, docs/decisions/0003-ingest-output-schema.md 참조.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1"

# TXT 형식 turn 구분자: "[timestamp] SPEAKER:"
TXT_TURN_RE = re.compile(r"^\[(?P<timestamp>[^\]]*)\]\s*(?P<speaker>[A-Za-z_]+):\s*$")

# Markdown 형식 turn 구분자: "### SPEAKER — timestamp"
MD_TURN_RE = re.compile(r"^###\s+(?P<speaker>[A-Za-z_]+)\s+—\s+(?P<timestamp>\S+)\s*$")

REQUIRED_JSON_TURN_FIELDS = ("speaker", "text")
KNOWN_SPEAKERS = ("user", "assistant")


@dataclass
class Turn:
    turn_id: int
    speaker: str
    timestamp: str | None
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "speaker": self.speaker,
            "timestamp": self.timestamp,
            "text": self.text,
        }


@dataclass
class SessionLog:
    schema_version: str
    source_format: str
    session_id: str | None
    turns: list[Turn]
    warnings: list[str] = field(default_factory=list)

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_format": self.source_format,
            "session_id": self.session_id,
            "turns": [t.to_dict() for t in self.turns],
            "turn_count": self.turn_count,
            "warnings": self.warnings,
        }


def _normalize_speaker(raw: str) -> str:
    speaker = raw.strip().lower()
    if speaker in KNOWN_SPEAKERS:
        return speaker
    return "unknown"


def _error(message: str) -> dict[str, Any]:
    return {"ok": False, "session": None, "error": message}


def _ok(session: SessionLog) -> dict[str, Any]:
    return {"ok": True, "session": session.to_dict(), "error": None}


def ingest_txt(text: str, session_id: str | None = None) -> dict[str, Any]:
    return _ingest_delimited(text, TXT_TURN_RE, "txt", session_id)


def ingest_markdown(text: str, session_id: str | None = None) -> dict[str, Any]:
    return _ingest_delimited(text, MD_TURN_RE, "markdown", session_id)


def _ingest_delimited(
    text: str, pattern: re.Pattern[str], source_format: str, session_id: str | None
) -> dict[str, Any]:
    turns: list[Turn] = []
    warnings: list[str] = []
    current_speaker: str | None = None
    current_timestamp: str | None = None
    current_body: list[str] = []

    def flush() -> None:
        if current_speaker is None:
            return
        body_text = "\n".join(current_body).strip()
        turns.append(
            Turn(
                turn_id=len(turns),
                speaker=_normalize_speaker(current_speaker),
                timestamp=current_timestamp,
                text=body_text,
            )
        )

    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            flush()
            current_speaker = match.group("speaker")
            current_timestamp = match.group("timestamp").strip() or None
            current_body = []
            continue
        if current_speaker is not None:
            current_body.append(line)
        elif line.strip():
            warnings.append("ignored content before first turn delimiter")
    flush()

    if not turns:
        warnings.append("session has no turns")

    session = SessionLog(
        schema_version=SCHEMA_VERSION,
        source_format=source_format,
        session_id=session_id,
        turns=turns,
        warnings=warnings,
    )
    return _ok(session)


def ingest_json(raw: str, session_id: str | None = None) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return _error(f"invalid JSON: {exc}")

    if not isinstance(data, dict):
        return _error("invalid JSON: top-level value must be an object")

    if "turns" not in data:
        return _error("missing required field: turns")

    raw_turns = data["turns"]
    if not isinstance(raw_turns, list):
        return _error("invalid JSON: 'turns' must be a list")

    turns: list[Turn] = []
    warnings: list[str] = []

    for index, raw_turn in enumerate(raw_turns):
        if not isinstance(raw_turn, dict):
            return _error(f"invalid turn at index {index}: must be an object")
        for required in REQUIRED_JSON_TURN_FIELDS:
            value = raw_turn.get(required)
            if value is None or not str(value).strip():
                return _error(f"missing required field: {required} at turn {index}")
        turns.append(
            Turn(
                turn_id=index,
                speaker=_normalize_speaker(str(raw_turn["speaker"])),
                timestamp=raw_turn.get("timestamp"),
                text=str(raw_turn["text"]).strip(),
            )
        )

    if not turns:
        warnings.append("session has no turns")

    session = SessionLog(
        schema_version=SCHEMA_VERSION,
        source_format="json",
        session_id=data.get("session_id", session_id),
        turns=turns,
        warnings=warnings,
    )
    return _ok(session)


def ingest_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return _error(f"file not found: {p}")

    suffix = p.suffix.lower()
    text = p.read_text(encoding="utf-8")

    if suffix == ".json":
        return ingest_json(text)
    if suffix in (".md", ".markdown"):
        return ingest_markdown(text)
    if suffix == ".txt":
        return ingest_txt(text)
    return _error(f"unsupported file extension: {suffix}")
