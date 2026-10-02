#!/usr/bin/env python3
"""
dossier_due.py — какие разделы досье перечитать в этот прогон.

Досье (`macro/macro_dossier.md`) — нарративный фон, который finalize читает
вместе с `macro.json`. До 25.09 его правили только при ≥5 заменах и только в
абзацах с числами заменённых фактов; тезис без чисел («цена денег и доступ к
ним разошлись») не трогался никогда, а срока годности у досье не было.

Разметка (логика docs/LOGIC-2026-09-25-macro-monthly-pass.md, §3.5):
    строка в шапке      Проверено: YYYY-MM-DD
    под каждым `## `    <!-- rests_on: topic_a, topic_b, macro_debt:g_spreads -->
Опора `macro_debt:*` — долговой срез сервера, облаку недоступен: такой раздел
помечается «не перепроверен: нужен долговой срез», а не проверяется.

Правила:
    еженедельно  раздел, у которого хоть одна опорная тема перепроверена или
                 заменена позже «Проверено» (harvested факта > даты);
    ежемесячно   (--monthly) — все разделы;
    декабрь      с 18 декабря — «Рамка года» переписывается на следующий год.
Проблемы разметки (нет «Проверено», раздел без опор, опора на тему, которой
нет в macro.json) печатаются и ловятся предохранителями (`fuses.py --dossier`).

Использование:
    python3 tools/dossier_due.py --dossier macro/macro_dossier.md --macro macro/macro.json \
        --today YYYY-MM-DD [--monthly] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

CHECKED_RE = re.compile(r"^Проверено:\s*(\d{4}-\d{2}-\d{2})\s*$", re.M)
ANCHOR_RE = re.compile(r"<!--\s*rests_on:\s*(.*?)-->", re.S)
FRAME_TITLE = "Рамка года"
DECEMBER_DAY = 18


def parse(text: str) -> dict:
    m = CHECKED_RE.search(text)
    sections = []
    for part in re.split(r"(?m)^## ", text)[1:]:
        title = part.split("\n", 1)[0].strip()
        a = ANCHOR_RE.search(part)
        rests = [x.strip() for x in re.split(r"[,\s]+", a.group(1)) if x.strip()] if a else None
        sections.append({"title": title, "rests_on": rests})
    return {"checked": m.group(1) if m else None, "sections": sections, "anchored": bool(m) or any(
        s["rests_on"] is not None for s in sections)}


def fact_dates(macro: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for facts in (macro.get("segments") or {}).values():
        for f in facts:
            out.setdefault(f.get("topic", ""), []).append(f.get("harvested") or "")
    return out


def problems(doc: dict, topics: dict[str, list[str]]) -> list[str]:
    out = []
    if not doc["checked"]:
        out.append("no 'Проверено: YYYY-MM-DD' line")
    for s in doc["sections"]:
        if s["rests_on"] is None:
            out.append("section without rests_on: %s" % s["title"])
            continue
        unknown = [t for t in s["rests_on"] if not t.startswith("macro_debt:") and t not in topics]
        if unknown:
            out.append("section '%s' rests on unknown topics: %s" % (s["title"], ", ".join(unknown)))
    return out


def due(doc: dict, topics: dict[str, list[str]], today: date, monthly: bool) -> list[dict]:
    checked = doc["checked"] or "0000-00-00"
    out = []
    for s in doc["sections"]:
        rests = s["rests_on"] or []
        moved = sorted(t for t in rests if any(h > checked for h in topics.get(t, [])))
        server = [t for t in rests if t.startswith("macro_debt:")]
        reasons = []
        if monthly:
            reasons.append("monthly full re-read")
        if moved:
            reasons.append("facts re-verified or replaced after %s: %s" % (checked, ", ".join(moved)))
        if s["title"].startswith(FRAME_TITLE) and today.month == 12 and today.day >= DECEMBER_DAY:
            reasons.append("December: rewrite the frame for %d" % (today.year + 1))
        if reasons:
            out.append({"title": s["title"], "reasons": reasons, "moved": moved,
                        "needs_server": server})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="dossier sections to re-read this run")
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--macro", required=True)
    ap.add_argument("--today", required=True)
    ap.add_argument("--monthly", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    doc = parse(Path(a.dossier).read_text("utf-8"))
    topics = fact_dates(json.loads(Path(a.macro).read_text("utf-8")))
    d = due(doc, topics, date.fromisoformat(a.today), a.monthly)
    probs = problems(doc, topics)
    if a.json:
        print(json.dumps({"checked": doc["checked"], "due": d, "problems": probs}, ensure_ascii=False, indent=1))
        return 0
    print("DOSSIER_DUE checked=%s sections=%d due=%d problems=%d" % (
        doc["checked"], len(doc["sections"]), len(d), len(probs)))
    for x in d:
        print("  DUE %s — %s%s" % (x["title"], "; ".join(x["reasons"]),
                                   (" [not re-checkable in the cloud: %s]" % ", ".join(x["needs_server"]))
                                   if x["needs_server"] else ""))
    for p in probs:
        print("  PROBLEM " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
