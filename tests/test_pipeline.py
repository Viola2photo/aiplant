import shutil
from datetime import date

import pytest

from aiplant import config as config_mod
from aiplant.db import Store
from aiplant.pipeline import Pipeline
from aiplant.planner import load_topics, plan
from aiplant.providers import build
from aiplant.publishers.export import ExportPublisher
from aiplant.srt import build_srt


@pytest.fixture
def cfg(tmp_path):
    c = config_mod.load()
    c["general"]["data_dir"] = str(tmp_path / "data")
    c["general"]["out_dir"] = str(tmp_path / "out")
    c["render"]["short_size"] = "270x480"
    c["render"]["long_size"] = "480x270"
    return c


@pytest.fixture
def topics():
    return load_topics("topics.txt")


def test_topic_bank_loads(topics):
    assert len(topics) >= 20
    assert {p for p, _ in topics} == {"growth", "odd", "symbiosis", "local", "myth"}


def test_plan_cadence(cfg, topics, tmp_path):
    cfg["cadence"]["shorts_per_day"] = 2
    store = Store(tmp_path / "t.db")
    res = plan(store, cfg, topics, date(2026, 11, 2), 7)
    vids = store.list()
    assert res["missing_topics"] == 0
    assert sum(v["kind"] == "short" for v in vids) == 14
    assert sum(v["kind"] == "long" for v in vids) == 3  # days 0, 3, 6
    assert len({v["topic"] for v in vids}) == len(vids)  # no repeated topics


def test_plan_is_idempotent(cfg, topics, tmp_path):
    store = Store(tmp_path / "t.db")
    plan(store, cfg, topics, date(2026, 11, 2), 3)
    again = plan(store, cfg, topics, date(2026, 11, 2), 3)
    assert again["created"] == 0 and again["skipped"] > 0
    assert len(store.list()) == 4  # 3 shorts + 1 long


def test_plan_reports_missing_topics(cfg, tmp_path):
    store = Store(tmp_path / "t.db")
    res = plan(store, cfg, [("growth", "only one")], date(2026, 11, 2), 3)
    assert res["created"] == 1 and res["missing_topics"] > 0


def test_srt_timing():
    srt = build_srt([("第一句。第二句。", 4.0)])
    assert "00:00:00,000 --> 00:00:02,000" in srt
    assert "00:00:02,000 --> 00:00:04,000" in srt


def test_error_is_recorded_and_retry_works(cfg, topics, tmp_path):
    store = Store(tmp_path / "t.db")
    plan(store, cfg, topics, date(2026, 11, 2), 1)
    prov = build(cfg)

    def boom(**_):
        raise RuntimeError("api down")

    prov.script.write = boom
    pipe = Pipeline(store, cfg, prov)
    pipe.run()
    v = store.list()[0]
    assert v["status"] == "idea" and "api down" in v["error"]

    pipe.p = build(cfg)
    pipe.run(retry=True)
    assert store.get(v["id"])["error"] is None
    assert store.get(v["id"])["status"] != "idea"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_end_to_end_to_export(cfg, topics, tmp_path):
    store = Store(tmp_path / "t.db")
    plan(store, cfg, topics, date(2026, 11, 2), 1)  # 1 short + 1 long
    pipe = Pipeline(store, cfg, build(cfg))
    pipe.run()
    vids = store.list()
    assert [v["status"] for v in vids] == ["pending_review"] * 2
    assert all(v["error"] is None for v in vids)
    assert all(v["script"]["fact_check"]["flags"] for v in vids)

    v = vids[0]
    store.update(v["id"], status="approved")
    folder = ExportPublisher(cfg["general"]["out_dir"]).publish(
        store.get(v["id"]), platforms=cfg["platforms"][v["kind"]]
    )
    from pathlib import Path

    assert (Path(folder) / "video.mp4").stat().st_size > 0
    assert (Path(folder) / "metadata.json").exists()
    assert (Path(cfg["general"]["out_dir"]) / "schedule.csv").exists()
