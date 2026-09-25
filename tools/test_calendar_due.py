#!/usr/bin/env python3
"""Тесты calendar_due.py: разбор next_event и отбор на настоящем посеве.
Запуск: python3 tools/test_calendar_due.py"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import calendar_due as cd  # noqa: E402

SEED = HERE.parent / "macro" / "macro.json"
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


D = date


@case("parse-explicit-dates")
def _():
    assert cd.parse("2027-01-01")["dates"] == [D(2027, 1, 1)]
    assert cd.parse("внесение проекта — до 1 октября 2026 года")["dates"] == [D(2026, 10, 1)]
    assert cd.parse("решение от 23.03.2026 — отслеживать")["dates"] == [D(2026, 3, 23)]


@case("parse-window-ignores-parenthetical-months")
def _():
    p = cd.parse("первая декада сентября 2026 (данные за январь–август)")
    assert p["window"] == (D(2026, 9, 1), D(2026, 9, 30)), p


@case("parse-window-range-and-year-of-phrase")
def _():
    assert cd.parse("Октябрь — ноябрь 2026: приказ МЭР")["window"] == (D(2026, 10, 1), D(2026, 11, 30))
    p = cd.parse("вместе с бюджетным пакетом на 2027–2029 годы — сентябрь–ноябрь 2026")
    assert p["window"] == (D(2026, 9, 1), D(2026, 11, 30)), p


@case("parse-no-may-inside-words")
def _():
    # «принимается» содержит «мает»: без границы слова давало окно «май»
    assert cd.parse("Осень 2026 — закон принимается в пакете")["window"] == (D(2026, 9, 1), D(2026, 11, 30))
    assert cd.parse("Решение обычно принимается осенью вместе с бюджетом")["window"] is None
    assert cd.parse("решение ожидалось в мае 2026")["window"] == (D(2026, 5, 1), D(2026, 5, 31))


@case("parse-quarter-and-regular")
def _():
    p = cd.parse("2026-12-31 (решение о продлении ожидается в IV квартале 2026)")
    assert p["dates"] == [D(2026, 12, 31)] and p["window"] == (D(2026, 10, 1), D(2026, 12, 31)), p
    assert cd.parse("публикуется еженедельно, обычно в среду")["every"] == 6
    assert cd.parse("проверять ежемесячно")["every"] == 28


@case("due-date-window-regular-rules")
def _():
    rs = [{"name": "d-soon", "as_of": "2026-08-20", "next_event": "2026-10-01"},
          {"name": "d-late", "as_of": "2026-08-20", "next_event": "2027-01-01"},
          {"name": "d-checked", "as_of": "2026-09-11", "next_event": "2026-09-11"},
          {"name": "w-old", "as_of": "2026-08-20", "next_event": "Октябрь — ноябрь 2026"},
          {"name": "w-fresh", "as_of": "2026-09-20", "next_event": "Октябрь — ноябрь 2026"},
          {"name": "weekly", "as_of": "2026-09-21", "next_event": "еженедельно"},
          {"name": "q4-window-beats-date", "as_of": "2026-08-20",
           "next_event": "2026-12-31 (решение в IV квартале 2026)"}]
    pick, rest = cd.due(rs, D(2026, 9, 25))
    names = [p["name"] for p in pick]
    assert names == ["d-soon", "w-old", "q4-window-beats-date"], names
    assert {r["name"] for r in rest} == {"d-late", "d-checked", "w-fresh", "weekly"}


@case("due-cap-keeps-dates-first")
def _():
    rs = [{"name": "w%d" % i, "as_of": "2026-01-01", "next_event": "сентябрь 2026"} for i in range(10)]
    rs.append({"name": "date", "as_of": "2026-08-20", "next_event": "2026-09-30"})
    pick, rest = cd.due(rs, D(2026, 9, 25), cap=3)
    assert pick[0]["name"] == "date" and len(pick) == 3 and len(rest) == 8
    assert all("over cap" in r["reason"] for r in rest)


@case("seed-is-deterministic-and-capped")
def _():
    recipes = json.loads(SEED.read_text("utf-8"))["reg_calendar"]
    a = cd.due(recipes, D(2026, 9, 25))
    b = cd.due(recipes, D(2026, 9, 25))
    assert a == b and len(a[0]) == cd.CAP, len(a[0])
    assert all(isinstance(x["reason"], str) and x["reason"] for x in a[0] + a[1])


if __name__ == "__main__":
    print("%d passed, %d failed" % (len(PASSED), len(FAILED)))
    sys.exit(1 if FAILED else 0)
