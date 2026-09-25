#!/usr/bin/env python3
"""
industry_cache.py — кеш отраслевого слоя (v6.21, дизайн industry-cache-proposal.md).

Зачем модуль:
    Отраслевой слой (объём рынка, тренды, регуляторный календарь, бенчмарки)
    пересобирался с нуля КАЖДЫЙ прогон брифа — осцилляция §3 между брифами
    одной отрасли и ~половина бюджета market-агента (10–12 вызовов) на факты,
    не зависящие от клиента. Кеш делает отраслевой слой таким же
    детерминированным входом, как perimeter.json и lens_<ИНН>.json.

Два канала наполнения:
    A — deep research (глубокий слой; вручную, релизными пакетами);
    B — жатва market-агента (фолбэк на MISSING/PARTIAL, через --merge).

Правила (согласованы 19.08.2026):
    - weekly-величины (пошлина, биржевые цены) НЕ кешируются как факты —
      в артефакте живут только рецепты запросов (reg_calendar) + last_value
      для сверки; агент перезапрашивает их КАЖДЫЙ прогон;
    - TTL по классам: fast 7 дн, slow 30 дн, annual 90 дн (от даты жатвы
      класса, не от даты публикации источника);
    - протухание → ДЕЛЬТА-жатва: пережинаются только протухшие классы
      (вердикт PARTIAL); протухли ВСЕ объявленные → STALE_ALL (полная жатва);
    - 🔴 профиль, чьё имя начинается с `_`, — НЕ отрасль, а режим работы, и
      кеша у него нет вовсе (v6.22.2, см. is_cacheable): статус всегда MISSING,
      merge отказывает. Сейчас это `_generic.md`;
    - профиль может объявить подмножество классов полем `cadence_classes`
      (v6.22, для macro.md — без fast). Объявление ЯВНОЕ: выводить «класса
      нет» из «фактов этой каденции ноль» нельзя — у отраслей класс бывает
      пуст просто потому, что жатва его не дала, и такой вывод выдал бы
      FRESH за недожатый кеш. Без поля судим по всем трём, как раньше;
    - 🔴 в артефакте НЕТ клиентских данных: ни chat_id, ни ИНН эмитента —
      кеш глобальный и читается всеми пользователями бота; merge-гейт
      это проверяет (см. _client_data_leak);
    - 🔴 в артефакте НЕТ макро-дублей: сквозные величины (ключевая ставка,
      общая ставка НДС, МРОТ, курс валют) живут в макро-слое, и merge их
      отбивает (v6.22.3, см. _macro_duplicate). Гейт узкий: факт, который
      величину лишь УПОМИНАЕТ, — отраслевой и проходит;
    - merge-гейт: факт без источника/даты не входит и НЕ затирает старое;
      запись атомарная (tmp + os.replace) — гонка прогонов даёт
      last-write-wins на валидном JSON, а не битый файл;
    - нарративное досье <profile>_dossier.md — кап 20 КБ; числа в бриф
      берутся ТОЛЬКО из JSON, досье — фон для связности §3.

Схема v2 (v6.61, docs/LOGIC-2026-09-24-cache-fact-freshness.md):
    - 🔴 свежесть принадлежит ФАКТУ, а не классу: у каждого факта свои
      `id` (адрес для replaces), `harvested` (когда собран/перепроверен —
      НЕ as_of) и `channel`. До v6.61 merge штамповал `harvested[класс]`, и
      один принесённый факт «омолаживал» весь класс; вместе с ключом замены,
      который не совпадал никогда (0 замен на 118 боевых вливаний
      27.08–22.09), в кеше жили пары «старое / новое значение», обе «свежие»;
    - merge ЗАМЕНЯЕТ: по явному `replaces: [id]`, запасной путь — по теме,
      только в слаговом профиле и только если в теме был ровно один факт
      (в рубриках apk/retail/development тема — не адрес факта); новый факт
      старее заменяемого по as_of — отклоняется; заменённое удаляется;
    - блок PARTIAL печатает очередь протухших фактов с id (кап QUEUE_CAP,
      fast → slow → annual, старейшие первыми), а не простыню тем;
    - finalize читает не сырой кеш, а выборку --view (действующие факты,
      протухшие отдельным блоком);
    - файл v1 поднимается до v2 В ПАМЯТИ при чтении (факт получает дату
      своего класса); на диск пишут только merge и cache_migrate_v2.py.

v6.62 «macro-pull»: макро-профиль `macro.md` — свой случай (гейт макро-дублей
к нему не применяется, у выборки свои правила и строка «макро-слой: …»);
необязательное поле `status` у факта (проект / принят / вступил / истёк);
канал `routine` — факт перепроверен облачной рутиной репозитория данных.

Использование:
    python3 industry_cache.py --status --profile apk.md --cache-dir <dir> [--json]
    python3 industry_cache.py --merge <facts.json> --profile apk.md --cache-dir <dir> \
        [--channel market_agent|deep_research|routine] [--dossier file.md]
    python3 industry_cache.py --invalidate --profile apk.md --cache-dir <dir>
    python3 industry_cache.py --view --profile apk.md --cache-dir <dir> --out <view.json>

Выход --status (маркер для оркестрации, читается глазами и грепом):
    ICACHE_STATUS: FRESH|PARTIAL|STALE_ALL|MISSING profile=<p> ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

SCHEMA_VERSION = 2
QUEUE_CAP = 15            # фактов в очереди блока PARTIAL (решение 25.09)
CHANNELS = ("deep_research", "market_agent", "routine", "unknown")   # routine — облачная рутина макро-слоя (v6.62)
MACRO_PROFILE = "macro.md"
# Статус нормы у факта (v6.62, необязательное поле): до v6.62 жил только словами
# в claim, а merge собирал факт из фиксированного набора полей и поле выбрасывал.
FACT_STATUSES = ("проект", "принят", "вступил", "истёк")
_CLS_ORDER = {"fast": 0, "slow": 1, "annual": 2}
TTL_DAYS = {"fast": 7, "slow": 30, "annual": 90}          # weekly не кешируется
CADENCES = {"weekly", "fast", "slow", "annual"}
DOSSIER_CAP_BYTES = 20 * 1024
EPOCH = "1970-01-01"

# Файлы ЧУЖИХ модулей в каталоге кеша (v6.60.2): HTTP-кеш ЕРЗ/ЕИСЖС из
# perimeter_projects.py (`erz_<sha1>.json`, `eiszhs_<sha1>.json`). До v6.60.2
# фолбэк finalize передавал ему --cache-dir …/industry_cache, и cache_digest
# падал трейсбеком на первом же JSON-массиве (боевой каталог 24.09.2026).
# Это не профили: их не считают, не сканируют и не переписывают.
FOREIGN_PREFIXES = ("erz_", "eiszhs_")


def is_foreign_file(name: str) -> bool:
    return name.startswith(FOREIGN_PREFIXES)

FACT_REQUIRED = ("claim", "value", "source", "cadence")
# клиентские данные в глобальном кеше = утечка через изоляционную границу
FORBIDDEN_KEYS = {"chat_id", "inn", "sender_id", "client", "emitent_inn"}
FORBIDDEN_SUBSTR = ("telegram:",)

_DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")

# ---- макро-дубли (v6.22.3) -------------------------------------------------
# Сквозные величины живут в макро-слое (macro_debt.json + macro.json, сегмент
# dkp) и в отраслевой кеш не кладутся: копия расходится с первоисточником и
# протухает не вместе с ним. До v6.22 ключевая ставка лежала в 12 отраслевых
# файлах из 16, и три записали дату РЕШЕНИЯ ЦБ как дату начала действия ставки
# (решение принимается в пятницу, ставка действует со следующего понедельника).
# Запрет был только текстом методички; по мета-закону проекта надёжен лишь
# исполняемый гейт — вот он.
#
# 🔴 Гейт узкий НАМЕРЕННО. Он ловит «голое» утверждение величины и обязан
# пропускать отраслевой факт, который её лишь УПОМИНАЕТ («спрос развернётся при
# ставке ниже 12%», «программа 1764: ключевая ставка минус 3,5 п.п.», «льгота по
# НДС для медизделий»). Широкие паттерны macro_dedup.MACRO_PATTERNS для двери не
# годятся: замер 20.08.2026 по боевому кешу дал ими 80 кандидатов на 2045
# фактов, из них настоящих дублей полтора — остальное «нефтегазовые доходы
# федерального бюджета», «медицинская инфляция», «страховые взносы
# ИТ-компаний», то есть отраслевые факты своих же профилей. Поэтому в
# macro_dedup решение принимает человек (--report/--apply), а на двери стоят
# три условия СРАЗУ:
#   1) величина названа в форме «величина + её значение»;
#   2) она стоит ПОДЛЕЖАЩИМ — в начале claim или сразу после «.», «;», «:»;
#   3) между границей и величиной нет ни букв, ни цифр (кавычки, тире и
#      разметка допустимы). Любое слово перед ней в том же предложении («при»,
#      «из-за», «на фоне снижения») делает факт упоминанием и снимает
#      подозрение — отдельный список предлогов для этого не нужен.
# Замер того же кеша этим правилом: 2 срабатывания на 2124 записи, оба —
# настоящие дубли базовой ставки НДС (it.json, reg_calendar remont.json).
#
# Отказ дёшев и обратим: факт остаётся в market_<ИНН>.json и доходит до §3,
# теряется только место в кеше. Поэтому дверь блокирует там, где авто-удаление
# в macro_dedup намеренно запрещено.
_MACRO_NUM = r"\d{1,3}(?:[\u00a0\u202f ]\d{3})*(?:[.,]\d{1,2})?"
# связка «величина → значение»: тире, двоеточие или глагол изменения
_MACRO_LINK = (r"(?:—|–|-|:|составля\w+|повышен\w*|снижен\w*|сохранен\w*|"
               r"установлен\w*|равн\w*|достигл\w*|поднят\w*|опущен\w*)"
               r"(?:\s+(?:до|с|на))?")
MACRO_BARE_PATTERNS = {
    "ключевая ставка": (
        rf"ключев\w+\s+ставк\w+(?:\s+(?:ЦБ(?:\s+РФ)?|Банка\s+России))?\s*"
        rf"{_MACRO_LINK}\s*{_MACRO_NUM}\s*%"),
    # «базовая/основная/общая ставка НДС» — уже сама по себе сквозная величина:
    # отраслевой факт говорит «льгота по НДС», «нулевая ставка НДС для судоремонта»
    "общая ставка НДС": (
        rf"(?:базов\w+|основн\w+|обща\w+|стандартн\w+)\s+ставк\w+\s+НДС|"
        rf"ставк\w+\s+НДС\s*{_MACRO_LINK}\s*{_MACRO_NUM}\s*%"),
    "МРОТ": rf"МРОТ\s*{_MACRO_LINK}\s*{_MACRO_NUM}",
    "курс валют": (rf"(?:официальн\w+\s+)?курс\s+(?:доллара|евро|юаня)\s*"
                   rf"{_MACRO_LINK}\s*{_MACRO_NUM}"),
}
_MACRO_RE = {name: re.compile(pat, re.I)
             for name, pat in MACRO_BARE_PATTERNS.items()}
_CLAUSE_RE = re.compile(r"[.;:]\s+")          # границы предложений и пунктов
_LETTER_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁё]")


# ---------------------------------------------------------------- helpers
def cache_path(cache_dir: str | Path, profile: str) -> Path:
    stem = profile[:-3] if profile.endswith(".md") else profile
    return Path(cache_dir) / f"{stem}.json"


def is_cacheable(profile: str) -> bool:
    """False = профиль не отрасль, кеша у него быть не должно.

    🔴 Кеш ключуется парой (профиль, B-блок) = (отрасль, подотрасль) —
    industry-cache-proposal.md §11.3. `_generic.md` такой парой не является:
    блоков `## B.` у неё НОЛЬ, и по собственному тексту это режим работы
    («линза НЕ заменяет профиль»), а не отрасль. Ключ по имени профиля делал её
    файл ОБЩИМ для всех отраслей без профиля.

    Замер 20.08.2026 (боевой кеш): в `_generic.json` лежали 6 фактов
    фармдистрибуции (ОКВЭД 46.46), 3 оптовой торговли и 1 про методологию
    рейтингов — вердикт FRESH. Следующий бриф оптовика металлопроката получил бы
    «ОТРАСЛЕВОЙ СЛОЙ ГОТОВ», пропустил собственный рыночный ресёрч и собрал §3
    из фактов чужой отрасли. Это утечка ЧЕРЕЗ ОТРАСЛЬ, а не через клиента:
    merge-гейт ищет chat_id/ИНН и такой факт пропускает законно — факт честный,
    просто не из той отрасли. Содержимым такую утечку не отличить; ловится
    только тем, что пространство имён что-то означает.

    Правило по имени, а не список: ведущее `_` в имени файла профиля уже
    означает «не отрасль». `macro.md` под правило не подпадает — это сквозной
    слой с объявленными сегментами, он кешируется как раньше.
    """
    stem = profile[:-3] if profile.endswith(".md") else profile
    return not stem.startswith("_")


def declared_classes(art: dict) -> list[str]:
    """Классы TTL, которые профиль реально использует.

    По умолчанию — все три. Профиль может объявить подмножество полем
    `cadence_classes`: macro.md не имеет класса fast, потому что всё
    быстроживущее (ставка, инфляция, курс, доходности) лежит рецептами в
    reg_calendar, а не фактами. Без объявления класс без клейма неотличим
    от протухшего, и вердикт вечно PARTIAL со списком тем на пережатие «—».
    Объявление ЯВНОЕ, а не выведенное из «фактов этой каденции нет»: у
    отраслей класс бывает пуст просто потому, что жатва его не дала, и
    догадка выдала бы FRESH за недожатый кеш.
    """
    decl = art.get("cadence_classes")
    if not isinstance(decl, list) or not decl:
        return list(TTL_DAYS)
    used = [c for c in TTL_DAYS if c in decl]
    return used or list(TTL_DAYS)


def dossier_path(cache_dir: str | Path, profile: str) -> Path:
    stem = profile[:-3] if profile.endswith(".md") else profile
    return Path(cache_dir) / f"{stem}_dossier.md"


def _parse_day(s: str) -> date:
    """YYYY[-MM[-DD]] → date; неполные даты консервативно к началу периода."""
    parts = (s or EPOCH).split("-")
    y = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 1
    d = int(parts[2]) if len(parts) > 2 else 1
    return date(y, m, d)


def as_of_cmp(a: str | None, b: str | None) -> int:
    """Сравнение дат данных на ОБЩЕЙ точности: -1 / 0 / 1.

    🔴 Агент пишет as_of месяцем («2026-07»), deep research — днём
    («2026-07-10»). Сравнение через _parse_day делало «июль» 1-м числом, и
    перепроверка тех же июльских данных выглядела СТАРШЕ факта эталона: страж
    даты отклонял её, а миграция оставляла старый факт (сухой прогон на боевом
    кеше 25.09: 10 таких пар в it/himiya/lpk/metallurgiya). На общей точности
    «2026-07» и «2026-07-10» равны.
    """
    pa = [int(x) for x in (a or EPOCH).split("-")]
    pb = [int(x) for x in (b or EPOCH).split("-")]
    k = min(len(pa), len(pb))
    return (pa[:k] > pb[:k]) - (pa[:k] < pb[:k])


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def fact_id(profile: str, topic: str, claim: str) -> str:
    """Адрес факта для `replaces`: выдаётся при записи и дальше не меняется."""
    stem = profile[:-3] if profile.endswith(".md") else profile
    return hashlib.sha1(f"{stem}|{topic or ''}|{claim or ''}".encode("utf-8")).hexdigest()[:8]


def iter_facts(art: dict | None):
    """(сегмент, индекс, факт) по всему артефакту."""
    for seg, items in ((art or {}).get("segments") or {}).items():
        for i, f in enumerate(items or []):
            if isinstance(f, dict):
                yield seg, i, f


def upgrade(art: dict, profile: str) -> dict:
    """v1 → v2 В ПАМЯТИ: у каждого факта свои id / harvested / channel.

    Факт v1 получает дату СВОЕГО класса — ровно то, что утверждал v1, без
    новой лжи; честные даты по эталону 20.08 ставит cache_migrate_v2.py.
    На диск здесь не пишется ничего: status и cache_digest обязаны остаться
    read-only (инвариант v6.28, закреплён тестом по sha файлов).
    """
    cls_dates = art.get("harvested") or {}
    file_ch = art.get("harvest_channel")
    for _, _, f in iter_facts(art):
        if not f.get("harvested"):
            f["harvested"] = cls_dates.get(f.get("cadence")) or EPOCH
        if not f.get("channel"):
            f["channel"] = file_ch if file_ch in CHANNELS else "unknown"
        if not f.get("id"):
            f["id"] = fact_id(profile, f.get("topic", ""), f.get("claim", ""))
    return art


def is_stale(f: dict, now: date) -> bool:
    ttl = TTL_DAYS.get(f.get("cadence"))
    return ttl is not None and (now - _parse_day(f.get("harvested") or EPOCH)).days > ttl


def expiry(f: dict) -> date:
    """Первый протухший день факта: порог строгий (`> ttl`)."""
    return _parse_day(f.get("harvested") or EPOCH) + timedelta(days=TTL_DAYS[f["cadence"]] + 1)


def derive(art: dict) -> dict:
    """Поля уровня файла — ПРОИЗВОДНЫЕ от фактов (для [ICACHE] и старых читателей).

    `harvested[класс]` = последняя перепроверка факта этого класса;
    `harvest_channel` = канал большинства фактов. До v6.61 оба поля
    переписывались вслепую при каждом merge (дефекты 5.1 и 5.2 хендоффа 20.08).
    """
    per_cls: dict[str, str] = {}
    chans: Counter = Counter()
    for _, _, f in iter_facts(art):
        c, h = f.get("cadence"), f.get("harvested")
        if c in TTL_DAYS and h and (c not in per_cls or h > per_cls[c]):
            per_cls[c] = h
        chans[f.get("channel") or "unknown"] += 1
    art["harvested"] = {c: per_cls[c] for c in TTL_DAYS if c in per_cls}
    if chans:
        art["harvest_channel"] = chans.most_common(1)[0][0]
    art["schema_version"] = SCHEMA_VERSION
    return art


def topic_convention(art: dict | None) -> str:
    """«slug» — тема служит адресом факта; «rubric» — тема = рубрика с многими фактами.

    Замер копии 20.08: в 13 профилях из 16 ровно один факт на тему; в apk,
    retail и development тема — рубрика (до 15 фактов, разные классы). Порог
    5% тем с несколькими фактами отделяет их с запасом (neftegaz: 1 из 152).
    Пустой профиль — «unknown»: угадывать конвенцию не на чем.
    """
    cnt = Counter(f.get("topic", "") for _, _, f in iter_facts(art))
    if not cnt:
        return "unknown"
    multi = sum(1 for n in cnt.values() if n > 1)
    return "slug" if multi / len(cnt) <= 0.05 else "rubric"


def load(cache_dir: str | Path, profile: str) -> dict | None:
    p = cache_path(cache_dir, profile)
    if not p.is_file():
        return None
    try:
        art = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None  # битый файл = отсутствующий: кеш не должен ронять прогон
    # массив или скаляр — не объект кеша (v6.60.2): .get() на нём ронял status()
    if not isinstance(art, dict):
        return None
    return upgrade(art, profile)


def _client_data_leak(obj) -> str | None:
    """Рекурсивный поиск клиентских данных. Возвращает причину или None."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in FORBIDDEN_KEYS:
                return f"запрещённый ключ «{k}»"
            hit = _client_data_leak(v)
            if hit:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = _client_data_leak(v)
            if hit:
                return hit
    elif isinstance(obj, str):
        for sub in FORBIDDEN_SUBSTR:
            if sub in obj:
                return f"клиентская подстрока «{sub}»"
    return None


