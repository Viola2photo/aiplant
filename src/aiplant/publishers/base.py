"""Publisher interface. `publish` hands a finished video to a platform / scheduler."""
from __future__ import annotations

from typing import Protocol


class Publisher(Protocol):
    name: str

    def publish(self, video: dict, *, platforms: list[str]) -> str | None:
        """Publish or schedule the video. Return a URL/identifier if known, else None."""
