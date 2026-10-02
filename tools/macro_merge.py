#!/usr/bin/env python3
"""
macro_merge.py — штатный merge industry_cache для профиля macro.md.

До v6.62 обёртка снимала боевой merge-гейт `_macro_duplicate`: он бил и по
самому макро-профилю (на посеве не проходили повторное вливание `vat_rate` и
`contribution_base_2026`). С v6.62 «macro-pull» боевой модуль сам не применяет
этот гейт к `macro.md` (`_validate_fact(f, profile)`), и обёртка больше ничего
не подменяет. Она:
  - требует модуль не старше v6.62 (есть `MACRO_PROFILE`) — со старой копией
    merge молча отбил бы сквозные величины, поэтому падает громко;
  - вливает каналом `routine` — так факт, перепроверенный рутиной, отличим от
    посева (`deep_research`).

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


def require_v662() -> None:
    """Модуль старше v6.62 бил бы гейтом макро-дублей по macro.md — не вливать."""
    if getattr(ic, "MACRO_PROFILE", None) != PROFILE or "routine" not in getattr(ic, "CHANNELS", ()):
        raise SystemExit("MACRO_MERGE FAIL: tools/industry_cache.py is older than v6.62 "
                         "(no MACRO_PROFILE / channel routine) - update the copy, do not merge")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="merge verified facts into macro/macro.json")
    ap.add_argument("--verified", required=True, help="verified.json from verify_sources.py")
    ap.add_argument("--macro-dir", required=True, help="directory with macro.json (cache dir)")
    ap.add_argument("--dossier")
    ap.add_argument("--now")
    a = ap.parse_args(argv)
    require_v662()
    args = ["--merge", a.verified, "--profile", PROFILE, "--cache-dir", a.macro_dir,
            "--channel", "routine"]
    if a.dossier:
        args += ["--dossier", a.dossier]
    if a.now:
        args += ["--now", a.now]
    return ic.main(args)


if __name__ == "__main__":
    sys.exit(main())