def _macro_duplicate(*parts: str) -> str | None:
    """None = чисто; иначе имя сквозной величины, утверждённой «голым» фактом.

    Проверяются claim, value и их склейка «claim — value»: агент иногда кладёт
    величину в claim, а её значение в value, и по отдельности ни то ни другое
    паттерну не отвечает.
    """
    for text in parts:
        text = str(text or "")
        if not text:
            continue
        bounds = [0] + [m.end() for m in _CLAUSE_RE.finditer(text)]
        for name, rx in _MACRO_RE.items():
            for m in rx.finditer(text):
                start = max((b for b in bounds if b <= m.start()), default=0)
                if not _LETTER_RE.search(text[start:m.start()]):
                    return name          # величина стоит подлежащим = дубль
    return None


# ---------------------------------------------------------------- status
_EMPTY_STATUS = {"stale_n": 0, "stale_queue": [], "queue_more": 0, "empty_classes": [],
                 "stale_since": None, "next_expiry": None, "dr_share": None}


def status(cache_dir: str | Path, profile: str, now: date | None = None) -> dict:
    """Вердикт свежести + данные для блока в задачу market-агента.

    v6.61: свежесть считается ПО ФАКТАМ. FRESH — протухших фактов нет и у
    каждого объявленного класса есть хоть один факт; STALE_ALL — протух каждый
    факт (или фактов нет вовсе); иначе PARTIAL. Пустой объявленный класс —
    тоже повод для PARTIAL: профиль, заведённый вливанием одних fast-фактов,
    иначе считался бы FRESH и никогда не добрал бы slow/annual.
    """
    now = now or date.today()
    if not is_cacheable(profile):
        # Файл игнорируется, даже если кто-то положил его руками: вердикт
        # определяется профилем, а не наличием файла. О самом файле сообщит
        # гейт [ICACHE] — он смотрит на диск напрямую.
        return {"verdict": "MISSING", "profile": profile, "not_cacheable": True,
                "stale_classes": list(TTL_DAYS), "fresh_classes": [],
                "harvested": {}, "n_facts": 0, "weekly": [], "stale_topics": [],
                "as_of": None, "dossier": False, **_EMPTY_STATUS}
    art = load(cache_dir, profile)
    if art is None:
        return {"verdict": "MISSING", "profile": profile, "stale_classes": list(TTL_DAYS),
                "fresh_classes": [], "harvested": {}, "n_facts": 0,
                "weekly": [], "stale_topics": [], "as_of": None,
                "dossier": dossier_path(cache_dir, profile).is_file(), **_EMPTY_STATUS}

    used = declared_classes(art)
    facts = [(seg, f) for seg, _, f in iter_facts(art)]
    judged = [(seg, f) for seg, f in facts if f.get("cadence") in used]
    stale = [(seg, f) for seg, f in judged if is_stale(f, now)]
    fresh_f = [f for _, f in judged if not is_stale(f, now)]
    have = {f.get("cadence") for _, f in judged}
    empty = [c for c in used if c not in have]
    stale_cls = {f["cadence"] for _, f in stale} | set(empty)
    stale_classes = [c for c in TTL_DAYS if c in stale_cls]
    fresh_classes = [c for c in used if c not in stale_cls]
    if not judged or len(stale) == len(judged):
        verdict = "STALE_ALL"
    elif stale or empty:
        verdict = "PARTIAL"
    else:
        verdict = "FRESH"

    stale.sort(key=lambda sf: (_CLS_ORDER[sf[1]["cadence"]], sf[1].get("harvested") or EPOCH,
                               sf[1].get("topic", ""), sf[1].get("id", "")))
    queue = [{"id": f.get("id"), "cadence": f["cadence"], "topic": f.get("topic", ""),
              "claim": f.get("claim", ""), "value": f.get("value", ""),
              "as_of": f.get("as_of"), "harvested": f.get("harvested"), "segment": seg}
             for seg, f in stale[:QUEUE_CAP]]
    per_cls = derive(dict(art, segments=art.get("segments")))["harvested"]
    dates = [f.get("harvested") for _, f in facts if f.get("harvested")]
    nxt = min(((expiry(f), f["cadence"]) for f in fresh_f), default=None)
    weekly = [{"name": w.get("name"), "query": w.get("query"),
               "last_value": w.get("last_value"), "as_of": w.get("as_of")}
              for w in art.get("reg_calendar", []) if w.get("cadence") == "weekly"]
    return {"verdict": verdict, "profile": profile, "stale_classes": stale_classes,
            "fresh_classes": fresh_classes, "harvested": per_cls,
            "n_facts": len(facts), "weekly": weekly,
            "stale_topics": sorted({f.get("topic", "?") for _, f in stale}),
            "as_of": max(dates) if dates else None,
            "dossier": dossier_path(cache_dir, profile).is_file(),
            "stale_n": len(stale), "stale_queue": queue,
            "queue_more": max(0, len(stale) - len(queue)), "empty_classes": empty,
            "stale_since": min(expiry(f) for _, f in stale).isoformat() if stale else None,
            "next_expiry": (nxt[1], nxt[0].isoformat()) if nxt else None,
            "dr_share": (sum(1 for _, f in facts if f.get("channel") == "deep_research")
                         / len(facts)) if facts else None,
            "schema_version": art.get("schema_version")}


