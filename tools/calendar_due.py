#!/usr/bin/env python3
"""
calendar_due.py — какие рецепты reg_calendar проверять в этот прогон.

Зачем скрипт, а не правило в промпте: поле `next_event` у рецептов в основном
текст («Октябрь — ноябрь 2026: постановление…», «осень 2026», «проверять
ежемесячно»). Пилот 25.09 трактовал окна расширительно — «окно уже идёт =
наступило» — и набрал 18 «наступивших» из 32; сам агент предупредил, что от
прогона к прогону это будет плавать. Отбор должен быть одинаковым при
одинаковом файле и дате.

Смысл `as_of` рецепта — дата последней проверки. Правила:
    дата     в тексте есть дата события d (самая ранняя позже as_of):
             проверять, когда d ≤ сегодня + 7 дней;
             (признаки не исключают друг друга: «2026-12-31, решение — в IV
             квартале» срабатывает по окну раньше, чем по дате)
    окно     месяцы/сезон/квартал с годом: проверять, когда окно началось
             (или начнётся за 7 дней) и с прошлой проверки прошло ≥ 28 дней;
    регулярно «еженедельно» ≥ 6 дней, «ежемесячно» и «при каждом …» ≥ 28,
             «ежеквартально» ≥ 85;
    прочее   (текст не разобран, «не объявлено») — раз в 28 дней.
Порядок: даты, окна, регулярные, прочее; внутри — давно не проверенные
первыми. Кап — 8 за прогон; остальное — в следующие недели.

Использование:
    python3 tools/calendar_due.py --macro macro/macro.json --today YYYY-MM-DD [--cap 8] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

CAP = 8
HORIZON = 7
WINDOW_EVERY = 28
UNPARSED_EVERY = 28
REGULAR = [(r"еженедельн|каждую неделю|по средам|раз в неделю", 6),
           (r"ежекварт|раз в квартал", 85),
           (r"ежемесячн|каждый месяц|раз в месяц|при каждом|перед любым|несколько раз в год|"
            r"в течение года|без фиксированной даты", 28)]
_MON = {"январ": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5, "июн": 6, "июл": 7,
        "август": 8, "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12}
# граница слова обязательна: без неё «принимается» даёт «май»
_MON_RE = (r"(?<![а-яё])(январ\w*|феврал\w*|март\w*|апрел\w*|ма[йяе](?![а-яё])|мая|июн\w*|июл\w*|"
           r"август\w*|сентябр\w*|октябр\w*|ноябр\w*|декабр\w*)")
_SEASON = {"зим": (12, 2), "весн": (3, 5), "лет": (6, 8), "осен": (9, 11)}
_QUARTER = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "1": 1, "2": 2, "3": 3, "4": 4}


def _mon(word: str) -> int:
    w = word.lower()
    for k in sorted(_MON, key=len, reverse=True):
        if w.startswith(k):
            return _MON[k]
    raise ValueError(word)


def _day(s: str) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _month_end(y: int, m: int) -> date:
    return (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))


def parse(text: str) -> dict:
    """{'dates': [date], 'window': (start, end) | None, 'every': int | None}."""
    t = (text or "").lower().replace(" ", " ")
    dates = []
    for y, m, d in re.findall(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", t):
        dates.append(date(int(y), int(m), int(d)))
    for d, m, y in re.findall(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)", t):
        dates.append(date(int(y), int(m), int(d)))
    for d, mw, y in re.findall(r"(?<!\d)(\d{1,2})\s+" + _MON_RE + r"\s+(\d{4})", t):
        try:
            dates.append(date(int(y), _mon(mw), int(d)))
        except ValueError:
            pass
    window = None
    rest = re.sub(r"(?<!\d)(\d{1,2})\s+" + _MON_RE + r"\s+(\d{4})", " ", t)
    # первая фраза «месяц [— месяц] год»: месяцы в скобках («данные за
    # январь–август») к окну события не относятся
    m = re.search(_MON_RE + r"(?:\s*[—–-]\s*" + _MON_RE + r")?\s+(20\d{2})", rest)
    if m:
        y, a = int(m.group(3)), _mon(m.group(1))
        b = _mon(m.group(2)) if m.group(2) else a
        window = (date(y, a, 1), _month_end(y if b >= a else y + 1, b))
    else:
        m = re.search(r"\b(iv|iii|ii|i|[1-4])\s*(?:-?й\s*)?квартал\w*\s*(20\d{2})", rest)
        if m:
            q, y = _QUARTER[m.group(1)], int(m.group(2))
            window = (date(y, 3 * q - 2, 1), _month_end(y, 3 * q))
        else:
            for k, (a, b) in _SEASON.items():
                m = re.search(k + r"\w*\s+(20\d{2})", rest)
                if m:
                    y = int(m.group(1))
                    window = (date(y, a, 1), _month_end(y + (b < a), b))
                    break
    every = None
    for rx, days in REGULAR:
        if re.search(rx, t):
            every = days
            break
    return {"dates": sorted(set(dates)), "window": window, "every": every}


def due(recipes: list[dict], today: date, cap: int = CAP) -> tuple[list[dict], list[dict]]:
    """(к проверке, отложенные) — каждый элемент: index, name, kind, reason, age."""
    picked, skipped = [], []
    for i, r in enumerate(recipes):
        checked = _day(r.get("as_of") or "")
        age = (today - checked).days if checked else 10 ** 4
        p = parse(r.get("next_event") or "")
        after = [d for d in p["dates"] if checked is None or d > checked]
        row = {"index": i, "name": r.get("name", ""), "age": age}
        hits, notes = [], []   # рецепт срабатывает по ЛЮБОМУ признаку
        if after:
            d = after[0]
            (hits if d <= today + timedelta(days=HORIZON) else notes).append(
                (0, d.isoformat(), "event date %s" % d))
        if p["window"]:
            a, b = p["window"]
            ok = a <= today + timedelta(days=HORIZON) and age >= WINDOW_EVERY
            (hits if ok else notes).append((1, -age, "window %s..%s, checked %s days ago" % (a, b, age)))
        if p["every"]:
            (hits if age >= p["every"] else notes).append(
                (2, -age, "every %s days, checked %s days ago" % (p["every"], age)))
        if not (after or p["window"] or p["every"]):
            (hits if age >= UNPARSED_EVERY else notes).append(
                (3, -age, "no date in text, checked %s days ago" % age))
        if hits:
            rank, key, why = min(hits, key=lambda h: h[0])
            picked.append(dict(row, rank=rank, key=key, reason=why))
        else:
            skipped.append(dict(row, reason="; ".join(n[2] for n in notes) or "past event already checked"))
    picked.sort(key=lambda x: (x["rank"], str(x["key"]) if x["rank"] == 0 else x["key"]))
    over = picked[cap:]
    for x in over:
        x["reason"] += " (over cap %d)" % cap
    return picked[:cap], skipped + over


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="reg_calendar recipes due this run")
    ap.add_argument("--macro", required=True)
    ap.add_argument("--today", required=True, help="YYYY-MM-DD (Moscow)")
    ap.add_argument("--cap", type=int, default=CAP)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    recipes = json.loads(Path(a.macro).read_text("utf-8")).get("reg_calendar") or []
    today = _day(a.today)
    if today is None:
        print("CALENDAR FAIL: --today must be YYYY-MM-DD")
        return 2
    pick, rest = due(recipes, today, a.cap)
    if a.json:
        print(json.dumps({"due": pick, "skipped": rest}, ensure_ascii=False, indent=1, default=str))
        return 0
    print("CALENDAR_DUE due=%d skipped=%d cap=%d" % (len(pick), len(rest), a.cap))
    for x in pick:
        print("  DUE [%d] %s — %s" % (x["index"], x["name"][:70], x["reason"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
