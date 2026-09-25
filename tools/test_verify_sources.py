#!/usr/bin/env python3
"""Офлайн-тесты verify_sources.py: форматы чисел и дат, цитата, маршрут, утечка прокси.
Запуск: python3 tools/test_verify_sources.py"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import zipfile
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_sources as vs  # noqa: E402

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


NB = "\u00a0"
PAGE = ("<html><head><title>Налоги 2026</title></head><body>"
        "<p>Основная ставка НДС с 1 января 2026 года составляет 22" + NB + "%.</p>"
        "<p>Пониженные ставки: 5 % при доходе до 272,5" + NB + "млн рублей и 7 процентов до 490,5 млн рублей.</p>"
        "<p>Средняя зарплата — 110" + NB + "216 рублей, рост на 10,9 %.</p>"
        "<p>Вправе не позднее 1" + NB + "июня 2026" + NB + "года уведомить налоговый орган.</p>"
        "<p>Решение принимается в пятницу, ставка действует со следующего понедельника.</p>"
        + "<p>" + "наполнитель " * 300 + "</p></body></html>")


class FakeNet:
    """url -> {route: (code, body)}; пишет тело туда же, куда curl."""

    def __init__(self, table):
        self.table, self.calls = table, []

    def __call__(self, url, proxy, dst):
        route = "proxy" if proxy else "direct"
        self.calls.append((url, route))
        code, body = self.table.get(url, {}).get(route, (0, b""))
        if code == 0:
            if dst.exists():
                dst.unlink()
            return 0, "", 7
        dst.write_bytes(body)
        return code, "text/html; charset=utf-8", 0


def fetcher(table, proxy="http://u:p@h:1"):
    return vs.Fetcher(Path(tempfile.mkdtemp()), proxy=proxy, fetch=FakeNet(table))


URL = "https://www.nalog.gov.ru/new2026/"
OKNET = {URL: {"direct": (200, PAGE.encode("utf-8"))}}


@case("tokens-percent-formats")
def _():
    t = vs.tokens("22%, 22 %, 22" + NB + "%, 22 процента")
    assert t["nums"] == [Decimal(22)] * 4, t


@case("tokens-thousands-nbsp-and-decimal-comma")
def _():
    t = vs.tokens("110" + NB + "216 руб.; 6\u202f455 млрд; 272,5 и 272.5; 45,11 трлн")
    assert t["nums"] == [Decimal("110216"), Decimal("6455"), Decimal("272.5"), Decimal("272.5"), Decimal("45.11")], t


@case("tokens-dates-three-forms-one-date")
def _():
    t = vs.tokens("до 01.06.2026, 2026-06-01, не позднее 1" + NB + "июня 2026 г.")
    assert t["dates"] == {"2026-06-01"} and t["nums"] == [], t


@case("tokens-years-are-weak")
def _():
    t = vs.tokens("20 / 15 / 10 млн ₽ (2026/2027/2028)")
    assert t["nums"] == [Decimal(20), Decimal(15), Decimal(10)] and t["weak"] == ["2026", "2027", "2028"], t


@case("tokens-range-and-minus")
def _():
    t = vs.tokens("3–5% годовых; КС−7 п.п.")
    assert t["nums"] == [Decimal(3), Decimal(5), Decimal(7)], t


@case("num-match-rounding")
def _():
    assert vs.num_match(Decimal("110216"), [Decimal("110216.3")])      # xlsx Росстата
    assert vs.num_match(Decimal("6455"), [Decimal("6455.6")])          # усечение
    assert vs.num_match(Decimal("10.9"), [Decimal("10.94")])
    assert not vs.num_match(Decimal("22"), [Decimal("2.2"), Decimal("220")])
    assert not vs.num_match(Decimal("20.5"), [Decimal("20")])


@case("quote-normalisation-and-fragments")
def _():
    page = vs.norm(vs.html_text(PAGE))
    assert vs.quote_found("пониженные ставки: 5 % при доходе до 272,5 млн рублей", page)
    assert vs.quote_found("Основная ставка НДС ... составляет 22 %", page)
    assert not vs.quote_found("Основная ставка НДС составляет 20 %", page)


@case("verified")
def _():
    r = vs.verify_item({"value": "22%", "source_url": URL,
                        "evidence": "с 1 января 2026 года составляет 22 %"}, fetcher(OKNET))
    assert r["verdict"] == "VERIFIED" and r["route"] == "direct", r


@case("verified-word-date-vs-dmy-value")
def _():
    r = vs.verify_item({"value": "уведомление до 01.06.2026", "source_url": URL,
                        "evidence": "Вправе не позднее 1 июня 2026 года уведомить"}, fetcher(OKNET))
    assert r["verdict"] == "VERIFIED", r


@case("not-found-number-missing-in-quote")
def _():
    r = vs.verify_item({"value": "5% до 272,5 млн ₽; 7% до 490,5 млн ₽", "source_url": URL,
                        "evidence": "Пониженные ставки: 5 % при доходе до 272,5 млн рублей"}, fetcher(OKNET))
    assert r["verdict"] == "NOT_FOUND" and "7" in r["detail"] and "490.5" in r["detail"], r


@case("composite-value-list-of-quotes")
def _():
    r = vs.verify_item({"value": "5% до 272,5 млн ₽; 7% до 490,5 млн ₽", "source_url": URL,
                        "evidence": ["Пониженные ставки: 5 % при доходе до 272,5 млн рублей",
                                     "7 процентов до 490,5 млн рублей"]}, fetcher(OKNET))
    assert r["verdict"] == "VERIFIED", r


@case("one-fabricated-quote-in-list-fails")
def _():
    r = vs.verify_item({"value": "5% до 272,5 млн ₽", "source_url": URL,
                        "evidence": ["Пониженные ставки: 5 % при доходе до 272,5 млн рублей",
                                     "ставка 5% отменена с 2027 года"]}, fetcher(OKNET))
    assert r["verdict"] == "QUOTE_NOT_FOUND" and "2" in r["detail"], r


@case("quote-not-found-fabricated")
def _():
    r = vs.verify_item({"value": "20%", "source_url": URL,
                        "evidence": "основная ставка НДС составляет 20 %"}, fetcher(OKNET))
    assert r["verdict"] == "QUOTE_NOT_FOUND", r


@case("verified-text-without-numbers")
def _():
    r = vs.verify_item({"value": "решение в пятницу → действие с понедельника", "source_url": URL,
                        "evidence": "Решение принимается в пятницу, ставка действует со следующего понедельника"},
                       fetcher(OKNET))
    assert r["verdict"] == "VERIFIED_TEXT", r


@case("no-evidence-html")
def _():
    r = vs.verify_item({"value": "22%", "source_url": URL}, fetcher(OKNET))
    assert r["verdict"] == "NO_EVIDENCE", r


@case("no-url")
def _():
    assert vs.verify_item({"value": "22%"}, fetcher(OKNET))["verdict"] == "NO_URL"


def _xlsx(rows):
    """rows: [[cell, …]]; строки — shared strings, числа — как в xlsx Росстата."""
    b = io.BytesIO()
    strings = sorted({c for r in rows for c in r if not c.replace(".", "").isdigit()})
    idx = {t: i for i, t in enumerate(strings)}
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/sharedStrings.xml", "<sst>" + "".join("<si><t>%s</t></si>" % t for t in strings) + "</sst>")
        body = ""
        for r in rows:
            body += "<row>" + "".join(
                ('<c t="s"><v>%d</v></c>' % idx[c]) if c in idx else "<c><v>%s</v></c>" % c for c in r) + "</row>"
        z.writestr("xl/worksheets/sheet1.xml", "<worksheet><sheetData>%s</sheetData></worksheet>" % body)
    return b.getvalue()


XLSX = _xlsx([["Российская Федерация", "110216.3", "10.94"], ["Центральный федеральный округ", "2.2", "3"]])
XURL = "https://rosstat.gov.ru/storage/mediabank/tab1-zpl_05-2026.xlsx"


@case("xlsx-rows-text")
def _():
    text, kind = vs.extract(XLSX)
    assert kind == "xlsx" and "Российская Федерация | 110216,3 | 10,94" in text, text


@case("xlsx-row-quote-verified-with-rounding")
def _():
    f = fetcher({XURL: {"direct": (200, XLSX)}})
    r = vs.verify_item({"value": "110 216 руб./мес, +10,9% г/г", "source_url": XURL,
                        "evidence": "Российская Федерация | 110216,3 | 10,94"}, f)
    assert r["verdict"] == "VERIFIED" and r["kind"] == "xlsx", r


@case("xlsx-without-quote-is-not-verified")
def _():
    # пилот 25.09: «2,2%» и «3» есть в любой большой таблице — без строки-цитаты не доказательство
    f = fetcher({XURL: {"direct": (200, XLSX)}})
    r = vs.verify_item({"value": "2,2% (скользящее за 3 мес.)", "source_url": XURL}, f)
    assert r["verdict"] == "NO_EVIDENCE", r


@case("negative-value-never-verified")
def _():
    for v in ("нет данных", "Нет данных (источник закрыт)", "данные не найдены"):
        r = vs.verify_item({"value": v, "source_url": URL, "evidence": "Налоги 2026"}, fetcher(OKNET))
        assert r["verdict"] == "NEGATIVE", (v, r)
    r = vs.verify_item({"value": "нетарифные меры 3%", "source_url": URL, "evidence": "22 %"}, fetcher(OKNET))
    assert r["verdict"] != "NEGATIVE", r


@case("links-absolute-and-filtered")
def _():
    page = ('<html><body><a href="/ru/press-center/?id_4=40635-byudzhetnyi_paket" title="Бюджетный пакет">'
            '<img></a><a href="https://x.ru/a">Другое</a>' + "<p>" + "x " * 1500 + "</p></body></html>").encode()
    u = "https://minfin.gov.ru/ru/press-center/"
    f = fetcher({u: {"direct": (200, page)}})
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        vs.links(f, u, "бюджет")
    out = buf.getvalue()
    assert "LINK Бюджетный пакет -> https://minfin.gov.ru/ru/press-center/?id_4=40635-byudzhetnyi_paket" in out, out
    assert "x.ru" not in out and "LINKS shown=1" in out, out


STUB503 = ("<html><body>Доступ к сайту временно ограничен владельцем веб-ресурса. "
           "Ваш IP-адрес: 0.0.0.0</body></html>").encode("utf-8")
DDG = b"<html><title>DDoS-Guard</title><body>ddos-guard check</body></html>"


@case("route-direct-blocked-then-proxy")
def _():
    net = {URL: {"direct": (503, STUB503), "proxy": (200, PAGE.encode("utf-8"))}}
    r = vs.verify_item({"value": "22%", "source_url": URL, "evidence": "составляет 22 %"}, fetcher(net))
    assert r["verdict"] == "VERIFIED" and r["route"] == "proxy", r


@case("route-antibot-200-counts-as-blocked")
def _():
    net = {URL: {"direct": (200, DDG + b" " * 3000), "proxy": (200, PAGE.encode("utf-8"))}}
    r = vs.verify_item({"value": "22%", "source_url": URL, "evidence": "составляет 22 %"}, fetcher(net))
    assert r["route"] == "proxy", r


@case("unreachable-is-not-refuted")
def _():
    net = {URL: {"direct": (503, STUB503), "proxy": (503, STUB503)}}
    r = vs.verify_item({"value": "22%", "source_url": URL, "evidence": "составляет 22 %"}, fetcher(net))
    assert r["verdict"] == "UNREACHABLE" and "direct: http 503" in r["detail"] and "proxy: http 503" in r["detail"], r


@case("no-proxy-means-single-try")
def _():
    net = FakeNet({URL: {"direct": (503, STUB503)}})
    f = vs.Fetcher(Path(tempfile.mkdtemp()), proxy=None, fetch=net)
    assert f.get(URL)["ok"] is False and net.calls == [(URL, "direct")]


@case("page-fetched-once-per-run")
def _():
    net = FakeNet(OKNET)
    f = vs.Fetcher(Path(tempfile.mkdtemp()), fetch=net)
    for _ in range(3):
        vs.verify_item({"value": "22%", "source_url": URL, "evidence": "составляет 22 %"}, f)
    assert net.calls == [(URL, "direct")], net.calls


@case("run-splits-and-strips")
def _():
    cands = {"segments": {"nalogi": [
        {"claim": "c1", "value": "22%", "source": "ФНС", "source_url": URL, "as_of": "2026-01-01",
         "cadence": "annual", "topic": "vat_rate", "replaces": ["585d6ffd"],
         "evidence": "составляет 22 %"},
        {"claim": "c2", "value": "20%", "source": "ФНС", "source_url": URL, "as_of": "2026-01-01",
         "cadence": "annual", "topic": "x", "evidence": "выдуманная цитата про 20 %"}]},
        "reg_calendar": [{"name": "r1", "cadence": "slow", "last_value": "22%", "as_of": "2026-09-25",
                          "next_event": "2027-01-01", "source_url": URL, "evidence": "составляет 22 %"}]}
    ver, pen, rep = vs.run(cands, fetcher(OKNET))
    f = ver["segments"]["nalogi"]
    assert len(f) == 1 and "evidence" not in f[0] and f[0]["replaces"] == ["585d6ffd"], ver
    assert pen["segments"]["nalogi"][0]["_verdict"] == "QUOTE_NOT_FOUND", pen
    rc = ver["reg_calendar"][0]
    assert "evidence" not in rc and rc.get("source_url") == URL, rc
    assert rep["hosts"]["nalog.gov.ru"]["direct"] == 3, rep["hosts"]


@case("proxy-value-never-leaks")
def _():
    secret = "http://SECRETUSER:SECRETPASS@127.0.0.1:9"
    td = Path(tempfile.mkdtemp())
    (td / "c.json").write_text(json.dumps({"segments": {"s": [
        {"claim": "c", "value": "22%", "source": "x", "source_url": "http://127.0.0.1:9/x",
         "as_of": "2026-01-01", "cadence": "slow", "evidence": "22 %"}]}}), "utf-8")
    old = os.environ.get("MACRO_PROXY")
    os.environ["MACRO_PROXY"] = secret
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            vs.main(["--candidates", str(td / "c.json"), "--out-dir", str(td / "out")])
    finally:
        if old is None:
            os.environ.pop("MACRO_PROXY", None)
        else:
            os.environ["MACRO_PROXY"] = old
    blob = buf.getvalue() + "".join(p.read_text("utf-8", "replace") for p in (td / "out").rglob("*") if p.is_file())
    assert "SECRET" not in blob, "proxy credentials leaked"
    assert "UNREACHABLE=1" in buf.getvalue() and "proxy=yes" in buf.getvalue(), buf.getvalue()


if __name__ == "__main__":
    print("%d passed, %d failed" % (len(PASSED), len(FAILED)))
    sys.exit(1 if FAILED else 0)