def _plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def _cut(s: str, k: int) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= k else s[:k - 1] + "…"


def _queue_lines(st: dict) -> list[str]:
    q = st.get("stale_queue") or []
    if not q:
        return []
    out = [f"ОЧЕРЕДЬ ПЕРЕЖАТИЯ ({len(q)} из {st['stale_n']} протухших, по приоритету — "
           f"иди сверху, сколько успеешь):"]
    for it in q:
        out.append(f"  [{it['id']}] {it['cadence']:<6} {it['topic']} | {_cut(it['claim'], 110)} | "
                   f"as_of {it['as_of'] or '—'} | собран {it['harvested']}")
    if st.get("queue_more"):
        out.append(f"  … ещё {st['queue_more']} протухших фактов пережмут следующие брифы.")
    out.append('Пересобранный факт клади в ФАЙЛ 2 с topic ДОСЛОВНО из строки очереди и '
               '"replaces": ["<id>"] — тогда старое значение заменится, а не ляжет рядом. '
               'Новая тема — без replaces, она допишется.')
    return out


def status_block(st: dict) -> str:
    """Человекочитаемый блок для вставки в задачу market-агента (ШАГ 2)."""
    p = st["profile"]
    lines = [f"ICACHE_STATUS: {st['verdict']} profile={p} facts={st['n_facts']} "
             f"as_of={st['as_of'] or '—'} "
             + " ".join(f"{c}@{st['harvested'].get(c) or '—'}" for c in TTL_DAYS)]
    if st.get("not_cacheable"):
        lines.append(
            f"Общая линза {p} НЕ КЕШИРУЕТСЯ (v6.22.2): это методика, а не "
            f"отрасль — подотраслей у неё нет, и один файл на все отрасли без "
            f"профиля разносил бы факты ЧУЖОЙ отрасли по брифам. → ПОЛНАЯ жатва "
            f"КАЖДЫЙ прогон: задачи 1–4 и ВЕСЬ A8 как обычно.\n"
            f"🔴 ФАЙЛ 2 (industry_facts_<ИНН>.json) НЕ собирай и --merge НЕ "
            f"вызывай — гейт откажет, работа пропадёт. Все находки идут в "
            f"market_<ИНН>.json, как до v6.21.\n"
            f"🔴 Строка для finalize: «отраслевой слой: не использован (общая "
            f"линза {p}, слой не кешируется)».")
        return "\n".join(lines)
    if st["verdict"] == "MISSING":
        lines.append(
            f"Отраслевой кеш по {p} ОТСУТСТВУЕТ → полная жатва (канал B): выполняй "
            f"задачи 1–4 и ВЕСЬ A8 как обычно. Отраслевые находки ([О]-запросы, "
            f"задачи 1–4) верни ВТОРЫМ файлом industry_facts.json для --merge.")
        return "\n".join(lines)
    if st["verdict"] == "STALE_ALL":
        lines.append(
            f"Кеш по {p} ПРОТУХ ЦЕЛИКОМ (все факты старше TTL) → полная жатва как "
            f"при MISSING; старые значения кеша используй только для сверки "
            f"расхождений. Отраслевые находки — вторым файлом для --merge.")
        lines += _queue_lines(st)
    elif st["verdict"] == "FRESH":
        lines.append(
            f"ОТРАСЛЕВОЙ СЛОЙ ГОТОВ (кеш {p} @ {st['as_of']}, {st['n_facts']} фактов, "
            f"канал A/B). Задачи 1–4 НЕ выполняй — §3 соберёт finalize из кеша. "
            f"Выполни ТОЛЬКО: (а) [Г]-запросы A8 (про группу); (б) weekly-позиции "
            f"ниже — каждый прогон, с датой расчёта. [О]-запросы A8 засчитай как "
            f"выполненные кешем: маркер «X/Y выполнены (M из кеша {p}@{st['as_of']})». "
            f"ФАЙЛ 2 НЕ собирай: пережимать нечего.")
    else:  # PARTIAL
        empty = st.get("empty_classes") or []
        lines.append(
            f"Кеш {p} @ {st['as_of']} годен ЧАСТИЧНО: протухло {st['stale_n']} "
            f"{_plural(st['stale_n'], 'факт', 'факта', 'фактов')}"
            + (f" (классы {', '.join(c for c in st['stale_classes'] if c not in empty)})"
               if st["stale_n"] else "")
            + (f"; пустые классы {', '.join(empty)} — собери их задачами 1–4, без replaces"
               if empty else "")
            + " → ДЕЛЬТА-жатва по очереди ниже + [Г]-запросы A8 + weekly. Свежие "
              "факты не трогай — их отдаст кеш. Дельта-находки верни вторым файлом "
              "для --merge.")
        lines += _queue_lines(st)
    if st["weekly"]:
        lines.append("WEEKLY (перезапросить СЕЙЧАС, в бриф только с датой расчёта):")
        for w in st["weekly"]:
            lines.append(f"  - {w['name']}: {w['query']} | было: {w['last_value']} "
                         f"(на {w['as_of']})")
    return "\n".join(lines)


