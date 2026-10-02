#!/usr/bin/env python3
"""Тесты dossier_due.py: разбор разметки, отбор разделов, проблемы.
Запуск: python3 tools/test_dossier_due.py"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dossier_due as dd  # noqa: E402

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


DOC = """# Макро-слой
Проверено: 2026-09-25

## Рамка года
<!-- rests_on: cbr_forecast_gdp, cbr_forecast_keyrate -->
Текст.

## Деньги: цена отдельно, доступ отдельно
<!-- rests_on: effekt_nadbavki,
     anticiklicheskaya_nadbavka, macro_debt:g_spreads -->
Текст.

## Труд
<!-- rests_on: zarplaty -->
"""
MACRO = {"segments": {"dkp": [{"topic": "cbr_forecast_gdp", "harvested": "2026-09-25"},
                              {"topic": "cbr_forecast_keyrate", "harvested": "2026-10-02"}],
                      "finansirovanie": [{"topic": "effekt_nadbavki", "harvested": "2026-08-20"},
                                         {"topic": "anticiklicheskaya_nadbavka", "harvested": "2026-08-20"}],
                      "trud": [{"topic": "zarplaty", "harvested": "2026-08-20"}]}}
TOPICS = dd.fact_dates(MACRO)


@case("parse-checked-and-multiline-anchors")
def _():
    doc = dd.parse(DOC)
    assert doc["checked"] == "2026-09-25" and doc["anchored"]
    assert [s["title"] for s in doc["sections"]] == ["Рамка года", "Деньги: цена отдельно, доступ отдельно", "Труд"]
    assert doc["sections"][1]["rests_on"] == ["effekt_nadbavki", "anticiklicheskaya_nadbavka", "macro_debt:g_spreads"]


@case("weekly-only-sections-whose-facts-moved")
def _():
    d = dd.due(dd.parse(DOC), TOPICS, date(2026, 10, 9), monthly=False)
    assert [x["title"] for x in d] == ["Рамка года"] and d[0]["moved"] == ["cbr_forecast_keyrate"], d


@case("same-day-harvest-is-not-newer")
def _():
    # факт перепроверен в день «Проверено» — досье уже учитывало его
    d = dd.due(dd.parse(DOC), {"cbr_forecast_gdp": ["2026-09-25"]}, date(2026, 9, 25), monthly=False)
    assert d == [], d


@case("monthly-all-sections-and-server-mark")
def _():
    d = dd.due(dd.parse(DOC), TOPICS, date(2026, 10, 2), monthly=True)
    assert len(d) == 3 and all("monthly full re-read" in x["reasons"] for x in d)
    money = [x for x in d if x["title"].startswith("Деньги")][0]
    assert money["needs_server"] == ["macro_debt:g_spreads"], money


@case("december-frame-rewrite")
def _():
    d = dd.due(dd.parse(DOC), TOPICS, date(2026, 12, 18), monthly=False)
    frame = [x for x in d if x["title"] == "Рамка года"][0]
    assert any("rewrite the frame for 2027" in r for r in frame["reasons"]), frame
    assert dd.due(dd.parse(DOC), {}, date(2026, 12, 17), monthly=False) == []


@case("problems-detected")
def _():
    bad = DOC.replace("Проверено: 2026-09-25\n", "").replace("<!-- rests_on: zarplaty -->", "") \
             .replace("cbr_forecast_gdp,", "cbr_forecast_gpd,")
    p = dd.problems(dd.parse(bad), TOPICS)
    assert any("no 'Проверено" in x for x in p)
    assert any("without rests_on: Труд" in x for x in p)
    assert any("unknown topics: cbr_forecast_gpd" in x for x in p), p
    assert dd.problems(dd.parse(DOC), TOPICS) == []


@case("legacy-unanchored-dossier")
def _():
    doc = dd.parse("# Досье\n\n## Раздел\nТекст без разметки.\n")
    assert doc["anchored"] is False and doc["checked"] is None


if __name__ == "__main__":
    print("%d passed, %d failed" % (len(PASSED), len(FAILED)))
    sys.exit(1 if FAILED else 0)
