#!/usr/bin/env python3
"""Тесты macro_merge.py и fuses.py на НАСТОЯЩЕМ посеве macro/macro.json.
Запуск: python3 tools/test_macro_merge.py"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import fuses  # noqa: E402
import industry_cache as ic  # noqa: E402

SEED = ROOT / "macro" / "macro.json"
PASSED, FAILED = [], []
REAL_GATE = ic._macro_duplicate


def case(name):
    def deco(fn):
        ic._macro_duplicate = REAL_GATE          # каждый тест с боевым гейтом
        try:
            fn()
            PASSED.append(name)
        except Exception as e:  # noqa: BLE001
            FAILED.append(name)
            print("FAIL %s: %s: %s" % (name, type(e).__name__, e))
        finally:
            ic._macro_duplicate = REAL_GATE
        return fn
    return deco


def seed_fact(topic):
    art = json.loads(SEED.read_text("utf-8"))
    for seg, _, f in ic.iter_facts(art):
        if f.get("topic") == topic:
            return seg, dict(f)
    raise KeyError(topic)


def workdir():
    td = Path(tempfile.mkdtemp())
    shutil.copy(SEED, td / "macro.json")
    return td


def merge(td, payload, now="2026-09-26"):
    p = td / "payload.json"
    p.write_text(json.dumps(payload, ensure_ascii=False), "utf-8")
    import macro_merge
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = macro_merge.main(["--verified", str(p), "--macro-dir", str(td), "--now", now])
    return rc, buf.getvalue()


def stats(out):
    m = re.search(r"MERGE_STATS (.*)", out)
    return dict(kv.split("=") for kv in m.group(1).split() if "=" in kv) if m else {}


@case("sentinel-combat-gate-still-rejects-macro-facts")
def _():
    # Если упало — боевой модуль сам перестал бить по macro.md: обёртку можно снять.
    for topic in ("vat_rate", "contribution_base_2026"):
        seg, f = seed_fact(topic)
        why = ic._validate_fact(dict(f, segment=seg))
        assert why and why.startswith("макро-дубль"), (topic, why)


@case("wrapper-admits-whole-seed")
def _():
    import macro_merge
    macro_merge.disable_macro_gate()
    art = json.loads(SEED.read_text("utf-8"))
    bad = [(f["id"], ic._validate_fact(dict(f, segment=s))) for s, _, f in ic.iter_facts(art)
           if ic._validate_fact(dict(f, segment=s))]
    assert not bad, bad


@case("wrapper-fails-loudly-if-gate-renamed")
def _():
    import macro_merge
    saved = ic._macro_duplicate
    del ic._macro_duplicate
    try:
        macro_merge.disable_macro_gate()
        raise AssertionError("no SystemExit")
    except SystemExit as e:
        assert "MACRO_MERGE FAIL" in str(e)
    finally:
        ic._macro_duplicate = saved


@case("reverify-vat-same-claim-is-refreshed")
def _():
    td = workdir()
    seg, f = seed_fact("vat_rate")
    rc, out = merge(td, {"segments": {seg: [{k: f[k] for k in ("claim", "value", "source", "source_url",
                                                                "as_of", "cadence", "topic")}]}})
    st = stats(out)
    assert rc == 0 and st.get("refreshed") == "1", out
    new = json.loads((td / "macro.json").read_text("utf-8"))
    g = [x for _, _, x in ic.iter_facts(new) if x["id"] == f["id"]][0]
    assert g["harvested"] == "2026-09-26" and len(list(ic.iter_facts(new))) == 92


@case("mrot-replaced-by-id-and-fuses-ok")
def _():
    td = workdir()
    seg, f = seed_fact("contribution_base_2026")
    newf = dict(claim=f["claim"] + " Уточнено по источнику.", value=f["value"], source=f["source"],
                source_url=f.get("source_url", ""), as_of=f["as_of"], cadence=f["cadence"],
                topic=f["topic"], replaces=[f["id"]])
    payload = {"segments": {seg: [newf]}}
    rc, out = merge(td, payload)
    st = stats(out)
    assert rc == 0 and st.get("replaced_by_id") == "1" and st.get("appended") == "0", out
    new_raw = (td / "macro.json").read_bytes()
    ids = {x["id"] for _, _, x in ic.iter_facts(json.loads(new_raw))}
    assert f["id"] not in ids and len(ids) == 92
    assert fuses.check(SEED.read_bytes(), new_raw, payload) == []


@case("older-as-of-rejected")
def _():
    td = workdir()
    seg, f = seed_fact("vat_rate")
    newf = dict(claim="Другая формулировка ставки НДС 22%.", value="22%", source=f["source"],
                source_url=f["source_url"], as_of="2025-12", cadence=f["cadence"],
                topic=f["topic"], replaces=[f["id"]])
    rc, out = merge(td, {"segments": {seg: [newf]}})
    assert stats(out).get("older_rejected") == "1" and rc == 1, out
    assert (td / "macro.json").read_bytes() == SEED.read_bytes()


@case("as-of-common-precision-month-equals-day")
def _():
    # страж на ОБЩЕЙ точности (v6.61.1): «2026-07» не старее «2026-07-31»
    td = workdir()
    seg, f = seed_fact("budget_execution_7m2026")
    newf = dict(claim=f["claim"] + " (перепроверено)", value=f["value"], source=f["source"],
                source_url=f["source_url"], as_of=f["as_of"][:7], cadence=f["cadence"],
                topic=f["topic"], replaces=[f["id"]])
    rc, out = merge(td, {"segments": {seg: [newf]}})
    assert rc == 0 and stats(out).get("replaced_by_id") == "1", out


@case("fuses-identity-ok")
def _():
    assert fuses.check(SEED.read_bytes(), SEED.read_bytes(), None) == []


@case("fuses-unexplained-deletion")
def _():
    art = json.loads(SEED.read_text("utf-8"))
    victim = art["segments"]["dkp"].pop(0)
    r = fuses.check(SEED.read_bytes(), json.dumps(art, ensure_ascii=False, indent=1).encode(), None)
    assert any(x.startswith("deleted") and victim["id"] in x for x in r), r


@case("fuses-too-many-changes")
def _():
    art = json.loads(SEED.read_text("utf-8"))
    n = 0
    for _, _, f in ic.iter_facts(art):
        if n < 13:
            f["id"] = "zz%06d" % n
            n += 1
    r = fuses.check(SEED.read_bytes(), json.dumps(art, ensure_ascii=False, indent=1).encode(), None)
    assert any(x.startswith("changed: 26") for x in r), r


@case("fuses-schema-and-size")
def _():
    art = json.loads(SEED.read_text("utf-8"))
    art["schema_version"] = 1
    assert fuses.check(SEED.read_bytes(), json.dumps(art).encode(), None)[0].startswith("schema")
    art = json.loads(SEED.read_text("utf-8"))
    art["segments"]["nalogi"][0]["as_of"] = ""
    assert any(x.startswith("schema: facts without") for x in
               fuses.check(SEED.read_bytes(), json.dumps(art, ensure_ascii=False, indent=1).encode(), None))
    art = json.loads(SEED.read_text("utf-8"))
    art["segments"]["nalogi"][0]["claim"] += "x" * 60000
    assert any(x.startswith("size") for x in
               fuses.check(SEED.read_bytes(), json.dumps(art, ensure_ascii=False, indent=1).encode(), None))
    assert fuses.check(SEED.read_bytes(), b"{not json", None)[0].startswith("schema: not JSON")


@case("fuses-dossier-cap-and-leak")
def _():
    assert fuses.check_dossier((ROOT / "macro" / "macro_dossier.md").read_bytes()) == []
    assert fuses.check_dossier(b"x" * (20 * 1024 + 1))[0].startswith("dossier: 20481")
    assert fuses.check_dossier("chat telegram:123".encode())[0].startswith("dossier: ")


@case("copy-sha-matches-readme")
def _():
    readme = (ROOT / "README.md").read_text("utf-8")
    m = re.search(r"industry_cache\.py[^\n]*?`([0-9a-f]{64})`", readme)
    assert m, "README must state the sha256 of tools/industry_cache.py"
    assert hashlib.sha256((HERE / "industry_cache.py").read_bytes()).hexdigest() == m.group(1)


if __name__ == "__main__":
    print("%d passed, %d failed" % (len(PASSED), len(FAILED)))
    sys.exit(1 if FAILED else 0)