# ---------------------------------------------------------------- merge
def _validate_fact(f: dict, profile: str | None = None) -> str | None:
    """None = валиден, иначе причина отказа.

    v6.62: гейт макро-дублей не применяется к самому макро-профилю — сквозные
    величины (общая ставка НДС, МРОТ) живут именно там. До v6.62 гейт бил и
    по macro.md: на посеве не проходили повторное вливание vat_rate и
    contribution_base_2026, репозиторий данных обходил это обёрткой.
    """
    if not isinstance(f, dict):
        return "факт не объект"
    for k in FACT_REQUIRED:
        v = f.get(k)
        if not v or not str(v).strip():
            return f"нет поля «{k}»"
    if f["cadence"] not in CADENCES:
        return f"неизвестная каденция «{f['cadence']}»"
    if f["cadence"] == "weekly":
        return "weekly не кешируется как факт — рецепт запроса в reg_calendar"
    src = str(f["source"]).strip().lower()
    if src in ("н/д", "nd", "n/a", "-", "—"):
        return "источник-заглушка"
    as_of = f.get("as_of") or f.get("pub_date")
    if not as_of or not _DATE_RE.match(str(as_of)):
        return f"нет валидной даты as_of/pub_date (получено: {as_of!r})"
    leak = _client_data_leak(f)
    if leak:
        return leak
    st = f.get("status")
    if st is not None and st not in FACT_STATUSES:
        return f"неизвестный status «{st}» (допустимо: {', '.join(FACT_STATUSES)})"
    dup = None if profile == MACRO_PROFILE else _macro_duplicate(
        f.get("claim"), f.get("value"), f'{f.get("claim") or ""} — {f.get("value") or ""}')
    if dup:
        return (f"макро-дубль «{dup}»: сквозная величина живёт в макро-слое "
                f"(macro_debt.json + macro.json, сегмент dkp) и в отраслевой "
                f"кеш не кладётся — копия расходится с первоисточником и тянет "
                f"дату решения вместо даты действия. Факт, который величину "
                f"лишь УПОМИНАЕТ, гейт пропускает: переформулируй от отрасли "
                f"или оставь находку в market_<ИНН>.json")
    if not f.get("segment"):
        return "нет поля «segment»"
    return None


