#!/usr/bin/env python3
"""
feeds.py — еженедельный снимок лент официальных источников и «Ведомостей».

Зачем снимок каждую неделю, а не чтение раз в месяц (замер 25.09.2026):
память лент короче месяца — пресс-релизы ЦБ 26 дней, документы правительства
23, «Ведомости» 28, пресс-центр минфина ~4 дня. Рутина каждую пятницу
детерминированно (без разбора агентом) снимает новые записи, отсекает немакро
словарём `feeds_keywords.json` и кладёт снимок `runs/<неделя>/feeds.json`;
месячный проход разбирает объединение снимков за 5 недель.

Источники:
    cbr_events   RSS событий Банка России (память 77 дней)
    cbr_press    RSS пресс-релизов Банка России (26 дней)
    gov_docs     RSS документов Правительства (23 дня)
    minfin       пресс-релизы минфина проходом по номерам `?id_4=N`: RSS у
                 минфина нет, пресс-центр листается через AJAX; номера идут
                 подряд, несуществующий даёт 404 — идём от последнего
                 увиденного (состояние в прошлом снимке) до STOP_404 подряд
    vedomosti    RSS «Ведомости. Экономика» (28 дней) — сигнал, не источник
    cons_week    еженедельный обзор законодательства КонсультантПлюс
                 (рубрики — юристы; обзоры по субботам, архив по датам)
    cons_bills   RSS «Обзор законопроектов» КонсультантПлюс (7 дней) —
                 законопроекты Думы, сайт которой из облака недоступен
Портала опубликования здесь нет намеренно (422 акта за 35 дней, по делу
~8–10): он — точечный поиск принятия и источник на рубеже года.

В снимок идут только заголовок (официальное название акта или новости),
дата, ссылка, рубрика и сегменты — без редакционных текстов источников.

Использование:
    python3 tools/feeds.py --today YYYY-MM-DD --out runs/<неделя>/feeds.json \
        [--since YYYY-MM-DD] [--runs-dir runs] [--macro macro/macro.json] [--minfin-start N]
    python3 tools/feeds.py --today YYYY-MM-DD --digest 35 --out runs/<неделя>/feeds_month.json
"""
from __future__ import annotations

import argparse
import email.utils
import html
import json
import re
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify_sources as vs  # noqa: E402  (curl с UA, прокси из MACRO_PROXY)

