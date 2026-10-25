#!/usr/bin/env python3
"""
seed_due.py — какие факты посева сверить в этот прогон (сверх очереди протухших).

Зачем: посев (срез 20.08.2026) собран ручной волной deep research до появления
сверки цитатой, а очередь `industry_cache --status` берёт факт только по сроку
годности (`harvested` + TTL). Годовые факты посева протухли бы все разом 18.11.2026
и до тех пор шли бы потребителям с пометкой «не сверен цитатой» (справка отчёта
по облигациям, 19–25.10.2026: закон о бюджете с дефицитом 3 786,4 млрд). Очередь
считает модуль-копия бота «macro-pull»; бот закрыт (25.10.2026), но модуль не
трогаем — отбор посева отдельным скриптом, как `calendar_due.py`.

Посев — факт с `harvested` не позже SEED_DATE (перепроверка рутиной ставит дату
прогона). Не берутся:
    отрицательные     `value` «нет данных»: сверка их не подтверждает никогда
                      (NEGATIVE), снимает их только найденный документ;
    в очереди         `id` уже в `stale_queue` этого прогона (status.json);
    уже пробовали     `id` стоит в `replaces` кандидата из прошлых
                      `runs/*/pending.json` — не подтвердился (страница
                      недоступна, цитаты нет); дальше факт ждёт обычного срока,
                      а не крутится каждую неделю.
Порядок: разделы, которые идут в справку отчёта по облигациям (ДКП, бюджет,
финансирование), затем остальные; внутри раздела — по `topic`. Кап — 20 за прогон.

Использование:
    python3 tools/seed_due.py --macro macro/macro.json [--status $R/status.json]
        [--runs-dir runs] [--cap 20] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from verify_sources import NEGATIVE_RE, norm  # noqa: E402

SEED_DATE = "2026-08-20"
CAP = 20
SEGMENT_ORDER = ("dkp", "byudzhet", "finansirovanie", "nalogi", "trud", "podderzhka", "vneshtorg")


def _day(s) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def tried_ids(runs_dir: Path) -> set[str]:
    """`replaces` кандидатов, оставшихся в pending прошлых прогонов."""
    ids: set[str] = set()
    for p in sorted(runs_dir.glob("*/pending.json")):
        try:
            data = json.loads(p.read_text("utf-8"))
        except (OSError, ValueError):
            continue
        for facts in (data.get("segments") or {}).values():
            for f in facts or []:
                r = f.get("replaces") or []
                ids |= {r} if isinstance(r, str) else set(map(str, r))
    return ids


def due(macro: dict, queued: set[str] = frozenset(), tried: set[str] = frozenset(),
        cap: int = CAP) -> tuple[list[dict], list[dict]]:
    """(к сверке, отложенные) — элементы: id, segment, topic, claim, value, as_of, reason."""
    seed = _day(SEED_DATE)
    picked, skipped = [], []
    for seg, facts in (macro.get("segments") or {}).items():
        for f in facts or []:
            h = _day(f.get("harvested") or "")
            if h and h > seed:
                continue
            row = {"id": f.get("id"), "segment": seg, "topic": f.get("topic", ""),
                   "claim": f.get("claim", ""), "value": f.get("value", ""),
                   "as_of": f.get("as_of"), "cadence": f.get("cadence")}
            if NEGATIVE_RE.match(norm(str(f.get("value") or ""))):
                skipped.append(dict(row, reason="negative value"))
            elif row["id"] in queued:
                skipped.append(dict(row, reason="already in stale_queue"))
            elif row["id"] in tried:
                skipped.append(dict(row, reason="tried before, left in pending"))
            else:
                picked.append(dict(row, reason="seed %s" % (f.get("harvested") or "no harvested")))
    rank = {s: i for i, s in enumerate(SEGMENT_ORDER)}
    picked.sort(key=lambda x: (rank.get(x["segment"], len(rank)), x["segment"], x["topic"], str(x["id"])))
    over = picked[cap:]
    for x in over:
        x["reason"] += " (over cap %d)" % cap
    return picked[:cap], skipped + over


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="seed facts to verify this run")
    ap.add_argument("--macro", required=True)
    ap.add_argument("--status", help="status.json этого прогона (stale_queue)")
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--cap", type=int, default=CAP)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    macro = json.loads(Path(a.macro).read_text("utf-8"))
    queued: set[str] = set()
    if a.status:
        st = json.loads(Path(a.status).read_text("utf-8"))
        queued = {str(q.get("id")) for q in st.get("stale_queue") or []}
    pick, rest = due(macro, queued, tried_ids(Path(a.runs_dir)), a.cap)
    if a.json:
        print(json.dumps({"due": pick, "skipped": rest}, ensure_ascii=False, indent=1))
        return 0
    left = sum(1 for x in rest if "over cap" in x["reason"])
    print("SEED_DUE due=%d left=%d skipped=%d cap=%d" % (len(pick), left, len(rest) - left, a.cap))
    for x in pick:
        print("  DUE %s [%s] %s — %s" % (x["id"], x["segment"], x["topic"], x["claim"][:70]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
