"""Pipeline stages. Each step moves one video forward exactly one status."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from . import render as render_mod
from .db import Store
from .srt import build_srt

# Statuses the automatic pipeline stops at (humans/exporters take over from here).
STOP = {"pending_review", "approved", "scheduled", "published", "rejected"}


class Pipeline:
    def __init__(self, store: Store, cfg: dict, providers: SimpleNamespace):
        self.store, self.cfg, self.p = store, cfg, providers
        self.data_dir = Path(cfg["general"]["data_dir"])
        self.steps = {
            "idea": self._script,
            "scripted": self._check,
            "checked": self._voice,
            "voiced": self._visuals,
            "visualized": self._render,
            "rendered": self._to_review,
        }

    def _dir(self, v: dict) -> Path:
        d = self.data_dir / "videos" / f"{v['id']:05d}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # --- steps ---------------------------------------------------------------

    def _script(self, v: dict) -> str:
        script = self.p.script.write(topic=v["topic"], pillar=v["pillar"], kind=v["kind"], lang=v["lang"])
        self.store.update(v["id"], script=script)
        return "scripted"

    def _check(self, v: dict) -> str:
        result = self.p.factcheck.check(script=v["script"], lang=v["lang"])
        script = dict(v["script"], fact_check=result)
        self.store.update(v["id"], script=script)
        return "checked"

    def _voice(self, v: dict) -> str:
        d = self._dir(v)
        audio, durations = [], []
        for i, scene in enumerate(v["script"]["scenes"]):
            path = d / f"scene{i:02d}.wav"
            durations.append(self.p.tts.synthesize(text=scene["narration"], out_path=path, lang=v["lang"]))
            audio.append(str(path))
        self.store.update(v["id"], assets={"audio": audio, "durations": durations})
        return "voiced"

    def _visuals(self, v: dict) -> str:
        d = self._dir(v)
        r = self.cfg["render"]
        size = r["short_size"] if v["kind"] == "short" else r["long_size"]
        clips = []
        for i, (scene, dur) in enumerate(zip(v["script"]["scenes"], v["assets"]["durations"])):
            path = d / f"scene{i:02d}.mp4"
            self.p.visuals.make(
                prompt=scene["visual_prompt"], out_path=path, duration=dur, size=size, fps=r["fps"], index=i
            )
            clips.append(str(path))
        self.store.update(v["id"], assets=dict(v["assets"], video=clips))
        return "visualized"

    def _render(self, v: dict) -> str:
        d = self._dir(v)
        a = v["assets"]
        scenes = [(s["narration"], dur) for s, dur in zip(v["script"]["scenes"], a["durations"])]
        srt_path = d / "final.srt"
        srt_path.write_text(build_srt(scenes), encoding="utf-8")
        final = d / "final.mp4"
        render_mod.render(
            video_clips=a["video"],
            audio_clips=a["audio"],
            out_path=final,
            srt_path=srt_path,
            burn_subtitles=self.cfg["render"]["burn_subtitles"],
        )
        self.store.update(v["id"], assets=dict(a, final=str(final), srt=str(srt_path)))
        return "rendered"

    def _to_review(self, v: dict) -> str:
        return "pending_review"

    # --- driver --------------------------------------------------------------

    def advance(self, video_id: int) -> str:
        """Run steps until the video reaches a stop status. Errors are stored, not raised."""
        while True:
            v = self.store.get(video_id)
            if v["status"] in STOP or v["error"]:
                return v["status"]
            try:
                new_status = self.steps[v["status"]](v)
            except Exception as exc:  # noqa: BLE001 - surface any provider failure on the row
                self.store.update(video_id, error=f"{v['status']}: {type(exc).__name__}: {exc}")
                return v["status"]
            self.store.update(video_id, status=new_status)

    def run(self, limit: int | None = None, retry: bool = False) -> dict[str, str]:
        """Advance all in-progress videos, earliest publish time first."""
        out: dict[int, str] = {}
        todo = [v for v in self.store.list() if v["status"] not in STOP]
        for v in todo[:limit]:
            if retry and v["error"]:
                self.store.update(v["id"], error=None)
            out[v["id"]] = self.advance(v["id"])
        return out
