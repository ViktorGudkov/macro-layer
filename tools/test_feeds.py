#!/usr/bin/env python3
"""Офлайн-тесты feeds.py: разбор лент, проход минфина, фильтр, состояние.
Запуск: python3 tools/test_feeds.py"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import feeds  # noqa: E402

PASSED, FAILED = [], []
DIC = feeds.Dictionary(json.loads((HERE / "feeds_keywords.json").read_text("utf-8")))


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


def rss(items):
    return ("<rss><channel>" + "".join(
        "<item><title><![CDATA[%s]]></title><link>%s</link><pubDate>%s</pubDate>"
        "<description>%s</description></item>" % it for it in items) + "</channel></rss>").encode()


def minfin_page(title, day):
    return ("<html><head><title>Новость \\ %s</title></head><body>%s 11:00" % (title, day)).encode()


CONS = ('<html><body><h3><a name="t1"></a>КОНСТИТУЦИОННЫЙ СТРОЙ.  ОСНОВЫ ГОСУДАРСТВЕННОГО УПРАВЛЕНИЯ</h3>'
        '<p class="doc_link"><a href="https://www.consultant.ru/document/cons_doc_LAW_1/"><strong>Указ Президента РФ от 17.09.2026 N 665 '
        '"О продлении действия отдельных специальных экономических мер"</strong></a></p>'
        '<p><span style="font-weight:bold;">До конца 2028 года продлены ограничения импорта сельхозпродукции</span></p>'
        '<p class="doc_link"><a href="https://www.consultant.ru/document/cons_doc_LAW_2/"><strong>Указ Президента РФ от 16.09.2026 N 660 '
        '"О награждении государственными наградами"</strong></a></p><p>...</p>'
        '<h3><a name="t2"></a>ТРУД И ЗАНЯТОСТЬ</h3>'
        '<p class="doc_link"><a href="https://www.consultant.ru/document/cons_doc_LAW_3/"><strong>Постановление Правительства РФ от 17.09.2026 N 1187 '
        '"О переносе выходных дней в 2027 году"</strong></a></p><p><span style="font-weight:bold;">Утвержден перенос выходных</span></p>'
        '<p class="doc_link"><a href="https://www.consultant.ru/document/cons_doc_LAW_4/"><strong>&lt;Письмо&gt; Минтруда России от 15.09.2026 N 14-1 '
        '"О профстандартах"</strong></a></p><p><span style="font-weight:bold;">Разъяснены профстандарты</span></p>'
        '</body></html>').encode()


def net(extra=None):
    table = {
        feeds.RSS["cbr_events"]: (200, rss([
            ("Банк России принял решение сохранить ключевую ставку", "https://cbr.ru/a", "Fri, 11 Sep 2026 13:30:00 +0300", ""),
            ("Банк России отозвал лицензию у банка «Х»", "https://cbr.ru/b", "Fri, 18 Sep 2026 10:00:00 +0300", ""),
            ("Старое событие про ключевую ставку", "https://cbr.ru/old", "Mon, 03 Aug 2026 10:00:00 +0300", "")])),
        feeds.RSS["cbr_press"]: (200, rss([])),
        feeds.RSS["gov_docs"]: (200, rss([])),
        feeds.RSS["vedomosti"]: (200, rss([
            ("Минфин предложил включить в базу по НДФЛ пассивные доходы", "https://vedomosti.ru/1", "Wed, 23 Sep 2026 10:00:00 +0300", ""),
            ("Инфляция в России ускорилась до 0,06% за неделю", "https://vedomosti.ru/2", "Wed, 23 Sep 2026 19:00:00 +0300", ""),
            ("Банк Англии сохранил ключевую ставку", "https://vedomosti.ru/3", "Thu, 24 Sep 2026 10:00:00 +0300", "")])),
        feeds.RSS["cons_bills"]: (200, rss([])),
        feeds.CONS_ARCHIVE: (200, b'<a href="/law/review/fed/fw2026-09-19.html">x</a><a href="/law/review/fed/fw2026-08-01.html">y</a>'),
        feeds.CONS_WEEK % "2026-09-19": (200, CONS),
        feeds.MINFIN_URL % 101: (200, minfin_page("Минфин России внес в Правительство РФ бюджетный пакет", "24 сентября 2026")),
        feeds.MINFIN_URL % 102: (404, b""),
        feeds.MINFIN_URL % 103: (200, minfin_page("Итоги конференции по инициативному бюджетированию", "25 сентября 2026")),
    }
    table.update(extra or {})
    calls = []

    def get(url):
        calls.append(url)
        return table.get(url, (404, b""))
    get.calls = calls
    return get


def run(start=100, get=None, known=frozenset()):
    return feeds.snapshot(date(2026, 9, 25), date(2026, 8, 21), DIC, set(known), start, get or net())


@case("rss-parse-and-since")
def _():
    snap = run()
    urls = {i["url"] for i in snap["items"]}
    assert "https://cbr.ru/a" in urls and "https://cbr.ru/old" not in urls, urls


@case("stop-list")
def _():
    urls = {i["url"] for i in run()["items"]}
    assert "https://cbr.ru/b" not in urls                                   # отзыв лицензии
    assert "https://vedomosti.ru/3" not in urls                             # Банк Англии
    assert "https://www.consultant.ru/document/cons_doc_LAW_2/" not in urls  # награждение


@case("vedomosti-dkp-only-dropped-signal-kept")
def _():
    urls = {i["url"] for i in run()["items"]}
    assert "https://vedomosti.ru/1" in urls and "https://vedomosti.ru/2" not in urls, urls


@case("cons-week-keyword-beats-wrong-rubric")
def _():
    items = {i["url"]: i for i in run()["items"]}
    x = items["https://www.consultant.ru/document/cons_doc_LAW_1/"]   # импорт в рубрике «Конституционный строй»
    assert "vneshtorg" in x["segments"] and x["why"] == "keyword" and x["date"] == "2026-09-17", x


@case("cons-week-rubric-only-for-acts")
def _():
    urls = {i["url"] for i in run()["items"]}
    assert "https://www.consultant.ru/document/cons_doc_LAW_3/" in urls      # постановление в рубрике «Труд»
    assert "https://www.consultant.ru/document/cons_doc_LAW_4/" not in urls  # письмо без слов словаря


@case("cons-week-only-reviews-in-window")
def _():
    g = net()
    run(get=g)
    assert feeds.CONS_WEEK % "2026-08-01" not in g.calls and feeds.CONS_WEEK % "2026-09-19" in g.calls


@case("minfin-walk-gaps-and-stop")
def _():
    g = net()
    snap = run(get=g)
    assert snap["state"]["minfin_last_id"] == 103, snap["state"]
    tried = [u for u in g.calls if "id_4=" in u]
    assert tried[-1].endswith("=%d" % (103 + feeds.STOP_404)) and len(tried) == 3 + feeds.STOP_404, tried
    t = [i for i in snap["items"] if i["source"] == "minfin"]
    assert [i["date"] for i in t] == ["2026-09-25", "2026-09-24"] and "бюджетный пакет" in t[1]["title"], t


@case("minfin-without-start-is-a-reported-failure")
def _():
    snap = run(start=None)
    assert snap["sources"]["minfin"]["ok"] is False and "minfin-start" in snap["sources"]["minfin"]["error"]
    assert all(s["ok"] for n, s in snap["sources"].items() if n != "minfin")


@case("failed-feed-is-reported-not-empty")
def _():
    snap = run(get=net({feeds.RSS["vedomosti"]: (503, b"")}))
    assert snap["sources"]["vedomosti"] == {"ok": False, "fetched": 0, "error": "RuntimeError: http 503"}


@case("known-marked")
def _():
    snap = run(known={"https://cbr.ru/a"})
    x = [i for i in snap["items"] if i["url"] == "https://cbr.ru/a"][0]
    assert x["known"] is True


@case("no-editorial-text-stored")
def _():
    blob = json.dumps(run(), ensure_ascii=False)
    assert "продлены ограничения импорта" not in blob and "_text" not in blob


@case("state-from-previous-snapshot")
def _():
    td = Path(tempfile.mkdtemp())
    (td / "runs" / "2026-W38").mkdir(parents=True)
    (td / "runs" / "2026-W38" / "feeds.json").write_text(json.dumps(
        {"today": "2026-09-18", "state": {"minfin_last_id": 40600}}), "utf-8")
    (td / "runs" / "2026-W37").mkdir(parents=True)
    (td / "runs" / "2026-W37" / "feeds.json").write_text(json.dumps(
        {"today": "2026-09-11", "state": {"minfin_last_id": 40500}}), "utf-8")
    st, day = feeds.previous_state(td / "runs", td / "runs" / "2026-W39" / "feeds.json")
    assert st == {"minfin_last_id": 40600} and day == "2026-09-18", (st, day)


@case("digest-union-window-unknown-only")
def _():
    td = Path(tempfile.mkdtemp())
    def put(week, today, items):
        (td / week).mkdir(parents=True)
        (td / week / "feeds.json").write_text(json.dumps({"today": today, "items": items}), "utf-8")
    it = lambda u, d, known=False: {"url": u, "date": d, "source": "minfin", "segments": ["byudzhet"],
                                    "title": u, "known": known}
    put("2026-W34", "2026-08-21", [it("old", "2026-08-20")])                 # вне окна 35 дней
    put("2026-W38", "2026-09-18", [it("a", "2026-09-17"), it("k", "2026-09-16", True)])
    put("2026-W39", "2026-09-25", [it("a", "2026-09-17"), it("b", "2026-09-24")])
    got = [x["url"] for x in feeds.digest(td, date(2026, 10, 2), 35)]
    assert got == ["b", "a"], got


if __name__ == "__main__":
    print("%d passed, %d failed" % (len(PASSED), len(FAILED)))
    sys.exit(1 if FAILED else 0)
