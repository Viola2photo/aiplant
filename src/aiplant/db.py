"""SQLite state store. One row per video; `status` drives the pipeline state machine."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Order matters: the pipeline advances a video one step at a time along this list.
STATUSES = [
    "idea",          # topic + slot chosen
    "scripted",      # script written
    "checked",       # fact-check done (flags attached)
    "voiced",        # narration audio per scene
    "visualized",    # visual clip per scene
    "rendered",      # final mp4 + srt built
    "pending_review",  # waiting for human approval
    "approved",
    "scheduled",     # exported / handed to a scheduler
    "published",
    "rejected",
]

JSON_FIELDS = ("script", "assets")

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,              -- short | long
    lang TEXT NOT NULL,
    pillar TEXT NOT NULL,
    topic TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'idea',
    publish_at TEXT NOT NULL,        -- ISO 8601 with offset
    script TEXT,                     -- JSON
    assets TEXT,                     -- JSON: scene audio/video paths, final paths
    published_url TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (kind, publish_at)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        d = dict(row)
        for f in JSON_FIELDS:
            d[f] = json.loads(d[f]) if d[f] else None
        return d

    def add(self, *, kind: str, lang: str, pillar: str, topic: str, publish_at: str) -> int | None:
        """Insert a video slot. Returns None if the slot already exists (idempotent planning)."""
        now = _now()
        try:
            cur = self.conn.execute(
                "INSERT INTO videos (kind, lang, pillar, topic, publish_at, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (kind, lang, pillar, topic, publish_at, now, now),
            )
        except sqlite3.IntegrityError:
            return None
        self.conn.commit()
        return cur.lastrowid

    def get(self, video_id: int) -> dict[str, Any] | None:
        return self._row(self.conn.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone())

    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM videos WHERE status=? ORDER BY publish_at", (status,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM videos ORDER BY publish_at").fetchall()
        return [self._row(r) for r in rows]

    def update(self, video_id: int, **fields: Any) -> None:
        for f in JSON_FIELDS:
            if f in fields and fields[f] is not None:
                fields[f] = json.dumps(fields[f], ensure_ascii=False)
        fields["updated_at"] = _now()
        cols = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(f"UPDATE videos SET {cols} WHERE id=?", (*fields.values(), video_id))
        self.conn.commit()

    def used_topics(self) -> set[str]:
        return {r["topic"] for r in self.conn.execute("SELECT topic FROM videos")}

    def counts(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT status, COUNT(*) c FROM videos GROUP BY status").fetchall()
        return {r["status"]: r["c"] for r in rows}
