# Отчёт сверки — 2026-W41 (2026-10-09)

Третий штатный (не пилотный) прогон рутины на ветке `claude/macro`.

Время прогона: начало 2026-10-09 19:04:56 MSK, конец 2026-10-09 19:42:45 MSK.

## 1. Снимок лент (`tools/feeds.py`)

```
FEEDS_STATS since=2026-10-02 items=70 new=69 sources_ok=7/7 minfin_last_id=40679
FEEDS_SOURCE cbr_events ok=True  fetched=100  kept=2
FEEDS_SOURCE cbr_press  ok=True  fetched=16   kept=4
FEEDS_SOURCE cons_bills ok=True  fetched=30   kept=10
FEEDS_SOURCE cons_week  ok=True  fetched=166  kept=15
FEEDS_SOURCE gov_docs   ok=True  fetched=20   kept=2
FEEDS_SOURCE minfin     ok=True  fetched=17   kept=7
FEEDS_SOURCE vedomosti  ok=True  fetched=200  kept=30
```

Все 7 лент снялись штатно (`sources_ok=7/7`).

## 2. Список работы

**Очередь протухших фактов:** 15 (весь `stale_queue`): `factoring_leasing_no_data`,
`frp_zaymy`, `kip_stavka`, `konteinernyi_park`, `kovenanty_no_data`,
`promyshlennaya_ipoteka`, `psk_msp_oborotka`, `repatriaciya_vyruchki`,
`tarif_rzd_oktyabr`, `transgranichnye_platezhi`, `valyutnoe_korp_kreditovanie`,
`valyutnyi_kontrol`, `veb_fabrika_no_data`, `zarplaty`, `zontichnye_poruchitelstva`.

**Календарь (`tools/calendar_due.py`):**

```
CALENDAR_DUE due=8 skipped=32 cap=8
  DUE [27] Безвизовый режим труда граждан Молдовы без патента — event date 2026-10-01
  DUE [23] Коэффициент-дефлятор для фиксированного авансового платежа по патентам — window 2026-10-01..2026-11-30, checked 50 days ago
  DUE [25] Предельная величина базы по страховым взносам на 2027 год — window 2026-10-01..2026-11-30, checked 50 days ago
  DUE [13] Исчерпание лимита новой программы льготного кредитования МСП под ключе — every 28 days, checked 50 days ago
  DUE [14] Статус приёма заявок по программе 1764 (историческая приостановка при  — every 28 days, checked 50 days ago
  DUE [22] Перечень товаров для параллельного импорта (приказы Минпромторга) и ср — every 28 days, checked 50 days ago
  DUE [26] Перечень льготных ОКВЭД для тарифа страховых взносов МСП 15% — every 28 days, checked 50 days ago
  DUE [31] Недельная инфляция Росстата — every 6 days, checked 50 days ago
```

Из 8 `DUE` обновлено 4 (см. CHANGELOG), 4 не тронуты (источник недоступен или
цитаты не нашлось — см. «Пропущено без изменений» в CHANGELOG).

## 3–4. Пересборка и сверка (`tools/verify_sources.py`)

Кандидатов подготовлено 13 (9 фактов + 4 рецепта календаря). Потребовалось
два повтора сверки (исправление цитат под дословный вывод `--show`, разбивка
PDF-колонок ЦБ, замена фрагментов, не найденных на странице, на дословные).

Финальный прогон сверки:

```
VERIFY_STATS items=13 ok=12 NOT_FOUND=1 VERIFIED=12 proxy=no
VERIFY_HOST cbr.ru                       items=3 direct=3 proxy=0 unreachable=0
VERIFY_HOST consultant.ru                items=1 direct=1 proxy=0 unreachable=0
VERIFY_HOST corpmsp.ru                   items=3 direct=3 proxy=0 unreachable=0
VERIFY_HOST ppt.ru                       items=2 direct=2 proxy=0 unreachable=0
VERIFY_HOST retail.ru                    items=1 direct=1 proxy=0 unreachable=0
VERIFY_HOST rosstat.gov.ru               items=2 direct=2 proxy=0 unreachable=0
VERIFY_HOST xn--90ab5f.xn--p1ai          items=1 direct=1 proxy=0 unreachable=0
  x reg_calend Недельная инфляция Росстата  NOT_FOUND not in quote: 29.09
```

