#!/usr/bin/env python3
"""
macro_merge.py — штатный merge industry_cache для профиля macro.md.

Гейт макро-дублей `_macro_duplicate` к `macro.md` не применяется
(`_validate_fact(f, profile)`), обёртка ничего не подменяет: вливает каналом
`routine` — так факт, перепроверенный рутиной, отличим от посева
(`deep_research`).

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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="merge verified facts into macro/macro.json")
    ap.add_argument("--verified", required=True, help="verified.json from verify_sources.py")
    ap.add_argument("--macro-dir", required=True, help="directory with macro.json (cache dir)")
    ap.add_argument("--dossier")
    ap.add_argument("--now")
    a = ap.parse_args(argv)
    args = ["--merge", a.verified, "--profile", PROFILE, "--cache-dir", a.macro_dir,
            "--channel", "routine"]
    if a.dossier:
        args += ["--dossier", a.dossier]
    if a.now:
        args += ["--now", a.now]
    return ic.main(args)


if __name__ == "__main__":
    sys.exit(main())
