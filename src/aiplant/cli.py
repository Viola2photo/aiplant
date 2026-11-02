"""Command line interface: `aiplant <command>` (or `python -m aiplant`)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import config as config_mod
from .db import Store
from .pipeline import Pipeline
from .planner import load_topics, plan
from .providers import build
from .publishers.export import ExportPublisher


def _store(cfg: dict) -> Store:
    return Store(Path(cfg["general"]["data_dir"]) / "aiplant.db")


def cmd_plan(args, cfg) -> int:
    store = _store(cfg)
    start = date.fromisoformat(args.start) if args.start else date.today()
    res = plan(store, cfg, load_topics(args.topics), start, args.days)
    print(f"created={res['created']} skipped(existing)={res['skipped']} missing_topics={res['missing_topics']}")
    if res["missing_topics"]:
        print(f"Topic bank ran out: add {res['missing_topics']} more lines to {args.topics}")
    return 0


def cmd_run(args, cfg) -> int:
    store = _store(cfg)
    results = Pipeline(store, cfg, build(cfg)).run(limit=args.limit, retry=args.retry)
    for vid, status in results.items():
        err = store.get(vid)["error"]
        print(f"#{vid}: {status}" + (f"  ERROR {err}" if err else ""))
    if not results:
        print("nothing to do")
    return 0


def cmd_list(args, cfg) -> int:
    for v in _store(cfg).list(args.status):
        flag = " !" if v["error"] else ""
        print(f"#{v['id']:<4} {v['publish_at'][:16]} {v['kind']:<5} {v['status']:<15} {v['pillar']:<9} {v['topic']}{flag}")
    return 0


def cmd_show(args, cfg) -> int:
    v = _store(cfg).get(args.id)
    if v is None:
        print("no such video")
        return 1
    print(json.dumps(v, ensure_ascii=False, indent=2))
    return 0


def _review(args, cfg, new_status: str) -> int:
    store = _store(cfg)
    v = store.get(args.id)
    if v is None or v["status"] != "pending_review":
        print("video not found or not pending_review")
        return 1
    store.update(args.id, status=new_status)
    print(f"#{args.id} -> {new_status}")
    return 0


def cmd_export(args, cfg) -> int:
    store = _store(cfg)
    pub = ExportPublisher(cfg["general"]["out_dir"])
    n = 0
    for v in store.list("approved"):
        folder = pub.publish(v, platforms=cfg["platforms"][v["kind"]])
        store.update(v["id"], status="scheduled")
        print(f"#{v['id']} exported -> {folder}")
        n += 1
    print(f"{n} exported")
    return 0


def cmd_mark_published(args, cfg) -> int:
    store = _store(cfg)
    if store.get(args.id) is None:
        print("no such video")
        return 1
    store.update(args.id, status="published", published_url=args.url)
    return 0


def cmd_status(args, cfg) -> int:
    for status, n in _store(cfg).counts().items():
        print(f"{status:<15} {n}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aiplant")
    ap.add_argument("--config", help="path to config TOML (default: ./config.toml if present)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="create dated video slots from the topic bank")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--start", help="YYYY-MM-DD (default today)")
    p.add_argument("--topics", default="topics.txt")
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser("run", help="advance in-progress videos up to human review")
    p.add_argument("--limit", type=int)
    p.add_argument("--retry", action="store_true", help="clear errors and retry failed videos")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("list", help="list videos")
    p.add_argument("--status")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("show", help="show one video in full")
    p.add_argument("id", type=int)
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("approve", help="approve a video pending review")
    p.add_argument("id", type=int)
    p.set_defaults(fn=lambda a, c: _review(a, c, "approved"))

    p = sub.add_parser("reject", help="reject a video pending review")
    p.add_argument("id", type=int)
    p.set_defaults(fn=lambda a, c: _review(a, c, "rejected"))

    p = sub.add_parser("export", help="write upload-ready folders for approved videos")
    p.set_defaults(fn=cmd_export)

    p = sub.add_parser("mark-published", help="record that a video was uploaded")
    p.add_argument("id", type=int)
    p.add_argument("--url", default="")
    p.set_defaults(fn=cmd_mark_published)

    p = sub.add_parser("status", help="count videos per status")
    p.set_defaults(fn=cmd_status)

    args = ap.parse_args(argv)
    return args.fn(args, config_mod.load(args.config))


if __name__ == "__main__":
    sys.exit(main())