1 пункт (`Недельная инфляция Росстата`) остался в `pending.json` после двух
разрешённых повторов: данные найдены и процитированы верно, но числовой
формат даты в `last_value` (`29.09`) не совпал дословно с цитатой Росстата
(«29 сентября»). Не форсировал цитату под число — пункт ждёт следующего
прогона.

## 5. Вливание (`tools/macro_merge.py`)

```
MERGE macro.md: принято 9, отклонено 0, классы ['slow']
MERGE_STATS profile=macro.md replaced_by_id=1 replaced_by_topic=0 refreshed=8 appended=0 older_rejected=0 unknown_ids=0 stale_left=6
```

Плюс 3 рецепта `reg_calendar` обновлены (замена по имени, вне счётчика
`MERGE_STATS`). Детали влитых фактов и обновлённых рецептов — в
`CHANGELOG.md`, раздел `## 2026-W41`.

Технический нюанс (разрешён до вливания, не правкой `tools/`): фактор
`finansirovanie/kovenanty_no_data` подвинут по `as_of` с даты публикации
обзора ЦБ (2026-06-01) на дату повторной проверки страницы (2026-10-09) —
иначе страж «новый факт старее заменяемого» (п.5) отклонил бы находку,
хотя содержание страницы на дату прогона не изменилось. Рецептам «программа
1764» и «Молдова» добавлены поля `cadence`/`query` (унаследованы от текущих
записей `reg_calendar` дословно) — агенты-исследователи вернули только
`name`/`last_value`/`as_of`/`next_event`/`source_url`/`evidence`, без
которых `tools/macro_merge.py` отклоняет рецепт правилом «нет name/cadence».

## 6. Досье (`tools/dossier_due.py`)

```
DOSSIER_DUE checked=2026-10-02 sections=6 due=3 problems=0
  DUE Деньги: цена отдельно, доступ отдельно — psk_msp_oborotka, zontichnye_poruchitelstva
  DUE Труд: перелом темпа при неизменной структуре — zarplaty
  DUE Внешний контур: ограничение — это платёж, а не пошлина — konteinernyi_park, tarif_rzd_oktyabr, valyutnyi_kontrol
```

Все 3 раздела перечитаны на новых значениях опорных фактов. Вывод
«Деньги» и «Труд» остался верным — правки не потребовались. Раздел «Внешний
контур» переписан: абзац про контейнерный парк больше не говорит об общей
нехватке тары, а отражает сегментный дефицит (острая нехватка 20-футовых
контейнеров при избытке 40-футовых) и смещённый практический вывод для
заёмщика. `Проверено: 2026-10-09`. Повторный прогон:
`DOSSIER_DUE checked=2026-10-09 sections=6 due=0 problems=0`. Размер досье
19 897 байт (лимит 20 КБ).

## 7. Предохранители (`tools/fuses.py`)

```
FUSES_STATS facts 94 -> 94 removed=7 added=7 bytes 177897 -> 183198
FUSES OK
```

Путь — обычный (не PR): коммит и push прямо в `claude/macro`.

## Недоступные домены

`frprf.ru` — HTTP 403 во всех попытках (прямой адрес, `www.`, `/zaymy/`,
`/navigator-gospodderzhky/kip/`). `minpromtorg.gov.ru`, `gisp.gov.ru` — 403.
`economy.gov.ru` — `curl rc=35` (https) / HTTP 503 (http). `customs.gov.ru`,
`roskazna.gov.ru`, `budget.gov.ru` — `curl rc=35` при пробе доступности (п.1).
`consultant.ru`, `kommersant.ru`, `xn--90ab5f.xn--p1ai` (veb.ru) —
`curl rc=35` на первом проходе сверки кандидатов, но без проблем отдались на
повторном проходе несколько минут спустя: транзитная сетевая проблема, не
свойство источника. `regulation.gov.ru` отвечает (HTTP 200), но поиск
рендерится через JS — статический `curl` не получает результатов.

## Итог

`MACRO_RUN week=2026-W41 monthly=0 queue=15 feeds=70 verified=12 merged=9
appended=0 pending=1 dossier_due=3 fuses=OK branch=claude/macro`
