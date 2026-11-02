"""Provider factory driven by the [providers] config section."""
from __future__ import annotations

from types import SimpleNamespace

from . import mock


def build(cfg: dict) -> SimpleNamespace:
    p, c = cfg["providers"], cfg["claude"]

    if p["script"] == "mock":
        script = mock.MockScriptWriter()
    elif p["script"] == "claude":
        from .claude import ClaudeScriptWriter

        script = ClaudeScriptWriter(c["model"], c["max_tokens"])
    else:
        raise ValueError(f"Unknown script provider: {p['script']}")

    if p["factcheck"] == "mock":
        factcheck = mock.MockFactChecker()
    elif p["factcheck"] == "claude":
        from .claude import ClaudeFactChecker

        factcheck = ClaudeFactChecker(c["model"], c["max_tokens"])
    else:
        raise ValueError(f"Unknown factcheck provider: {p['factcheck']}")

    if p["tts"] == "mock":
        tts = mock.MockTTS()
    else:
        raise NotImplementedError(
            f"TTS provider '{p['tts']}' not implemented yet. Add a class with "
            "synthesize(text, out_path, lang) in providers/ and register it here."
        )

    if p["visuals"] == "mock":
        visuals = mock.MockVisuals()
    else:
        raise NotImplementedError(
            f"Visuals provider '{p['visuals']}' not implemented yet. Add a class with "
            "make(prompt, out_path, duration, size, fps, index) in providers/ and register it here."
        )

    return SimpleNamespace(script=script, factcheck=factcheck, tts=tts, visuals=visuals)
