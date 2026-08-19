"""Task Context Analysis: SessionLog -> ContextItem 추출 (규칙 기반 baseline).

평가 목적: LLM 없이 결정적(deterministic)으로 동작하는 첫 baseline을 만들어
schema(docs/decisions/0004, 0005)가 실제 파이프라인에서 채워질 수 있는지
검증한다. 결과는 src/validate.py로 검사한다.

이 모듈이 하지 않는 것:
- LLM 호출 (이유: docs/decisions/0006)
- 의미 요약(paraphrase). summary는 원문 앞부분을 잘라낸 값이다.
- compaction 실행(Working Context 생성). retention_action까지만 계산한다.

파이프라인 순서: SessionLog -> ContextItem 추출(카테고리 분류) ->
task_relevance 계산(시간 간격 기반 episode 추정) -> dependency 연결 ->
importance 보정(의존 대상 여부 반영) -> retention_action 결정.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

SCHEMA_VERSION = "1"
SUMMARY_MAX_CHARS = 40

# --- 1. turn -> category 분류 규칙 (우선순위 순서, 첫 매치 채택) ---

# 아래 규칙들은 두 층으로 나뉜다:
#   (a) fixture-specific: 최초 fixture(groq_model_migration_session)에서 관찰한 표현.
#   (b) generic: 특정 fixture와 무관하게 개발 대화 일반에 나타나는 표현.
# (b)를 나중에 추가한 이유는 docs/decisions/0017 참조 - e2e 벤치마크에서 새 대화를
# 넣었을 때 assistant turn이 거의 하나도 추출되지 않는 문제가 실측으로 드러났기 때문이다.

FAILURE_PATTERNS = [
    # (a) fixture-specific
    r"error code",
    r"오류",
    r"에러",
    r"실패",
    r"안\s?보여",
    r"no module",
    r"not found",
    r"model_not_found",
    r"unsupported file type",
    # (b) generic: 버그/함정/깨짐/폐기된 시도
    r"버그",
    r"함정",
    r"깨졌",
    r"깨집니다",
    r"깨면",
    r"안 맞습니다",
    r"문제입니다",
    r"빠뜨리면",
    r"말아먹",
    r"폐기",
    r"버렸습니다",
    r"잘못된",
]

# current_state: "커밋 완료"류 표현 + git 커밋 해시(7자리 16진수 유사 문자열)가 같이 나오는 turn.
CURRENT_STATE_HASH_RE = re.compile(r"\b[0-9a-f]{7}\b")
CURRENT_STATE_PATTERNS = [
    r"커밋 완료",
    r"커밋했습니다",
    r"완료했습니다",
]

EVIDENCE_PATTERNS = [
    # (a) fixture-specific
    r"http_status",
    r"deprecated",
    r"web search results",
    r"groqdocs",
    r"공식 문서",
    r"확인했는데",
    r"document_count",
    r"document_errors",
    r"git log",
    # (b) generic: 재현/실측으로 확인한 근거
    r"재현",
    r"확인했습니다",
    r"돌려보니",
    r"원인입니다",
    r"실측",
]

DECISION_PATTERNS = [
    # (a) fixture-specific
    r"하기로",
    r"결정",
    r"추가하겠습니다",
    r"교체하겠습니다",
    r"통합하겠습니다",
    r"정리하겠습니다",
    r"바꾸겠습니다",
    # (b) generic: 방식 채택/제약 명시
    r"채택",
    r"방식입니다",
    r"방법은",
    r"하는 게 맞습니다",
    r"반드시",
    r"해야 합니다",
    r"어긋나지 않습니다",
    r"근본 해결이 아닙니다",
]

GOAL_PATTERNS = [
    # (a) fixture-specific
    r"되어야",
    r"하면 되잖아",
    r"기능이\s?없다",
    # (b) generic: 사용자가 지시하는 목표
    r"고치자",
    r"고쳐줘",
    r"추가해야",
    r"해야겠네",
    r"절대",
]

NEXT_ACTION_PATTERNS = [
    # (a) fixture-specific
    r"먼저 설명하는게",
    r"방향을.*설명",
    # (b) generic: 다음 세션으로 넘기는 표현
    r"다음에 할 일",
    r"다음에 이어서",
    r"다음 세션",
    r"이어서 할",
]

SHORT_USER_FALLBACK_MAX_CHARS = 20


def _matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def classify_turn(speaker: str, text: str, is_last_turn: bool) -> str | None:
    """turn 하나를 category로 분류한다. 매치되는 규칙이 없으면 None(item으로 만들지 않음)."""
    if is_last_turn and speaker == "user":
        return "next_action"
    if _matches_any(FAILURE_PATTERNS, text):
        return "failure"
    if CURRENT_STATE_HASH_RE.search(text) and _matches_any(CURRENT_STATE_PATTERNS, text):
        return "current_state"
    if _matches_any(EVIDENCE_PATTERNS, text):
        return "evidence"
    if _matches_any(NEXT_ACTION_PATTERNS, text):
        return "next_action"
    if speaker == "assistant" and _matches_any(DECISION_PATTERNS, text):
        return "decision"
    if speaker == "user" and _matches_any(GOAL_PATTERNS, text):
        return "goal"
    if speaker == "user" and len(text.strip()) <= SHORT_USER_FALLBACK_MAX_CHARS:
        return "evidence"
    return None


# --- 2. importance 기본값(카테고리 사전, 의존 대상이면 이후 단계에서 보정) ---

BASE_IMPORTANCE = {
    "goal": 0.9,
    "decision": 0.7,
    "failure": 0.7,
    "current_state": 0.6,
    "evidence": 0.4,
    "next_action": 0.5,
}
DEPENDENT_IMPORTANCE_BONUS = 0.1

# --- 3. task_relevance: 마지막 큰 시간 간격을 기준으로 "현재 episode" 추정 ---

CURRENT_TASK_GAP_HOURS = 1.0
HIGH_TASK_RELEVANCE = 0.9
LOW_TASK_RELEVANCE = 0.2

# --- 4. dependency 연결: category별 "앞에서 찾을 대상 카테고리" 목록 ---

PREDECESSOR_CATEGORIES = {
    "current_state": ["decision", "evidence"],
    "decision": ["failure", "current_state", "goal"],
    "failure": ["decision"],
    "next_action": ["current_state"],
    "evidence": [],
    "goal": [],
}

# --- 5. retention_action 결정 임계값 ---

TASK_RELEVANCE_KEEP_THRESHOLD = 0.7
TASK_RELEVANCE_CATEGORY_KEEP_THRESHOLD = 0.4
IMPORTANCE_HIGH_THRESHOLD = 0.6
KEEP_BY_CATEGORY = {"current_state", "decision", "failure"}


@dataclass
class ExtractedItem:
    item_id: str
    category: str
    summary: str
    timestamp: str | None
    source_turn_ids: list[int]
    turn_id: int  # 정렬/의존성 탐색용 대표 turn_id(첫 source_turn_id)
    depends_on: list[str] = field(default_factory=list)
    importance: float | None = None
    task_relevance: float | None = None
    retention_action: str | None = None
    retention_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "category": self.category,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "source_turn_ids": self.source_turn_ids,
            "depends_on": self.depends_on,
            "importance": self.importance,
            "task_relevance": self.task_relevance,
            "retention_action": self.retention_action,
            "retention_reason": self.retention_reason,
        }


def _make_summary(text: str) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= SUMMARY_MAX_CHARS:
        return collapsed
    return collapsed[:SUMMARY_MAX_CHARS].rstrip() + "..."


def _find_current_episode_start(turns: list[dict[str, Any]]) -> int:
    """마지막으로 CURRENT_TASK_GAP_HOURS를 넘는 turn 간 시간 간격을 찾는다.

    그 간격 다음 turn부터 "현재 episode"로 본다. 넘는 간격이 없으면 전체를
    현재 episode로 취급한다(turn_id 0부터).
    """
    timestamps: list[datetime | None] = []
    for t in turns:
        ts = t.get("timestamp")
        try:
            timestamps.append(datetime.fromisoformat(ts) if ts else None)
        except ValueError:
            timestamps.append(None)

    boundary = 0
    for i in range(1, len(timestamps)):
        prev, cur = timestamps[i - 1], timestamps[i]
        if prev is None or cur is None:
            continue
        if cur - prev >= timedelta(hours=CURRENT_TASK_GAP_HOURS):
            boundary = i
    return boundary


def extract_context_items(session: dict[str, Any]) -> list[ExtractedItem]:
    turns = session["turns"]
    last_turn_id = turns[-1]["turn_id"] if turns else -1

    items: list[ExtractedItem] = []
    skipped_turn_ids: list[int] = []
    counter = 0

    for turn in turns:
        category = classify_turn(
            speaker=turn["speaker"],
            text=turn["text"],
            is_last_turn=(turn["turn_id"] == last_turn_id),
        )
        if category is None:
            skipped_turn_ids.append(turn["turn_id"])
            continue
        counter += 1
        items.append(
            ExtractedItem(
                item_id=f"item-{counter:04d}",
                category=category,
                summary=_make_summary(turn["text"]),
                timestamp=turn.get("timestamp"),
                source_turn_ids=[turn["turn_id"]],
                turn_id=turn["turn_id"],
            )
        )

    # task_relevance: 시간 간격 기반 episode 추정.
    episode_start_turn_id = None
    if turns:
        boundary_index = _find_current_episode_start(turns)
        episode_start_turn_id = turns[boundary_index]["turn_id"]
        for item in items:
            item.task_relevance = (
                HIGH_TASK_RELEVANCE if item.turn_id >= episode_start_turn_id else LOW_TASK_RELEVANCE
            )

    # dependency 연결: 각 item보다 앞선 item 중 허용 category의 "가장 가까운" 것을 찾는다.
    for i, item in enumerate(items):
        allowed = PREDECESSOR_CATEGORIES.get(item.category, [])
        deps: list[str] = []
        for cat in allowed:
            nearest = None
            for earlier in items[:i]:
                if earlier.category == cat:
                    nearest = earlier
            if nearest is not None:
                deps.append(nearest.item_id)
        item.depends_on = deps

    # importance: category 기본값 + 의존 대상(다른 item이 참조하는 item)이면 보너스.
    dependent_targets = {dep for item in items for dep in item.depends_on}
    for item in items:
        base = BASE_IMPORTANCE.get(item.category, 0.5)
        bonus = DEPENDENT_IMPORTANCE_BONUS if item.item_id in dependent_targets else 0.0
        item.importance = min(1.0, base + bonus)

    # retention_action 결정(규칙 기반, docs/decisions/0004 4절 근거).
    for item in items:
        has_dependents = item.item_id in dependent_targets
        _decide_retention(item, has_dependents)

    return items


def _decide_retention(item: ExtractedItem, has_dependents: bool) -> None:
    if item.task_relevance is not None and item.task_relevance >= TASK_RELEVANCE_KEEP_THRESHOLD:
        item.retention_action = "KEEP"
        item.retention_reason = (
            f"task_relevance={item.task_relevance:.1f} >= {TASK_RELEVANCE_KEEP_THRESHOLD}"
            " (현재 task 수행에 직접 필요)"
        )
        return

    if (
        item.category in KEEP_BY_CATEGORY
        and item.task_relevance is not None
        and item.task_relevance >= TASK_RELEVANCE_CATEGORY_KEEP_THRESHOLD
    ):
        item.retention_action = "KEEP"
        item.retention_reason = (
            f"category={item.category}(현재 상태/결정/실패)이고 "
            f"task_relevance={item.task_relevance:.1f} >= {TASK_RELEVANCE_CATEGORY_KEEP_THRESHOLD}"
        )
        return

    if item.importance is not None and item.importance >= IMPORTANCE_HIGH_THRESHOLD:
        if has_dependents:
            item.retention_action = "EXTERNALIZE"
            item.retention_reason = (
                f"importance={item.importance:.1f} >= {IMPORTANCE_HIGH_THRESHOLD}이고 "
                "다른 item이 참조함 — discard 불가, 현재 task relevance는 낮아 원문만 외부 보관"
            )
        else:
            item.retention_action = "COMPRESS"
            item.retention_reason = (
                f"importance={item.importance:.1f} >= {IMPORTANCE_HIGH_THRESHOLD}이지만 "
                "참조하는 item 없음 — 원문 보존 불필요, 의미만 압축 보존"
            )
        return

    if has_dependents:
        item.retention_action = "EXTERNALIZE"
        item.retention_reason = "importance/task_relevance는 낮지만 다른 item의 dependency — discard 불가"
        return

    item.retention_action = "DISCARD"
    item.retention_reason = "task_relevance 낮음, importance 낮음, dependency 대상 아님"


def build_analysis(session: dict[str, Any]) -> dict[str, Any]:
    items = extract_context_items(session)
    current_task = None
    current_episode_items = [i for i in items if i.task_relevance == HIGH_TASK_RELEVANCE]
    if current_episode_items:
        current_task = current_episode_items[0].summary

    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": session.get("session_id"),
        "current_task": current_task,
        "items": [item.to_dict() for item in items],
    }
