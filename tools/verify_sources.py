#!/usr/bin/env python3
"""
verify_sources.py — сверка «число есть на странице источника» для макро-слоя.

Вход — кандидаты рутины в формате merge-пакета industry_cache
(`{"segments": {seg: [fact…]}, "reg_calendar": [recipe…]}`), у каждого факта
дополнительно:
    evidence   — дословная цитата со страницы источника (≤ 300 символов)
                 или список до 4 таких цитат; ВСЕ числа поля value должны
                 стоять в цитатах, каждая цитата — на странице;
    replaces   — [id] заменяемого факта из очереди (как для merge).

Выход (--out-dir):
    verified.json      — пакет для merge: только подтверждённое, без evidence;
    pending.json       — не подтверждённое, с причиной (досверка на сервере,
                         вариант Б логики, или правка на следующей итерации);
    verify_report.json — вердикт по каждому пункту + сводка по доменам.

Вердикты:
    VERIFIED        цитата найдена на странице, все значимые числа value — в ней;
    VERIFIED_TEXT   в value нет значимых чисел, цитата найдена на странице;
    QUOTE_NOT_FOUND цитаты на странице нет (выдумана или перефразирована);
    QUOTE_TOO_SHORT ни одного фрагмента от 30 символов — голая ячейка или число
                    без подписи и периода не доказывают, о чём цифра;
    NOT_FOUND       цитата есть, но в ней нет числа(ел) value — список в detail;
    NO_EVIDENCE     нет цитаты (у xlsx тоже: цитата — строка таблицы из --show);
    NEGATIVE        value — «нет данных»: отсутствие страницей не доказывается;
    UNREACHABLE     страница не скачалась ни напрямую, ни через прокси. Это
                    «не проверено», а НЕ «опровергнуто»: пункт идёт в pending;
    UNSUPPORTED     формат, из которого текст не извлекается (PDF без pymupdf
                    и без pdftotext);
    NO_URL          нет source_url.

Нормализация (почему так, см. этап 0 в README):
    «22%», «22 %», «22 процента», «22 %» — одно число 22; неразрывные и узкие
    пробелы внутри чисел («110 216») снимаются; десятичная запятая = точка;
    даты «01.06.2026», «2026-06-01» и «1 июня 2026 г.» — одна дата
    2026-06-01 (Гарант пишет даты словами); голые годы 1990–2100 и
    месяц+год — контекст, а не доказательство; округление: значение с k
    знаками после запятой подтверждается числом страницы, которое при k
    знаках даёт то же (110 216 ← 110216,3 в xlsx Росстата).

Сеть: curl -k с браузерным UA (российский УЦ; без UA часть госсайтов
отвечает 403/503). Сначала напрямую; отказ (ошибка curl, HTTP не 2xx,
заглушка антибота, пустая страница) и задана переменная MACRO_PROXY →
повтор через прокси. Значение прокси не печатается и не пишется в отчёт.

Использование:
    python3 tools/verify_sources.py --candidates work/candidates.json --out-dir work
        [--cache-dir work/pages] [--offline]
    python3 tools/verify_sources.py --show URL [--grep 'ставк[аи] НДС'] --out-dir work
    python3 tools/verify_sources.py --show URL --links [--grep 'бюджет'] --out-dir work
    python3 tools/verify_sources.py --probe URL [URL ...] --out-dir work
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urljoin, urlsplit

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
# только заглушки защиты: голые «cloudflare»/«captcha» встречаются на живых
# страницах (ссылки CDN, формы) — этап 0 дал на kontur.ru ложное срабатывание
ANTIBOT = (b"ddos-guard", b"servicepipe", b"qrator", b"cf-chl", b"challenge-platform",
           b"__js_p_", b"just a moment", b"variti",
           "доступ к сайту временно ограничен".encode("utf-8"))
MIN_HTML_BYTES = 2000
QUOTE_MAX = 300
QUOTES_MAX = 4
MIN_CONTEXT = 30          # хотя бы один фрагмент цитаты — с контекстом, не голая ячейка

SPACES = "\u00a0\u202f\u2009\u2007\u200b\ufeff"
MONTHS = {"январ": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5, "июн": 6,
          "июл": 7, "август": 8, "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12}
_MONTH_GEN = r"(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)"
_DATE_DMY = re.compile(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)")
_DATE_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_DATE_WORD = re.compile(r"(?<!\d)(\d{1,2})\s+" + _MONTH_GEN + r"\s+(\d{4})(?!\d)")
# число: группы по три через пробел ИЛИ сплошные цифры; десятичная , или .
_NUM = re.compile(r"(?<![\d,.])(\d{1,3}(?: \d{3})+|\d+)(?:[.,](\d+))?(?![\d])")


# ---------------------------------------------------------------- text
def norm(s: str) -> str:
    """Регистр, пробелы, кавычки, тире, ё — к одному виду; для поиска цитаты."""
    s = html.unescape(s or "").lower().replace("ё", "е")
    for ch in SPACES:
        s = s.replace(ch, " ")
    s = re.sub(r"[«»“”„‟\"'`’‘]", '"', s)
    s = re.sub(r"[‐‑‒–—―−]", "-", s)
    s = s.replace("…", "...")
    return re.sub(r"\s+", " ", s).strip()


def html_text(t: str) -> str:
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|td|th|h\d)>", " ", t)
    return html.unescape(re.sub(r"<[^>]+>", " ", t))


def decode(body: bytes, ctype: str = "") -> str:
    m = re.search(r"charset=([\w-]+)", ctype or "", re.I) or \
        re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", body[:4000], re.I)
    cands = []
    if m:
        cs = m.group(1)
        cands.append(cs.decode("ascii", "ignore") if isinstance(cs, bytes) else cs)
    for enc in cands + ["utf-8", "cp1251"]:
        try:
            return body.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", "replace")


def pdf_text(body: bytes) -> str | None:
    for mod in ("fitz", "pymupdf"):
        try:
            m = __import__(mod)
            doc = m.open(stream=body, filetype="pdf")
            return "\n".join(p.get_text() for p in doc)
        except ImportError:
            continue
        except Exception:
            return None
    if shutil.which("pdftotext"):
        try:
            r = subprocess.run(["pdftotext", "-layout", "-", "-"], input=body,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=120)
            if r.returncode == 0:
                return r.stdout.decode("utf-8", "replace")
        except Exception:
            return None
    return None


def sniff(body: bytes, ctype: str = "") -> str:
    if body[:4] == b"%PDF":
        return "pdf"
    if body[:2] == b"PK":
        return "xlsx"
    head = body[:5000].lower()
    return "html" if (b"<html" in head or b"<body" in head or b"<div" in head or "html" in ctype.lower()) else "text"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def xlsx_rows(z: zipfile.ZipFile) -> str:
    """Таблица построчно: «ячейка | ячейка | …», строки — через перевод строки.

    Пилот 25.09: сплошной дамп ячеек xlsx Росстата нечитаем, цитату из него не
    взять, а сверка «число есть где-то в ячейках» на таблице в 344 тыс. символов
    подтверждала «2,2» и «3» чем угодно. Построчный текст даёт цитату «строка
    таблицы» — подпись и значения рядом.
    """
    import xml.etree.ElementTree as ET
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root:
            shared.append("".join(t.text or "" for t in si.iter() if _local(t.tag) == "t"))
    sheets = sorted((n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)),
                    key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[-1]).group(1)))
    out = []
    for n in sheets:
        out.append("== %s ==" % n.rsplit("/", 1)[-1])
        root = ET.fromstring(z.read(n))
        for row in (e for e in root.iter() if _local(e.tag) == "row"):
            cells = []
            for c in (e for e in row if _local(e.tag) == "c"):
                typ = c.get("t", "")
                v = next((e.text for e in c if _local(e.tag) == "v"), None)
                if typ == "s" and v is not None:
                    try:
                        val = shared[int(v)]
                    except (ValueError, IndexError):
                        val = ""
                elif typ == "inlineStr":
                    val = "".join(t.text or "" for t in c.iter() if _local(t.tag) == "t")
                elif v is None:
                    val = ""
                elif typ in ("str", "b", "e"):
                    val = v
                else:
                    try:
                        val = ("%.10g" % float(v)).replace(".", ",")
                    except ValueError:
                        val = v
                val = re.sub(r"\s+", " ", val).strip()
                if val:
                    cells.append(val)
            if cells:
                out.append(" | ".join(cells))
    return "\n".join(out)


def extract(body: bytes, ctype: str = "") -> tuple[str | None, str]:
    """(текст, вид) — вид: html | pdf | xlsx | text; текст None = не извлёкся."""
    if body[:4] == b"%PDF":
        return pdf_text(body), "pdf"
    if body[:2] == b"PK":
        try:
            z = zipfile.ZipFile(io.BytesIO(body))
            if any(n.startswith("xl/worksheets/") for n in z.namelist()):
                return xlsx_rows(z), "xlsx"
            parts = [n for n in z.namelist() if n.endswith(".xml") and n.startswith("word/")]
            xml = " ".join(z.read(n).decode("utf-8", "replace") for n in parts)
            return html.unescape(re.sub(r"<[^>]+>", " ", xml)), "docx"
        except Exception:
            return None, "xlsx"
    t = decode(body, ctype)
    if re.search(r"(?i)<html|<body|<div|<p[ >]", t[:5000]):
        return html_text(t), "html"
    return t, "text"


# ---------------------------------------------------------------- tokens
def _dec(intpart: str, frac: str | None) -> Decimal | None:
    try:
        return Decimal(intpart.replace(" ", "") + ("." + frac if frac else ""))
    except InvalidOperation:
        return None


def tokens(s: str) -> dict:
    """{'dates': set[str], 'nums': list[Decimal], 'weak': list[str]} из текста.

    Даты вынимаются первыми и из текста вырезаются — иначе «01.06.2026» дал бы
    числа 1,06 и 2026. Голый год 1990–2100 (4 цифры подряд) — слабый токен.
    """
    s = norm(s)
    dates: set[str] = set()

    def _cut(m, iso):
        dates.add(iso)
        return " "

    s = _DATE_ISO.sub(lambda m: _cut(m, "%s-%s-%s" % m.groups()), s)
    s = _DATE_DMY.sub(lambda m: _cut(m, "%s-%02d-%02d" % (m.group(3), int(m.group(2)), int(m.group(1)))), s)

    def _word(m):
        mon = next(v for k, v in MONTHS.items() if m.group(2).startswith(k))
        return _cut(m, "%s-%02d-%02d" % (m.group(3), mon, int(m.group(1))))

    s = _DATE_WORD.sub(_word, s)
    nums, weak = [], []
    for m in _NUM.finditer(s):
        ip, fr = m.group(1), m.group(2)
        if fr is None and " " not in ip and len(ip) == 4 and 1990 <= int(ip) <= 2100:
            weak.append(ip)
            continue
        d = _dec(ip, fr)
        if d is not None:
            nums.append(d)
    return {"dates": dates, "nums": nums, "weak": weak}


def num_match(v: Decimal, pool: list[Decimal]) -> bool:
    """v подтверждается числом пула: равно, или округление/усечение пула до
    точности v даёт v (значение в факте — округлённое число страницы)."""
    exp = v.as_tuple().exponent
    q = Decimal(1).scaleb(exp) if isinstance(exp, int) else Decimal(1)
    for p in pool:
        if p == v:
            return True
        try:
            if p.quantize(q, ROUND_HALF_UP) == v or p.quantize(q, ROUND_DOWN) == v:
                return True
        except InvalidOperation:
            continue
    return False


def missing_tokens(value: str, evidence_text: str) -> tuple[list[str], int]:
    """(чего из value нет в тексте, сколько значимых токенов у value)."""
    tv, te = tokens(value), tokens(evidence_text)
    miss = [d for d in sorted(tv["dates"]) if d not in te["dates"]]
    miss += [str(n) for n in tv["nums"] if not num_match(n, te["nums"])]
    return miss, len(tv["dates"]) + len(tv["nums"])


def quote_found(evidence: str, page_norm: str) -> bool:
    """Цитата (или каждый её фрагмент между «...») есть на странице по порядку."""
    frags = [f.strip(" .,;:") for f in norm(evidence).split("...")]
    frags = [f for f in frags if len(f) >= 12] or [norm(evidence)]
    pos = 0
    for f in frags:
        i = page_norm.find(f, pos)
        if i < 0:
            return False
        pos = i + len(f)
    return True


# ---------------------------------------------------------------- fetch
def _bad(code: int, body: bytes, kind: str) -> str | None:
    if not 200 <= code < 300:
        return "http %d" % code
    low = body[:200000].lower()
    for m in ANTIBOT:
        if m in low:
            return "antibot"
    if kind == "html" and len(body) < MIN_HTML_BYTES:
        return "stub %dB" % len(body)
    return None


def curl_fetch(url: str, proxy: str | None, dst: Path) -> tuple[int, str, int]:
    """(http, content-type, rc curl). Прокси в аргументах, но наружу не печатается."""
    hdr = dst.with_suffix(".hdr")
    cmd = ["curl", "-k", "-s", "-L", "--max-redirs", "6", "--connect-timeout", "15",
           "--max-time", "60", "--max-filesize", str(40 * 1024 * 1024), "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "-H", "Accept-Language: ru-RU,ru;q=0.9,en;q=0.5",
           "-o", str(dst), "-D", str(hdr), "-w", "%{http_code}", url]
    if proxy:
        cmd[1:1] = ["--proxy", proxy]
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=90)
    except Exception:              # не печатать исключение: в нём cmd с прокси
        return 0, "", -1
    ctype = ""
    try:
        cts = re.findall(r"(?im)^content-type:\s*([^\r\n]+)", hdr.read_text("latin-1"))
        ctype = cts[-1] if cts else ""
    except OSError:
        pass
    try:
        code = int(r.stdout.decode("ascii", "replace").strip() or 0)
    except ValueError:
        code = 0
    return code, ctype, r.returncode


class Fetcher:
    """Скачивает страницу один раз за прогон; маршрут напрямую → прокси."""

    def __init__(self, cache_dir: Path, proxy: str | None = None, offline: bool = False, fetch=curl_fetch):
        self.dir = cache_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.proxy, self.offline, self._fetch = proxy, offline, fetch
        self.memo: dict[str, dict] = {}

    def get(self, url: str) -> dict:
        if url in self.memo:
            return self.memo[url]
        key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        body_p, meta_p = self.dir / (key + ".body"), self.dir / (key + ".meta.json")
        if meta_p.exists() and body_p.exists():
            res = json.loads(meta_p.read_text("utf-8"))
            res["body"] = body_p.read_bytes()
            self.memo[url] = res
            return res
        tries = []
        res = {"url": url, "ok": False, "route": "-", "http": 0, "ctype": "", "tries": tries}
        if self.offline:
            tries.append("offline: no cached page")
        else:
            routes = [("direct", None)] + ([("proxy", self.proxy)] if self.proxy else [])
            for route, px in routes:
                code, ctype, rc = self._fetch(url, px, body_p)
                body = body_p.read_bytes() if body_p.exists() else b""
                kind = sniff(body, ctype) if body else "-"
                why = ("curl rc=%d" % rc) if rc != 0 else _bad(code, body, kind)
                tries.append("%s: %s" % (route, why or "ok"))
                if not why:
                    res.update(ok=True, route=route, http=code, ctype=ctype)
                    break
                res.update(http=code)
        if res["ok"]:
            meta_p.write_text(json.dumps({k: v for k, v in res.items()}, ensure_ascii=False), "utf-8")
            res["body"] = body_p.read_bytes()
        else:
            res["body"] = b""
        self.memo[url] = res
        return res


# ---------------------------------------------------------------- verify
def verify_item(item: dict, fetcher: Fetcher, text_field: str = "value") -> dict:
    url = (item.get("source_url") or "").strip()
    raw_ev = item.get("evidence") or []
    # список цитат: числа составного факта стоят на странице в разных абзацах
    # (ФНС «Налоги 2026»: 272,5 — у ставки 5%, 490,5 — в пороге УСН)
    evs = [str(e).strip() for e in ([raw_ev] if isinstance(raw_ev, str) else raw_ev) if str(e).strip()]
    ev = " ... ".join(evs)
    rep = {"topic": item.get("topic") or item.get("name", ""), "replaces": item.get("replaces") or [],
           "source_url": url, "value": item.get(text_field, ""), "evidence": [e[:QUOTE_MAX] for e in evs],
           "route": "-", "verdict": "", "detail": ""}
    if NEGATIVE_RE.match(norm(str(item.get(text_field) or ""))):
        # пилот 25.09: агент заменял положительный факт на «нет данных», потому
        # что источник был закрыт по расписанию. Отрицательный поиск факт не
        # снимает, а страница «отсутствие» не доказывает — с любой цитатой без
        # чисел это прошло бы как VERIFIED_TEXT.
        rep["verdict"] = "NEGATIVE"
        rep["detail"] = "a negative value cannot be verified by a page; keep the old fact"
        return rep
    if not url:
        rep["verdict"] = "NO_URL"
        return rep
    host = urlsplit(url).hostname or ""
    rep["host"] = host[4:] if host.startswith("www.") else host
    page = fetcher.get(url)
    rep["route"], rep["http"] = page["route"], page["http"]
    if not page["ok"]:
        rep["verdict"], rep["detail"] = "UNREACHABLE", "; ".join(page["tries"])
        return rep
    text, kind = extract(page["body"], page.get("ctype", ""))
    rep["kind"] = kind
    if text is None:
        rep["verdict"], rep["detail"] = "UNSUPPORTED", "%s: text not extractable" % kind
        return rep
    value = str(item.get(text_field) or "")
    if not ev:
        rep["verdict"] = "NO_EVIDENCE"
        return rep
    if max(len(norm(e)) for e in evs) < MIN_CONTEXT:
        # прогон 25.09: безработица «подтверждена» цитатой «Российская Федерация;2,2» —
        # голая ячейка, период из цитаты не виден; нужен хоть один фрагмент с контекстом
        rep["verdict"] = "QUOTE_TOO_SHORT"
        rep["detail"] = "no fragment of %d+ chars: quote a sentence, or the table row with its header/period" % MIN_CONTEXT
        return rep
    if len(evs) > QUOTES_MAX:
        rep["verdict"], rep["detail"] = "QUOTE_NOT_FOUND", "more than %d quotes" % QUOTES_MAX
        return rep
    page_n = norm(text)
    lost = [i for i, e in enumerate(evs) if not quote_found(e[:QUOTE_MAX], page_n)]
    if lost:
        rep["verdict"] = "QUOTE_NOT_FOUND"
        rep["detail"] = "quote(s) %s not on page" % ",".join(str(i + 1) for i in lost)
        return rep
    miss, n = missing_tokens(value, " ; ".join(e[:QUOTE_MAX] for e in evs))
    if not n:
        rep["verdict"] = "VERIFIED_TEXT"
    elif miss:
        rep["verdict"], rep["detail"] = "NOT_FOUND", "not in quote: " + ", ".join(miss)
    else:
        rep["verdict"] = "VERIFIED"
    return rep


OK_VERDICTS = {"VERIFIED", "VERIFIED_TEXT"}
NEGATIVE_RE = re.compile(r"^(нет данных|данные не найдены|сведений нет|сведения не найдены|не найдено|н/д)(?![а-я])")


def run(cands: dict, fetcher: Fetcher) -> tuple[dict, dict, dict]:
    verified = {"segments": {}, "reg_calendar": []}
    pending = {"segments": {}, "reg_calendar": []}
    items = []
    for seg, facts in (cands.get("segments") or {}).items():
        for f in facts:
            r = verify_item(f, fetcher)
            r.update(kind_item="fact", segment=seg)
            items.append(r)
            clean = {k: v for k, v in f.items() if k != "evidence"}
            if r["verdict"] in OK_VERDICTS:
                verified["segments"].setdefault(seg, []).append(clean)
            else:
                pending["segments"].setdefault(seg, []).append(dict(f, _verdict=r["verdict"], _detail=r["detail"]))
    for rc in cands.get("reg_calendar") or []:
        r = verify_item(rc, fetcher, text_field="last_value")
        r.update(kind_item="recipe", segment="reg_calendar")
        items.append(r)
        # merge кладёт рецепт в файл целиком: цитата (текст чужой страницы) в
        # файл не идёт, а source_url остаётся — у инициатив (kind, stage) это
        # адрес, по которому рутина проверяет стадию (monthly-pass §4)
        clean = {k: v for k, v in rc.items() if k != "evidence"}
        if r["verdict"] in OK_VERDICTS:
            verified["reg_calendar"].append(clean)
        else:
            pending["reg_calendar"].append(dict(rc, _verdict=r["verdict"], _detail=r["detail"]))
    hosts: dict[str, dict] = {}
    for r in items:
        h = r.get("host")
        if not h:
            continue
        e = hosts.setdefault(h, {"items": 0, "direct": 0, "proxy": 0, "unreachable": 0})
        e["items"] += 1
        if r["verdict"] == "UNREACHABLE":
            e["unreachable"] += 1
        elif r["route"] in ("direct", "proxy"):
            e[r["route"]] += 1
    counts: dict[str, int] = {}
    for r in items:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    report = {"counts": counts, "hosts": hosts, "items": items}
    return verified, pending, report


def links(f: Fetcher, url: str, grep: str | None, limit: int = 40) -> None:
    """Ссылки страницы (текст -> абсолютный URL): точный адрес пресс-релиза или
    файла брать отсюда, а не угадывать и не разбирать сырой HTML руками."""
    page = f.get(url)
    print("LINKS route=%s http=%s ok=%s" % (page["route"], page["http"], page["ok"]))
    if not page["ok"]:
        return
    t = decode(page["body"], page.get("ctype", ""))
    n, seen = 0, set()
    for m in re.finditer(r"(?is)<a\b[^>]*?href\s*=\s*[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", t):
        href = urljoin(url, html.unescape(m.group(1)).strip())
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        title = re.search(r"title\s*=\s*[\"']([^\"']+)", m.group(0))
        if not text and title:
            text = html.unescape(title.group(1))
        if grep and not re.search(grep, text + " " + href, re.I):
            continue
        if href in seen:        # картинка и заголовок новости ведут на один адрес
            continue
        seen.add(href)
        print("LINK %s -> %s" % (text[:100] or "-", href))
        n += 1
        if n >= limit:
            break
    print("LINKS shown=%d" % n)


def show(f: Fetcher, url: str, grep: str | None, width: int = 300, limit: int = 12) -> None:
    """Текст страницы ровно в том виде, в каком его увидит сверка: цитату для
    evidence брать отсюда, а не из WebFetch (другой маршрут, другая разметка)."""
    page = f.get(url)
    print("SHOW route=%s http=%s ok=%s tries=%s" % (page["route"], page["http"], page["ok"], "; ".join(page["tries"])))
    if not page["ok"]:
        return
    text, kind = extract(page["body"], page.get("ctype", ""))
    if text is None:
        print("SHOW kind=%s: text not extractable" % kind)
        return
    t = re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()
    print("SHOW kind=%s chars=%d" % (kind, len(t)))
    if not grep:
        print(t[:6000])
        return
    hits = list(re.finditer(grep, t, re.I))
    print("SHOW grep=%r hits=%d" % (grep, len(hits)))
    for m in hits[:limit]:
        a, b = max(0, m.start() - width), min(len(t), m.end() + width)
        print("--- @%d\n%s" % (m.start(), t[a:b]))


def probe(f: Fetcher, urls: list[str]) -> None:
    """Доступность источников с этой машины (пилот: сравнить с этапом 0 сервера)."""
    print("PROBE proxy=%s" % ("yes" if f.proxy else "no"))
    for u in urls:
        page = f.get(u)
        kind = sniff(page["body"], page.get("ctype", "")) if page["ok"] else "-"
        print("PROBE %-30s ok=%-5s route=%-6s http=%-3s kind=%-5s bytes=%-8d %s" % (
            (urlsplit(u).hostname or "")[:30], page["ok"], page["route"], page["http"], kind,
            len(page["body"]), "; ".join(page["tries"])))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="macro layer: verify numbers against source pages")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--candidates", help="candidates.json (merge payload + evidence)")
    mode.add_argument("--show", metavar="URL", help="print the page text as the verifier sees it")
    mode.add_argument("--probe", nargs="+", metavar="URL", help="reachability table")
    ap.add_argument("--grep", help="--show: regex, print windows around matches (with --links: filter links)")
    ap.add_argument("--links", action="store_true", help="--show: list the page links instead of its text")
    ap.add_argument("--out-dir", default="work")
    ap.add_argument("--cache-dir", help="page cache (default <out-dir>/pages)")
    ap.add_argument("--offline", action="store_true", help="only cached pages (tests, re-runs)")
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    proxy = (os.environ.get("MACRO_PROXY") or "").strip() or None
    if proxy and not re.match(r"^(https?|socks5h?)://", proxy):
        print("VERIFY: MACRO_PROXY ignored (expected http(s)://[user:pass@]host:port)")
        proxy = None
    f = Fetcher(Path(a.cache_dir) if a.cache_dir else out / "pages", proxy, a.offline)
    if a.show:
        (links if a.links else show)(f, a.show, a.grep)
        return 0
    if a.probe:
        probe(f, a.probe)
        return 0
    cands = json.loads(Path(a.candidates).read_text("utf-8"))
    verified, pending, report = run(cands, f)
    for name, obj in (("verified.json", verified), ("pending.json", pending), ("verify_report.json", report)):
        (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), "utf-8")
    ok = sum(v for k, v in report["counts"].items() if k in OK_VERDICTS)
    print("VERIFY_STATS items=%d ok=%d %s proxy=%s" % (
        len(report["items"]), ok,
        " ".join("%s=%d" % kv for kv in sorted(report["counts"].items())), "yes" if proxy else "no"))
    for h, e in sorted(report["hosts"].items()):
        print("VERIFY_HOST %-28s items=%d direct=%d proxy=%d unreachable=%d" % (
            h, e["items"], e["direct"], e["proxy"], e["unreachable"]))
    for r in report["items"]:
        if r["verdict"] not in OK_VERDICTS:
            print("  x %-10s %-28s %s %s" % (r["segment"][:10], (r["topic"] or "")[:28], r["verdict"], r["detail"][:90]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