def merge(cache_dir: str | Path, profile: str, facts: list[dict],
          channel: str = "market_agent", now: date | None = None,
          reg_calendar: list[dict] | None = None,
          cadence_classes: list[str] | None = None) -> dict:
    """Валидация + ЗАМЕНА или дозапись (v6.61) + атомарная запись. Возвращает отчёт.

    Порядок для каждого принятого факта:
      1. тот же факт (тот же id = та же тема и текст) → перепроверка на месте;
      2. `replaces: [id]` и такие id в профиле есть → заменить их;
      3. профиль слаговый (topic_convention), тема была в кеше ДО вливания и в
         ней ровно один факт → заменить его (тема = адрес факта; в рубриках
         apk/retail/development — только по replaces, см. К5 логики);
      4. иначе дописать — в сегмент темы, если тема есть, иначе в свой сегмент.
    Страж даты: новый факт старее заменяемого по as_of → отклоняется.
    Заменённое удаляется (решение 25.09: история не ведётся; копия дельта-факта
    остаётся в briefs/…/industry_facts_*.json). Штамп `harvested` и `channel`
    ставится ТОЛЬКО принятым фактам — класс больше не «омолаживается».
    """
    now = now or date.today()
    if not is_cacheable(profile):
        why = (f"профиль {profile} не отрасль (см. is_cacheable) — кеша у него "
               f"нет: факты одной отрасли ушли бы в брифы всех остальных. "
               f"Находки остаются в market_<ИНН>.json")
        return {"accepted": 0, "rejected": [{"claim": f"<все {len(facts)}>",
                                             "why": why}],
                "refused": why, "classes_touched": [],
                "path": str(cache_path(cache_dir, profile))}
    art = load(cache_dir, profile) or {
        "schema_version": SCHEMA_VERSION, "profile": profile,
        "harvest_channel": channel, "harvested": {}, "reg_calendar": [],
        "segments": {},
    }
    accepted, rejected = [], []
    for f in facts:
        why = _validate_fact(f, profile)
        if why:
            rejected.append({"claim": str(f.get("claim", "?"))[:80], "why": why})
            continue
        accepted.append(f)

    seg_index = art.setdefault("segments", {})
    today = now.isoformat()
    # Кандидаты на замену ПО ТЕМЕ — только из кеша ДО вливания и только в
    # слаговом профиле: иначе второй факт рубрики из того же пакета «однозначно»
    # заменил бы первый (кейс теста v2-rubric-appended).
    convention = topic_convention(art)
    pre_topic_ids: dict[str, list[str]] = defaultdict(list)
    for _, _, old in iter_facts(art):
        pre_topic_ids[old.get("topic", "")].append(old.get("id") or "")
    stats: Counter = Counter()
    unknown_ids: list[str] = []
    applied: list[dict] = []
    for f in accepted:
        clean = {
            "claim": f["claim"], "value": f["value"], "source": f["source"],
            "source_url": f.get("source_url", ""),
            "as_of": f.get("as_of") or f.get("pub_date"),
            "cadence": f["cadence"], "topic": f.get("topic", ""),
        }
        if f.get("status"):
            clean["status"] = f["status"]
        clean["id"] = fact_id(profile, clean["topic"], clean["claim"])
        clean["harvested"] = today
        clean["channel"] = channel if channel in CHANNELS else "unknown"

        by_id: dict[str, tuple[str, int]] = {}
        by_topic: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for seg, i, old in iter_facts(art):
            by_id.setdefault(old.get("id") or "", (seg, i))
            by_topic[old.get("topic", "")].append((seg, i))

        targets: list[tuple[str, int]] = []
        how = ""
        repl = f.get("replaces") or []
        if isinstance(repl, str):
            repl = [repl]
        repl = [str(r).strip() for r in repl if str(r).strip()]
        if clean["id"] in by_id:
            targets, how = [by_id[clean["id"]]], "refreshed"
        elif repl:
            found = list(dict.fromkeys(by_id[r] for r in repl if r in by_id))
            unknown_ids += [r for r in repl if r not in by_id]
            if found:
                targets, how = found, "replaced_by_id"
        pre = pre_topic_ids.get(clean["topic"], [])
        if (not targets and clean["topic"] and convention == "slug" and len(pre) == 1
                and pre[0] in by_id and len(by_topic.get(clean["topic"], [])) == 1):
            targets, how = [by_id[pre[0]]], "replaced_by_topic"

        if targets:
            olds = [seg_index[sg][ix] for sg, ix in targets]
            newer = [o.get("as_of") for o in olds if as_of_cmp(clean["as_of"], o.get("as_of")) < 0]
            if how != "refreshed" and newer:
                stats["older_rejected"] += 1
                rejected.append({"claim": str(clean["claim"])[:80],
                                 "why": f"старее кешевого: as_of {clean['as_of']} < "
                                        f"{newer[0]} — кеш не тронут, находка "
                                        f"остаётся в market_<ИНН>.json"})
                continue
            sg0, ix0 = targets[0]
            seg_index[sg0][ix0] = clean
            for sg, ix in sorted(targets[1:], key=lambda t: (t[0], -t[1])):
                del seg_index[sg][ix]
            stats[how] += 1
        else:
            home = by_topic.get(clean["topic"]) if clean["topic"] else None
            seg_index.setdefault(home[0][0] if home else f["segment"], []).append(clean)
            stats["appended"] += 1
        applied.append(clean)

    # reg_calendar: замена по имени (weekly-рецепты и календарные позиции)
    for rc in (reg_calendar or []):
        leak = _client_data_leak(rc)
        if leak or not rc.get("name") or not rc.get("cadence"):
            rejected.append({"claim": f"reg_calendar:{rc.get('name', '?')}",
                             "why": leak or "нет name/cadence"})
            continue
        # рецепт запроса на сквозную величину — тот же дубль, только weekly:
        # боевой remont.json держал «Базовая ставка НДС 22% с 01.01.2026»
        dup = None if profile == MACRO_PROFILE else _macro_duplicate(
            rc.get("name"), rc.get("last_value"), f'{rc.get("name") or ""} — {rc.get("last_value") or ""}')
        if dup:
            rejected.append({"claim": f"reg_calendar:{rc.get('name', '?')}",
                             "why": f"макро-дубль «{dup}»: сквозную величину "
                                    f"перезапрашивает макро-слой, рецепт в "
                                    f"отраслевом кеше ей не нужен"})
            continue
        cal = art.setdefault("reg_calendar", [])
        for i, old in enumerate(cal):
            if old.get("name") == rc["name"]:
                cal[i] = rc
                break
        else:
            cal.append(rc)

    if cadence_classes:
        decl = [c for c in TTL_DAYS if c in cadence_classes]
        if decl:
            art["cadence_classes"] = decl
        else:
            rejected.append({"claim": f"cadence_classes:{cadence_classes}",
                             "why": "ни один класс не из fast/slow/annual"})

    derive(art)
    if applied or reg_calendar or cadence_classes:
        _atomic_write(cache_path(cache_dir, profile),
                      json.dumps(art, ensure_ascii=False, indent=1))
    return {"accepted": len(applied), "rejected": rejected,
            "classes_touched": sorted({f["cadence"] for f in applied}),
            "path": str(cache_path(cache_dir, profile)),
            "replaced_by_id": stats["replaced_by_id"],
            "replaced_by_topic": stats["replaced_by_topic"],
            "refreshed": stats["refreshed"], "appended": stats["appended"],
            "older_rejected": stats["older_rejected"], "unknown_ids": unknown_ids,
            "stale_left": sum(1 for _, _, x in iter_facts(art)
                              if x.get("cadence") in declared_classes(art) and is_stale(x, now))}


