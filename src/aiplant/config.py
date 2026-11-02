"""Configuration: built-in defaults deep-merged with an optional TOML file."""
from __future__ import annotations

import copy
import tomllib
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "general": {
        "channel_lang": "zh-TW",
        "timezone": "Asia/Taipei",
        "data_dir": "data",
        "out_dir": "out",
    },
    "cadence": {
        "shorts_per_day": 1,
        "short_times": ["12:00", "18:00", "21:00"],
        "long_every_days": 3,
        "long_time": "19:30",
        "anchor_date": "",
    },
    "platforms": {
        "short": ["youtube", "facebook", "instagram", "threads"],
        "long": ["youtube", "facebook"],
    },
    "providers": {"script": "mock", "factcheck": "mock", "tts": "mock", "visuals": "mock"},
    "claude": {"model": "claude-sonnet-5-5", "max_tokens": 4096},
    "render": {
        "short_size": "1080x1920",
        "long_size": "1920x1080",
        "fps": 24,
        "burn_subtitles": False,
    },
}


def _merge(base: dict, extra: dict) -> dict:
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load(path: str | Path | None = None) -> dict[str, Any]:
    cfg = copy.deepcopy(DEFAULTS)
    if path is None and Path("config.toml").exists():
        path = "config.toml"
    if path is not None:
        with open(path, "rb") as fh:
            _merge(cfg, tomllib.load(fh))
    return cfg
