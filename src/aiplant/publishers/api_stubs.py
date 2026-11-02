"""Phase-3 publishers that call official APIs. Not implemented yet - see docs/PLAN.md section 3.3.

Prerequisites before implementing:
- YouTube: Google Cloud project + OAuth + API compliance audit (otherwise uploads are forced private).
- Facebook/Instagram/Threads: Meta app, Page linked to an IG professional account, app review.
"""
from __future__ import annotations


class _NotReady:
    name = "stub"

    def publish(self, video: dict, *, platforms: list[str]) -> str | None:
        raise NotImplementedError(f"{self.name} API publisher is not implemented yet; use the export publisher")


class YouTubePublisher(_NotReady):
    name = "youtube"


class MetaPublisher(_NotReady):
    name = "meta"


class ThreadsPublisher(_NotReady):
    name = "threads"
