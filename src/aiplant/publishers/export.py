"""Phase-1 publisher: write an upload-ready folder per video for third-party schedulers
(Buffer / Metricool / Publer) or manual upload via YouTube Studio / Meta Business Suite."""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


class ExportPublisher:
    name = "export"

    def __init__(self, out_dir: str | Path):
        self.out_dir = Path(out_dir)

    def publish(self, video: dict, *, platforms: list[str]) -> str | None:
        script, assets = video["script"], video["assets"]
        day = video["publish_at"][:10]
        pkg = self.out_dir / f"{day}_{video['kind']}_{video['id']:05d}"
        pkg.mkdir(parents=True, exist_ok=True)
        shutil.copy2(assets["final"], pkg / "video.mp4")
        shutil.copy2(assets["srt"], pkg / "captions.srt")
        meta = {
            "id": video["id"],
            "kind": video["kind"],
            "lang": video["lang"],
            "publish_at": video["publish_at"],
            "platforms": platforms,
            "title": script["title"],
            "description": script["description"],
            "tags": script["tags"],
            "hook": script.get("hook", ""),  # use as the Threads post text
            "sources": script.get("sources", []),
            "ai_disclosure": True,  # tick the "altered or synthetic content" box on YouTube
        }
        (pkg / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        self._append_schedule(meta, pkg)
        return str(pkg)

    def _append_schedule(self, meta: dict, pkg: Path) -> None:
        path = self.out_dir / "schedule.csv"
        new = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["publish_at", "id", "kind", "platforms", "title", "folder"])
            w.writerow([meta["publish_at"], meta["id"], meta["kind"], "+".join(meta["platforms"]), meta["title"], pkg.name])