STOP_404 = 6          # столько несуществующих номеров минфина подряд = конец
MINFIN_MAX = 120      # номеров за прогон (≈ 2 месяца при ~1,5 в день)
DEFAULT_SINCE_DAYS = 8
RSS = {
    "cbr_events": "https://www.cbr.ru/rss/eventrss",
    "cbr_press": "https://www.cbr.ru/rss/RssPress",
    "gov_docs": "http://government.ru/docs/rss/",
    "vedomosti": "https://www.vedomosti.ru/rss/rubric/economics",
    "cons_bills": "https://www.consultant.ru/rss/zw.xml",
}
MINFIN_URL = "https://minfin.gov.ru/ru/press-center/?id_4=%d"
CONS_ARCHIVE = "https://www.consultant.ru/law/review/fed/fw/archive/"
CONS_WEEK = "https://www.consultant.ru/law/review/fed/fw%s.html"
_MONTHS = {"январ": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5, "июн": 6, "июл": 7,
           "август": 8, "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12}


# ---------------------------------------------------------------- network
def http_get(url: str, proxy: str | None = None) -> tuple[int, bytes]:
    """(HTTP-код, тело). Тот же curl, что у сверки: UA, -k, прокси не печатается."""
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "body"
        code, _ctype, rc = vs.curl_fetch(url, proxy, dst)
        body = dst.read_bytes() if dst.exists() else b""
    return (code if rc == 0 else 0), body


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _ru_date(s: str) -> date | None:
    m = re.search(r"(\d{1,2})\s+([а-я]+)\s+(20\d\d)", s or "")
    if not m:
        return None
    mon = next((v for k, v in sorted(_MONTHS.items(), key=lambda kv: -len(kv[0]))
                if m.group(2).startswith(k)), None)
    return date(int(m.group(3)), mon, int(m.group(1))) if mon else None


# ---------------------------------------------------------------- sources
def parse_rss(body: bytes, source: str) -> list[dict]:
    t = body.decode("utf-8", "replace")
    out = []
    for it in re.findall(r"(?s)<item[ >].*?</item>", t):
        title = _clean(re.sub(r"(?s)<!\[CDATA\[(.*?)\]\]>", r"\1",
                              (re.search(r"(?s)<title>(.*?)</title>", it) or [None, ""])[1]))
        link = _clean((re.search(r"(?s)<link>(.*?)</link>", it) or [None, ""])[1])
        desc = _clean(re.sub(r"(?s)<!\[CDATA\[(.*?)\]\]>", r"\1",
                             (re.search(r"(?s)<description>(.*?)</description>", it) or [None, ""])[1]))
        pub = (re.search(r"<pubDate>([^<]+)</pubDate>", it) or [None, ""])[1]
        try:
            d = email.utils.parsedate_to_datetime(pub.strip()).date()
        except (TypeError, ValueError, IndexError):
            d = None
        if title and link:
            out.append({"source": source, "date": d, "title": title, "url": link, "_text": desc})
    return out


def minfin_walk(start: int, get=http_get, stop_404: int = STOP_404, cap: int = MINFIN_MAX) -> tuple[list[dict], int]:
    """Пресс-релизы с номера start+1; ([записи], последний существующий номер)."""
    out, last, miss, n = [], start, 0, start
    while miss < stop_404 and n - start < cap:
        n += 1
        code, body = get(MINFIN_URL % n)
        if code != 200:
            miss += 1
            continue
        t = body.decode("utf-8", "replace")
        m = re.search(r"(?s)<title>(.*?)</title>", t)
        title = _clean(m.group(1)) if m else ""
        title = re.sub(r"^Новость\s*\\\s*", "", title)
        if not title or title == "Минфин России":
            miss += 1
            continue
        miss, last = 0, n
        out.append({"source": "minfin", "date": _ru_date(t), "title": title, "url": MINFIN_URL % n, "_text": ""})
    return out, last


def cons_week_dates(archive: bytes, since: date, today: date) -> list[str]:
    ds = sorted(set(re.findall(r"fw(20\d\d-\d\d-\d\d)\.html", archive.decode("utf-8", "replace"))))
    return [d for d in ds if since <= date.fromisoformat(d) <= today]


def parse_cons_week(body: bytes, review_date: str) -> list[dict]:
    """Обзор: h3 — рубрика, p.doc_link — акт (ссылка + официальное название),
    следующий жирный абзац — однострочник-суть (только для фильтра, не хранится)."""
    t = body.decode("utf-8", "replace")
    t = t[t.find("<body"):] if "<body" in t else t
    out = []
    for part in re.split(r"<h3[^>]*>", t)[1:]:
        rubric = re.sub(r"\s+", " ", _clean(part.split("</h3>")[0])).strip()
        for m in re.finditer(r'(?s)<p class="doc_link">\s*<a href="([^"]+)"[^>]*>(.*?)</a>\s*</p>(.*?)(?=<p class="doc_link">|$)', part):
            title = _clean(m.group(2))
            head = _clean((re.search(r'(?s)font-weight:\s*bold[^>]*>(.*?)</span>', m.group(3)) or [None, ""])[1])
            dm = re.search(r"от (\d\d)\.(\d\d)\.(20\d\d)", title)
            d = date(int(dm.group(3)), int(dm.group(2)), int(dm.group(1))) if dm else date.fromisoformat(review_date)
            out.append({"source": "cons_week", "date": d, "title": title, "url": m.group(1),
                        "rubric": rubric, "_text": head})
    return out


# ---------------------------------------------------------------- filter
class Dictionary:
    def __init__(self, spec: dict):
        self.seg = {s: [re.compile(p, re.I) for p in ps] for s, ps in spec["segments"].items()}
        self.stop = [re.compile(p, re.I) for p in spec.get("stop", [])]
        self.rubrics = {re.sub(r"\s+", " ", k).strip().upper(): v for k, v in spec.get("rubrics", {}).items()}
        self.policy = {k: v for k, v in (spec.get("sources") or {}).items() if not k.startswith("_")}

    def classify(self, rec: dict) -> tuple[bool, list[str], str]:
        text = rec["title"] + " " + rec.get("_text", "")
        pol = self.policy.get(rec["source"], {})
        if any(p.search(rec["title"]) for p in self.stop):
            return False, [], "stop"
        segs = sorted(s for s, ps in self.seg.items() if any(p.search(text) for p in ps))
        why = "keyword" if segs else ""
        rub = self.rubrics.get(re.sub(r"\s+", " ", rec.get("rubric", "")).strip().upper())
        types = pol.get("rubric_doc_types")
        if rub and not segs and (not types or any(rec["title"].startswith(t) for t in types)):
            segs, why = [rub], "rubric"
        elif rub and segs and rub not in segs:
            segs = sorted(segs + [rub])
        if not segs:
            return False, [], "no keyword"
        only = pol.get("drop_if_only")
        if only and set(segs) <= set(only):
            return False, segs, "only " + ",".join(only)
        return True, segs, why


def known_urls(macro: Path | None) -> set[str]:
    if not macro or not macro.exists():
        return set()
    d = json.loads(macro.read_text("utf-8"))
    urls = {f.get("source_url", "") for fs in d.get("segments", {}).values() for f in fs}
    urls |= {r.get("source_url", "") for r in d.get("reg_calendar") or []}
    return {u.rstrip("/") for u in urls if u}


def previous_state(runs_dir: Path, out: Path) -> tuple[dict, str | None]:
    """Состояние последнего снимка до этого: минфин и дата. Детерминированно
    по самому свежему runs/*/feeds.json (кроме записываемого)."""
    best, best_key = {}, None
    for p in sorted(runs_dir.glob("*/feeds.json")):
        if p.resolve() == out.resolve():
            continue
        try:
            d = json.loads(p.read_text("utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        key = d.get("today") or ""
        if best_key is None or key > best_key:
            best, best_key = d.get("state") or {}, key
    return best, best_key


# ---------------------------------------------------------------- run
def snapshot(today: date, since: date, dic: Dictionary, known: set[str], minfin_start: int | None,
             get=http_get) -> dict:
    sources, raw = {}, []

    def take(name, fn):
        try:
            recs = fn()
            sources[name] = {"ok": True, "fetched": len(recs)}
            raw.extend(recs)
        except Exception as e:  # noqa: BLE001 — лента упала: причина, а не пустота
            sources[name] = {"ok": False, "fetched": 0, "error": type(e).__name__ + ": " + str(e)[:120]}

    def rss(name):
        def f():
            code, body = get(RSS[name])
            if code != 200:
                raise RuntimeError("http %s" % code)
            return parse_rss(body, name)
        return f

    for name in ("cbr_events", "cbr_press", "gov_docs", "vedomosti", "cons_bills"):
        take(name, rss(name))

    state = {}

    def minfin():
        if minfin_start is None:
            raise RuntimeError("no minfin start: pass --minfin-start on the first run")
        recs, last = minfin_walk(minfin_start, get)
        state["minfin_last_id"] = last
        return recs
    take("minfin", minfin)

    def cons_week():
        code, body = get(CONS_ARCHIVE)
        if code != 200:
            raise RuntimeError("archive http %s" % code)
        recs = []
        for d in cons_week_dates(body, since, today):
            c2, b2 = get(CONS_WEEK % d)
            if c2 != 200:
                raise RuntimeError("review %s http %s" % (d, c2))
            recs += parse_cons_week(b2, d)
        return recs
    take("cons_week", cons_week)

    items, seen = [], set()
    for r in raw:
        if r["date"] and r["date"] < since and r["source"] != "minfin":
            continue
        ok, segs, why = dic.classify(r)
        s = sources[r["source"]]
        s["kept"] = s.get("kept", 0) + int(ok)
        if not ok or r["url"] in seen:
            continue
        seen.add(r["url"])
        items.append({"source": r["source"], "date": r["date"].isoformat() if r["date"] else None,
                      "title": r["title"][:300], "url": r["url"], "rubric": r.get("rubric", ""),
                      "segments": segs, "why": why, "known": r["url"].rstrip("/") in known})
    items.sort(key=lambda x: (x["date"] or "", x["source"], x["url"]), reverse=True)
    if minfin_start is not None and "minfin_last_id" not in state:
        state["minfin_last_id"] = minfin_start
    return {"today": today.isoformat(), "since": since.isoformat(), "state": state,
            "sources": sources, "items": items}


def digest(runs_dir: Path, today: date, days: int) -> list[dict]:
    """Объединение снимков за `days` дней для месячного разбора: без дублей по
    URL, только ещё неизвестное слою (`known` = false), свежее сверху."""
    start = today - timedelta(days=days)
    seen: dict[str, dict] = {}
    for p in sorted(runs_dir.glob("*/feeds.json")):
        try:
            d = json.loads(p.read_text("utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        if not d.get("today") or not (start <= date.fromisoformat(d["today"]) <= today):
            continue
        for it in d.get("items") or []:
            if not it.get("known"):
                seen[it["url"]] = it
    return sorted(seen.values(), key=lambda x: (x.get("date") or "", x["source"], x["url"]), reverse=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="weekly snapshot of official feeds + Vedomosti")
    ap.add_argument("--today", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--digest", type=int, metavar="DAYS",
                    help="monthly pass: union of snapshots for DAYS days into --out (no fetching)")
    ap.add_argument("--since", help="YYYY-MM-DD (default: date of the previous snapshot, else today-8)")
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--macro", default="macro/macro.json")
    ap.add_argument("--keywords", default=str(HERE / "feeds_keywords.json"))
    ap.add_argument("--minfin-start", type=int, help="first run only: last minfin id already seen")
    a = ap.parse_args(argv)
    today = date.fromisoformat(a.today)
    out = Path(a.out)
    if a.digest:
        items = digest(Path(a.runs_dir), today, a.digest)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"today": today.isoformat(), "days": a.digest, "items": items},
                                  ensure_ascii=False, indent=1), "utf-8")
        print("FEEDS_DIGEST days=%d items=%d" % (a.digest, len(items)))
        for it in items:
            print("  %s | %-10s | %-24s | %s | %s" % (it.get("date") or "-", it["source"],
                                                      ",".join(it["segments"])[:24], it["title"][:150], it["url"]))
        return 0
    prev, prev_day = previous_state(Path(a.runs_dir), out)
    since = date.fromisoformat(a.since) if a.since else (
        date.fromisoformat(prev_day) if prev_day else today - timedelta(days=DEFAULT_SINCE_DAYS))
    start = a.minfin_start if a.minfin_start is not None else prev.get("minfin_last_id")
    dic = Dictionary(json.loads(Path(a.keywords).read_text("utf-8")))
    snap = snapshot(today, since, dic, known_urls(Path(a.macro)), start)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=1), "utf-8")
    bad = [n for n, s in snap["sources"].items() if not s["ok"]]
    print("FEEDS_STATS since=%s items=%d new=%d sources_ok=%d/%d minfin_last_id=%s%s" % (
        snap["since"], len(snap["items"]), sum(1 for i in snap["items"] if not i["known"]),
        len(snap["sources"]) - len(bad), len(snap["sources"]), snap["state"].get("minfin_last_id"),
        (" FAILED=" + ",".join(bad)) if bad else ""))
    for n, s in sorted(snap["sources"].items()):
        print("FEEDS_SOURCE %-10s ok=%-5s fetched=%-4d kept=%-4d %s" % (
            n, s["ok"], s["fetched"], s.get("kept", 0), s.get("error", "")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