def merge_dossier(cache_dir: str | Path, profile: str, dossier_file: str) -> str | None:
    """None = ок, иначе причина отказа. Кап 20 КБ + отсутствие клиентских данных."""
    if not is_cacheable(profile):
        return (f"профиль {profile} не отрасль (см. is_cacheable) — досье "
                f"общей линзы стало бы фоном для §3 чужих отраслей")
    raw = Path(dossier_file).read_bytes()
    if len(raw) > DOSSIER_CAP_BYTES:
        return f"досье {len(raw)} байт > кап {DOSSIER_CAP_BYTES} — сожми, числа держи в JSON"
    text = raw.decode("utf-8", errors="replace")
    leak = _client_data_leak(text)
    if leak:
        return leak
    _atomic_write(dossier_path(cache_dir, profile), text)
    return None


def invalidate(cache_dir: str | Path, profile: str) -> bool:
    art = load(cache_dir, profile)
    if art is None:
        return False
    for _, _, f in iter_facts(art):
        f["harvested"] = EPOCH                    # v6.61: протухает каждый факт
    derive(art)
    art["harvested"] = {cls: EPOCH for cls in TTL_DAYS}
    _atomic_write(cache_path(cache_dir, profile),
                  json.dumps(art, ensure_ascii=False, indent=1))
    return True


