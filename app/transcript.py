"""Junta picados de transcrição em falas legíveis."""

from datetime import datetime


def group_turns(items: list[dict], gap_seconds: float = 18, max_chars: int = 520) -> list[dict]:
    blocks: list[dict] = []
    buf: dict | None = None
    for item in items:
        text = " ".join(str(item.get("text") or "").split())
        if len(text) < 2:
            continue
        created = item.get("created_at")
        if buf is None:
            buf = _fresh(item, text, created)
            continue
        gap = _gap(buf.get("ended_at"), created)
        if gap > gap_seconds or len(buf["text"]) >= max_chars:
            blocks.append(buf)
            buf = _fresh(item, text, created)
            continue
        buf["text"] = f"{buf['text']} {text}"
        buf["ended_at"] = created or buf["ended_at"]
        buf["parts"] += 1
    if buf:
        blocks.append(buf)
    return blocks


def _fresh(item: dict, text: str, created) -> dict:
    return {
        "id": item.get("id"),
        "text": text,
        "created_at": created,
        "ended_at": created,
        "parts": 1,
    }


def _gap(previous, current) -> float:
    if not isinstance(previous, datetime) or not isinstance(current, datetime):
        return 0
    return abs((current - previous).total_seconds())
