#!/usr/bin/env python3
"""Тесты seed_due.py: отбор посева на замороженном посеве.
Запуск: python3 tools/test_seed_due.py"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import seed_due as sd  # noqa: E402

SEED = HERE / "fixtures" / "seed_macro.json"   # замороженный посев, не живые данные
PASSED, FAILED = [], []


def case(name):
    def deco(fn):
        try:
            fn()
            PASSED.append(name)
        except Exception as e:  # noqa: BLE001
            FAILED.append(name)
            print("FAIL %s: %s: %s" % (name, type(e).__name__, e))
        return fn
    return deco


MACRO = json.loads(SEED.read_text("utf-8"))


@case("cap-and-order-report-segments-first")
def _():
    pick, rest = sd.due(MACRO)
    assert len(pick) == sd.CAP, len(pick)
    segs = [x["segment"] for x in pick]
    assert segs[0] == "dkp" and segs == sorted(segs, key=sd.SEGMENT_ORDER.index), segs
    assert any("over cap" in x["reason"] for x in rest)


@case("deterministic")
def _():
    assert [x["id"] for x in sd.due(MACRO)[0]] == [x["id"] for x in sd.due(json.loads(SEED.read_text("utf-8")))[0]]


@case("negative-never-picked")
def _():
    pick, rest = sd.due(MACRO, cap=1000)
    neg = {x["topic"] for x in rest if x["reason"] == "negative value"}
    assert {"tor_oez_spik_no_data", "factoring_leasing_no_data"} <= neg, neg
    assert not neg & {x["topic"] for x in pick}


@case("verified-fact-is-not-seed")
def _():
    m = json.loads(SEED.read_text("utf-8"))
    f = m["segments"]["dkp"][0]
    f["harvested"] = "2026-10-23"
    pick, rest = sd.due(m, cap=1000)
    assert f["id"] not in {x["id"] for x in pick + rest}


@case("queued-and-tried-skipped")
def _():
    first = sd.due(MACRO)[0]
    a, b = first[0]["id"], first[1]["id"]
    pick, rest = sd.due(MACRO, queued={a}, tried={b})
    ids = {x["id"] for x in pick}
    assert a not in ids and b not in ids and len(pick) == sd.CAP
    why = {x["id"]: x["reason"] for x in rest}
    assert why[a] == "already in stale_queue" and why[b].startswith("tried before"), why


@case("tried-ids-from-pending-files")
def _():
    with tempfile.TemporaryDirectory() as td:
        w = Path(td, "2026-W44")
        w.mkdir()
        (w / "pending.json").write_text(json.dumps({"segments": {"byudzhet": [
            {"topic": "federal_budget_2026", "replaces": ["1f44440c"]},
            {"topic": "x", "replaces": "abcd1234"}]}, "reg_calendar": [{"name": "r"}]}), "utf-8")
        Path(td, "2026-W45").mkdir()   # прогон без pending
        assert sd.tried_ids(Path(td)) == {"1f44440c", "abcd1234"}


@case("cli-text-and-json")
def _():
    import contextlib
    import io
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        sd.main(["--macro", str(SEED), "--runs-dir", "/nonexistent"])
    assert out.getvalue().startswith("SEED_DUE due=20 "), out.getvalue()[:80]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        sd.main(["--macro", str(SEED), "--runs-dir", "/nonexistent", "--json", "--cap", "3"])
    assert len(json.loads(out.getvalue())["due"]) == 3


print("%d passed, %d failed" % (len(PASSED), len(FAILED)))
sys.exit(1 if FAILED else 0)
