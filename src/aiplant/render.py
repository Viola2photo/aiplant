"""Assemble scene clips + narration into the final mp4 with ffmpeg."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _concat_list(paths: list[str], list_path: Path) -> None:
    list_path.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in paths), encoding="utf-8")


def render(
    *, video_clips: list[str], audio_clips: list[str], out_path: Path, srt_path: Path | None, burn_subtitles: bool
) -> None:
    if not have_ffmpeg():
        raise RuntimeError("ffmpeg not found on PATH; install it to render videos")
    work = out_path.parent
    vlist, alist = work / "video.txt", work / "audio.txt"
    _concat_list(video_clips, vlist)
    _concat_list(audio_clips, alist)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", vlist.name,
        "-f", "concat", "-safe", "0", "-i", alist.name,
    ]
    if burn_subtitles and srt_path is not None:
        # Needs an ffmpeg build with libass. Paths with ':' or quotes would need escaping.
        cmd += ["-vf", f"subtitles={srt_path.name}"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out_path.name)]
    subprocess.run(cmd, check=True, cwd=work)
