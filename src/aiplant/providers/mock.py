"""Offline placeholder providers so the whole pipeline runs without API keys."""
from __future__ import annotations

import math
import shutil
import subprocess
import wave
from pathlib import Path

PALETTE = ["0x2e7d32", "0x558b2f", "0x1b5e20", "0x33691e", "0x00695c", "0x4e342e"]


def speech_seconds(text: str, lang: str) -> float:
    """Rough narration length: ~4.5 chars/s for Chinese, ~2.5 words/s otherwise."""
    if lang.lower().startswith(("zh", "ja")):
        return max(1.5, len(text) / 4.5)
    return max(1.5, len(text.split()) / 2.5)


class MockScriptWriter:
    def write(self, *, topic: str, pillar: str, kind: str, lang: str) -> dict:
        n = 3 if kind == "short" else 8
        scenes = [
            {
                "narration": f"[MOCK] 關於「{topic}」的第 {i + 1} 段旁白。這是佔位文字。",
                "visual_prompt": f"macro footage of plants, scene {i + 1}: {topic}",
            }
            for i in range(n)
        ]
        return {
            "title": f"[MOCK] {topic}",
            "hook": f"你知道嗎？{topic}",
            "description": f"[MOCK] {topic}\n\n參考資料：（待補）",
            "tags": ["植物", "自然", pillar],
            "scenes": scenes,
            "sources": [],
        }


class MockFactChecker:
    def check(self, *, script: dict, lang: str) -> dict:
        return {"ok": True, "flags": ["[MOCK] 未實際查核，正式使用請改用 claude 查核器並人工確認"]}


class MockTTS:
    RATE = 16000

    def synthesize(self, *, text: str, out_path: Path, lang: str) -> float:
        dur = speech_seconds(text, lang)
        frames = int(math.ceil(dur * self.RATE))
        with wave.open(str(out_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.RATE)
            w.writeframes(b"\x00\x00" * frames)
        return frames / self.RATE


class MockVisuals:
    def make(self, *, prompt: str, out_path: Path, duration: float, size: str, fps: int, index: int) -> None:
        if shutil.which("ffmpeg") is None:
            out_path.write_bytes(b"")  # placeholder; render step will report ffmpeg missing
            return
        color = PALETTE[index % len(PALETTE)]
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", f"color=c={color}:s={size}:r={fps}:d={duration:.3f}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_path),
            ],
            check=True,
        )
