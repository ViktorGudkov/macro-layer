#!/usr/bin/env python3
"""
fuses.py — предохранители недельного коммита macro.json (логика §3.2 п.6).

Сравнивает файл до прогона (обычно `git show HEAD:macro/macro.json`) и после
merge. Любое срабатывание → рабочую ветку не трогать, открыть PR с объяснением.

    changed   > 25 фактов (удалённые + новые id) — неделя слишком «громкая»;
    deleted   id исчез, и это не замена: нет в `replaces` принятых фактов и
              нет нового факта с той же темой (замена по теме);
    schema    не v2, не macro.md, у факта нет обязательного поля, status() падает;
    size      размер файла изменился больше чем на 30%;
    shrink    фактов стало меньше, чем 80% от прежнего (как у забора на сервере);
    dossier   (--dossier) больше 20 КБ или клиентские данные в тексте.

Код возврата: 0 — FUSES OK, 3 — FUSES TRIPPED, 2 — файл не читается.

Использование:
    python3 tools/fuses.py --old old_macro.json --new macro/macro.json --verified work/verified.json \
        [--dossier macro/macro_dossier.md]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_cache as ic  # noqa: E402

MAX_CHANGED = 25
MAX_SIZE_DELTA = 0.30
MIN_FACTS_RATIO = 0.80
FACT_KEYS = ("id", "harvested", "channel", "claim", "value", "source", "as_of", "cadence", "topic")


def facts_of(art: dict) -> dict[str, dict]:
    return {f.get("id", ""): f for _, _, f in ic.iter_facts(art)}


def check(old_raw: bytes, new_raw: bytes, verified: dict | None) -> list[str]:
    reasons: list[str] = []
    try:
        old, new = json.loads(old_raw), json.loads(new_raw)
    except (ValueError, UnicodeDecodeError) as e:
        return ["schema: not JSON (%s)" % type(e).__name__]
    if not isinstance(new, dict) or new.get("schema_version") != 2 or new.get("profile") != "macro.md":
        return ["schema: expected schema_version 2 and profile macro.md"]
    fo, fn = facts_of(old), facts_of(new)
    bad = [i for i, f in fn.items() if any(not str(f.get(k) or "").strip() for k in FACT_KEYS if k != "topic")]
    if bad or "" in fn:
        reasons.append("schema: facts without required fields: %s" % ", ".join(sorted(bad)[:5] or ["<no id>"]))
    try:  # тот же вызов, что сделают забор на сервере и дайджест
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "macro.json").write_bytes(new_raw)
            if ic.status(td, "macro.md").get("n_facts") != len(fn):
                reasons.append("schema: status() sees a different number of facts")
    except Exception as e:  # noqa: BLE001
        reasons.append("schema: status fails (%s)" % type(e).__name__)
    removed, added = set(fo) - set(fn), set(fn) - set(fo)
    changed = len(removed) + len(added)
    if changed > MAX_CHANGED:
        reasons.append("changed: %d facts (> %d)" % (changed, MAX_CHANGED))
    repl = set()
    for facts in ((verified or {}).get("segments") or {}).values():
        for f in facts:
            r = f.get("replaces") or []
            repl |= {r} if isinstance(r, str) else set(map(str, r))
    new_topics = {f.get("topic") for f in fn.values()}
    unexplained = sorted(i for i in removed if i not in repl and fo[i].get("topic") not in new_topics)
    if unexplained:
        reasons.append("deleted: %d facts not replaced: %s" % (len(unexplained), ", ".join(unexplained[:8])))
    if len(fo) and len(fn) < MIN_FACTS_RATIO * len(fo):
        reasons.append("shrink: %d -> %d facts" % (len(fo), len(fn)))
    if len(old_raw) and abs(len(new_raw) - len(old_raw)) > MAX_SIZE_DELTA * len(old_raw):
        reasons.append("size: %d -> %d bytes" % (len(old_raw), len(new_raw)))
    return reasons


def check_dossier(raw: bytes) -> list[str]:
    """Досье рутина правит прямо в файле — те же условия, что у merge_dossier."""
    out = []
    if len(raw) > ic.DOSSIER_CAP_BYTES:
        out.append("dossier: %d bytes (> %d)" % (len(raw), ic.DOSSIER_CAP_BYTES))
    leak = ic._client_data_leak(raw.decode("utf-8", "replace"))
    if leak:
        out.append("dossier: " + leak)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="safety fuses for the weekly macro.json commit")
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--verified")
    ap.add_argument("--dossier", help="macro/macro_dossier.md: cap 20 KB, no client data")
    a = ap.parse_args(argv)
    try:
        old_raw, new_raw = Path(a.old).read_bytes(), Path(a.new).read_bytes()
        verified = json.loads(Path(a.verified).read_text("utf-8")) if a.verified else None
    except (OSError, ValueError) as e:
        print("FUSES FAIL: cannot read input (%s)" % type(e).__name__)
        return 2
    reasons = check(old_raw, new_raw, verified)
    if a.dossier:
        try:
            reasons += check_dossier(Path(a.dossier).read_bytes())
        except OSError:
            reasons.append("dossier: not readable")
    try:
        fo, fn = facts_of(json.loads(old_raw)), facts_of(json.loads(new_raw))
    except (ValueError, UnicodeDecodeError, AttributeError):
        fo, fn = {}, {}
    print("FUSES_STATS facts %d -> %d removed=%d added=%d bytes %d -> %d" % (
        len(fo), len(fn), len(set(fo) - set(fn)), len(set(fn) - set(fo)), len(old_raw), len(new_raw)))
    if reasons:
        print("FUSES TRIPPED")
        for r in reasons:
            print("  - " + r)
        return 3
    print("FUSES OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
