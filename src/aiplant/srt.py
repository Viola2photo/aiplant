"""Subtitle generation from scene narration + known audio durations (no ASR needed)."""
from __future__ import annotations

import re

_SPLIT = re.compile(r"(?<=[。！？!?；;.])\s*")


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def build_srt(scenes: list[tuple[str, float]]) -> str:
    """scenes: [(narration, duration_seconds)]. Time is split across sentences by length."""
    cues: list[str] = []
    t = 0.0
    n = 1
    for text, dur in scenes:
        parts = [p for p in _SPLIT.split(text.strip()) if p] or [text]
        total = sum(len(p) for p in parts) or 1
        for p in parts:
            span = dur * len(p) / total
            cues.append(f"{n}\n{_ts(t)} --> {_ts(t + span)}\n{p}\n")
            t += span
            n += 1
    return "\n".join(cues)