# ---------------------------------------------------------------- view
VIEW_RULES = [
    "fresh — действующие факты отрасли: числа в §3 брать отсюда, каждое с "
    "источником, годом и пометкой «по состоянию на <as_of>».",
    "stale — факты, не перепроверенные в срок (поле not_checked_since): "
    "использовать только как «по состоянию на <as_of>», не как текущее значение; "
    "свежее значение из market_<ИНН>.json (дельта-жатва, weekly) побеждает.",
    "Несколько фактов одной темы — это РАЗНЫЕ аспекты, а не версии: версии кеш "
    "уже заменил при вливании. Выбирать «последний» по теме не нужно.",
    "Строку «отраслевой слой: …» для брифа брать дословно из layer_line.",
]
# Выборка макро-слоя (v6.62): тот же механизм, другие правила — макро не
# источник чисел для §3, а фон суждений для §4/§7/§7.4/§8 (SKILL, ШАГ 1.7-макро).
MACRO_VIEW_RULES = [
    "fresh — действующие макро-условия: фон для §4 (стоимость долга), §7/§7.4 "
    "(окно рефинансирования, продукты), §8 (вопросы к CFO); число — с источником "
    "и «по состоянию на <as_of>»; собственных абзацев «про экономику» не порождать.",
    "stale — не перепроверены в срок (поле not_checked_since): только «по "
    "состоянию на <as_of>», не как текущее значение.",
    "Ключевая ставка, курсы, кривая ОФЗ, доходности — ТОЛЬКО из macro_debt.json "
    "на дату брифа, не отсюда.",
    "status: «проект» — не утверждать как действующую норму («рассматривается…»); "
    "«истёк» — норма не действует; «принят» с датой вступления в будущем — «вступит в "
    "силу с …». Без status — статус нормы читать из текста claim.",
    "Строку «макро-слой: …» для брифа собирать из layer_line и даты долгового среза.",
]


