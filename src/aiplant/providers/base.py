"""Provider interfaces. Swap implementations via [providers] in config."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

# Script shape produced by ScriptWriter:
# {
#   "title": str, "hook": str, "description": str, "tags": [str],
#   "scenes": [{"narration": str, "visual_prompt": str}],
#   "sources": [str]            # references backing the factual claims
# }
Script = dict


class ScriptWriter(Protocol):
    def write(self, *, topic: str, pillar: str, kind: str, lang: str) -> Script: ...


class FactChecker(Protocol):
    def check(self, *, script: Script, lang: str) -> dict:
        """Return {"ok": bool, "flags": [str]} - flags are claims a human should verify."""


class TTS(Protocol):
    def synthesize(self, *, text: str, out_path: Path, lang: str) -> float:
        """Write narration audio (wav) to out_path and return its duration in seconds."""


class VisualProvider(Protocol):
    def make(self, *, prompt: str, out_path: Path, duration: float, size: str, fps: int, index: int) -> None:
        """Write a silent video clip of `duration` seconds at `size` (WxH) to out_path."""
