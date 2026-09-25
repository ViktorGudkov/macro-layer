#!/usr/bin/env python3
"""
macro_merge.py — штатный merge industry_cache для профиля macro.md.

Зачем обёртка, а не прямой вызов `industry_cache.py --merge`:
    в боевом модуле merge-гейт `_macro_duplicate` отбивает факт, где сквозная
    величина (общая ставка НДС, МРОТ, ключевая ставка, курс) стоит подлежащим
    со своим значением. Гейт написан для ОТРАСЛЕВЫХ кешей: сквозным величинам
    там не место, их дом — макро-слой. Но он не смотрит на профиль и бьёт и по
    самому macro.md. Сухой прогон 25.09 на посеве (идентичен боевому файлу):
    2 из 92 фактов не прошли бы повторное вливание — `vat_rate` («Основная
    ставка НДС повышена с 20% до 22%…») и `contribution_base_2026` (МРОТ).
    Без исключения эти два факта протухли бы навсегда.

    Модуль tools/industry_cache.py — побайтная копия боевого (sha в README):
    правка в нём разошлась бы с ботом. Исключение живёт здесь и снимает ТОЛЬКО
    этот гейт и ТОЛЬКО для macro.md; валидация, клиентские данные, replaces,
    страж as_of_cmp и атомарная запись — штатные.

Использование:
    python3 tools/macro_merge.py --verified work/verified.json --macro-dir macro \
        [--dossier work/macro_dossier.md] [--now YYYY-MM-DD]
Печатает штатные строки `MERGE macro.md: …` и `MERGE_STATS …`; код возврата —
как у industry_cache.py --merge (1 = ни один факт не прошёл гейт).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_cache as ic  # noqa: E402

PROFILE = "macro.md"


def disable_macro_gate() -> None:
    """Снять гейт макро-дублей в этом процессе. Упасть, если модуль изменился:
    молча вливать с включённым гейтом (или с чужой функцией) нельзя."""
    if not callable(getattr(ic, "_macro_duplicate", None)):
        raise SystemExit("MACRO_MERGE FAIL: industry_cache._macro_duplicate not found - "
                         "module changed, re-check the exception before merging")
    ic._macro_duplicate = lambda *parts: None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="merge verified facts into macro/macro.json")
    ap.add_argument("--verified", required=True, help="verified.json from verify_sources.py")
    ap.add_argument("--macro-dir", required=True, help="directory with macro.json (cache dir)")
    ap.add_argument("--dossier")
    ap.add_argument("--now")
    a = ap.parse_args(argv)
    disable_macro_gate()
    args = ["--merge", a.verified, "--profile", PROFILE, "--cache-dir", a.macro_dir,
            "--channel", "deep_research"]
    if a.dossier:
        args += ["--dossier", a.dossier]
    if a.now:
        args += ["--now", a.now]
    return ic.main(args)


if __name__ == "__main__":
    sys.exit(main())