def view(cache_dir: str | Path, profile: str, now: date | None = None) -> dict:
    """Выборка для finalize (v6.61): действующие факты, протухшие — отдельно.

    Finalize раньше читал сырой файл профиля (100–160 фактов) и не знал,
    какие факты протухли: дата свежести жила у класса. Выборка несёт её у
    каждого факта и не сворачивает тему «до последнего» — в рубриках
    apk/retail/development факты одной темы — разные аспекты.
    """
    now = now or date.today()
    st = status(cache_dir, profile, now)
    art = load(cache_dir, profile) if is_cacheable(profile) else None
    if st.get("not_cacheable"):
        line = f"отраслевой слой: не использован (общая линза {profile}, слой не кешируется)"
    elif art is None or not st["as_of"]:
        line = ("макро-слой" if profile == MACRO_PROFILE else "отраслевой слой") + ": не использован"
    elif profile == MACRO_PROFILE:
        line = f"макро-слой: macro@{st['as_of']}"
    else:
        line = f"отраслевой слой: {profile}@{st['as_of']}"
    fresh, stale = [], []
    used = declared_classes(art) if art else []
    for seg, _, f in iter_facts(art):
        item = {"segment": seg, "topic": f.get("topic", ""), "claim": f.get("claim", ""),
                "value": f.get("value", ""), "source": f.get("source", ""),
                "source_url": f.get("source_url", ""), "as_of": f.get("as_of"),
                "cadence": f.get("cadence"), "harvested": f.get("harvested")}
        if f.get("status"):
            item["status"] = f["status"]
        if f.get("cadence") in used and is_stale(f, now):
            item["not_checked_since"] = f.get("harvested")
            stale.append(item)
        else:
            fresh.append(item)
    key = lambda x: (x["segment"], x["topic"], -_parse_day(x["as_of"] or EPOCH).toordinal())
    fresh.sort(key=key)
    stale.sort(key=key)
    return {"schema": "icache-view-1", "profile": profile, "generated": now.isoformat(),
            "verdict": st["verdict"], "as_of": st["as_of"], "layer_line": line,
            "counts": {"fresh": len(fresh), "stale": len(stale)},
            "rules": MACRO_VIEW_RULES if profile == MACRO_PROFILE else VIEW_RULES,
            "fresh": fresh, "stale": stale}


# ---------------------------------------------------------------- cli
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--profile", required=True, help="файл профиля, напр. apk.md")
    ap.add_argument("--cache-dir", required=True, help="каталог industry_cache/")
    ap.add_argument("--now", help="дата «сегодня» YYYY-MM-DD (тесты/воспроизводимость)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--merge", metavar="FACTS_JSON")
    mode.add_argument("--invalidate", action="store_true")
    mode.add_argument("--view", action="store_true",
                      help="выборка для finalize (v6.61) в файл --out")
    ap.add_argument("--out", help="--view: куда записать выборку (briefs/<chat>/icache_<ИНН>.json)")
    ap.add_argument("--json", action="store_true", help="--status: машинный вывод")
    ap.add_argument("--channel", default="market_agent",
                    choices=["market_agent", "deep_research", "routine"])
    ap.add_argument("--dossier", help="--merge: файл нарративного досье (кап 20 КБ)")
    args = ap.parse_args(argv)
    now = _parse_day(args.now) if args.now else None

    if args.status:
        st = status(args.cache_dir, args.profile, now)
        print(json.dumps(st, ensure_ascii=False, indent=1) if args.json
              else status_block(st))
        return 0

    if args.view:
        if not args.out:
            print("VIEW FAIL: нужен --out")
            return 2
        v = view(args.cache_dir, args.profile, now)
        _atomic_write(Path(args.out), json.dumps(v, ensure_ascii=False, indent=1))
        print(f"ICACHE_VIEW profile={args.profile} verdict={v['verdict']} "
              f"fresh={v['counts']['fresh']} stale={v['counts']['stale']} out={args.out}")
        print(v["layer_line"])
        return 0

    if args.invalidate:
        ok = invalidate(args.cache_dir, args.profile)
        print(f"invalidate {args.profile}: " + ("все классы помечены протухшими"
                                                if ok else "кеша нет — нечего инвалидировать"))
        return 0

    # --merge
    try:
        payload = json.loads(Path(args.merge).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"MERGE FAIL: вход не читается: {e}")
        return 1
    if isinstance(payload, dict):
        facts, reg_cal = [], payload.get("reg_calendar", [])
        cad_cls = payload.get("cadence_classes")
        for seg, items in payload.get("segments", {}).items():
            for f in items:
                facts.append(dict(f, segment=seg))
    else:
        facts, reg_cal, cad_cls = payload, [], None
    rep = merge(args.cache_dir, args.profile, facts,
                channel=args.channel, now=now, reg_calendar=reg_cal,
                cadence_classes=cad_cls)
    if rep.get("refused"):
        print(f"MERGE REFUSED {args.profile}: {rep['refused']}")
        return 1
    print(f"MERGE {args.profile}: принято {rep['accepted']}, "
          f"отклонено {len(rep['rejected'])}, классы {rep['classes_touched']}")
    # ASCII-маркер для приёмки: работает ли замена (до v6.61 — 0 из 118)
    print(f"MERGE_STATS profile={args.profile} replaced_by_id={rep['replaced_by_id']} "
          f"replaced_by_topic={rep['replaced_by_topic']} refreshed={rep['refreshed']} "
          f"appended={rep['appended']} older_rejected={rep['older_rejected']} "
          f"unknown_ids={len(rep['unknown_ids'])} stale_left={rep['stale_left']}")
    for r in rep["rejected"][:20]:
        print(f"  ✗ {r['claim']} — {r['why']}")
    if args.dossier:
        why = merge_dossier(args.cache_dir, args.profile, args.dossier)
        print("DOSSIER: ok" if why is None else f"DOSSIER FAIL: {why}")
        if why:
            return 1
    if rep["accepted"] == 0 and facts:
        print("MERGE FAIL: ни один факт не прошёл гейт — кеш не изменён")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
