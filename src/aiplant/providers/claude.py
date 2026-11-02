"""Claude-backed script writer and fact-checker (requires `pip install aiplant[claude]` + ANTHROPIC_API_KEY)."""
from __future__ import annotations

import json
import re

PILLAR_GUIDE = {
    "growth": "plant growth time-lapse: germination, flowering, climbing, rapid growth",
    "odd": "unusual plants: carnivorous, parasitic, mimicry, plants that move",
    "symbiosis": "forest ecology: mycorrhizal networks, pollination, seed dispersal, chemical signaling",
    "local": "native Taiwanese plants and seasonal phenomena",
    "myth": "common plant myths, answered accurately",
}

LANG_NAME = {"zh-TW": "Traditional Chinese (Taiwan usage)", "en": "English"}

SCRIPT_RULES = """You write narration scripts for a nature-education video channel about plants.
Rules:
- Only state facts you are confident are true. Never invent species names, numbers, or studies.
- If a figure is uncertain, phrase it as approximate or leave it out.
- List real, checkable references in "sources" (e.g. Wikipedia article titles, journal names, government agencies).
- Open with a hook in the first sentence. Calm, curious, accurate tone. No clickbait claims.
- Each scene: one narration paragraph plus a concrete visual_prompt describing footage to show.
Return ONLY a JSON object: {"title","hook","description","tags":[],"scenes":[{"narration","visual_prompt"}],"sources":[]}."""

CHECK_RULES = """You are a plant-science fact checker. Read the script and list every factual claim that is
wrong, unverifiable, overstated, or lacks a source. Return ONLY JSON: {"ok": bool, "flags": [string]}.
ok is true only if flags is empty."""


def _client():
    try:
        import anthropic  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install the Claude extra: pip install -e '.[claude]'") from exc
    return anthropic.Anthropic()


def _json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in model output: {text[:200]!r}")
    return json.loads(match.group(0))


class ClaudeScriptWriter:
    def __init__(self, model: str, max_tokens: int):
        self.model, self.max_tokens, self.client = model, max_tokens, _client()

    def write(self, *, topic: str, pillar: str, kind: str, lang: str) -> dict:
        scenes = "3-4 scenes, 25-45 seconds when read aloud" if kind == "short" else "8-12 scenes, 8-12 minutes when read aloud"
        prompt = (
            f"Topic: {topic}\nPillar: {PILLAR_GUIDE.get(pillar, pillar)}\n"
            f"Format: {kind} video, {scenes}.\nLanguage: {LANG_NAME.get(lang, lang)}."
        )
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SCRIPT_RULES,
            messages=[{"role": "user", "content": prompt}],
        )
        script = _json(msg.content[0].text)
        if not script.get("scenes"):
            raise ValueError("Model returned a script with no scenes")
        return script


class ClaudeFactChecker:
    def __init__(self, model: str, max_tokens: int):
        self.model, self.max_tokens, self.client = model, max_tokens, _client()

    def check(self, *, script: dict, lang: str) -> dict:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=CHECK_RULES,
            messages=[{"role": "user", "content": json.dumps(script, ensure_ascii=False)}],
        )
        result = _json(msg.content[0].text)
        return {"ok": bool(result.get("ok")), "flags": list(result.get("flags", []))}
