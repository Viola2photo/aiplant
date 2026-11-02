"""Content calendar: turn cadence settings + a topic bank into dated video slots."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .db import Store

PILLARS = ["growth", "odd", "symbiosis", "local", "myth"]


def load_topics(path: str | Path) -> list[tuple[str, str]]:
    """Read `pillar|topic` lines; blank lines and # comments are ignored."""
    topics: list[tuple[str, str]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pillar, _, topic = line.partition("|")
        if pillar.strip() in PILLARS and topic.strip():
            topics.append((pillar.strip(), topic.strip()))
    return topics


def _pick(bank: list[tuple[str, str]], want: str) -> tuple[str, str] | None:
    """Prefer the wanted pillar so content mixes; fall back to any remaining topic."""
    for item in bank:
        if item[0] == want:
            bank.remove(item)
            return item
    return bank.pop(0) if bank else None


def plan(store: Store, cfg: dict, topics: list[tuple[str, str]], start: date, days: int) -> dict:
    """Create video slots for `days` days from `start`. Idempotent per (kind, publish_at).

    Returns {"created": n, "skipped": n, "missing_topics": n}.
    """
    cad = cfg["cadence"]
    tz = ZoneInfo(cfg["general"]["timezone"])
    lang = cfg["general"]["channel_lang"]
    anchor = date.fromisoformat(cad["anchor_date"]) if cad["anchor_date"] else start

    used = store.used_topics()
    bank = [t for t in topics if t[1] not in used]
    result = {"created": 0, "skipped": 0, "missing_topics": 0}
    rotation = len(store.list())  # keeps pillar rotation going across plan runs

    def make(kind: str, day: date, hhmm: str) -> None:
        nonlocal rotation
        hour, minute = (int(x) for x in hhmm.split(":"))
        when = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz).isoformat()
        picked = _pick(bank, PILLARS[rotation % len(PILLARS)])
        if picked is None:
            result["missing_topics"] += 1
            return
        vid = store.add(kind=kind, lang=lang, pillar=picked[0], topic=picked[1], publish_at=when)
        if vid is None:
            bank.insert(0, picked)  # slot exists already: give the topic back
            result["skipped"] += 1
        else:
            rotation += 1
            result["created"] += 1

    for offset in range(days):
        day = start + timedelta(days=offset)
        for hhmm in cad["short_times"][: cad["shorts_per_day"]]:
            make("short", day, hhmm)
        if (day - anchor).days % cad["long_every_days"] == 0 and day >= anchor:
            make("long", day, cad["long_time"])
    return result
