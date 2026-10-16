# Отчёт прогона 2026-W42 (2026-10-16) — боевой прогон, не пилот

Начало: 2026-10-16 19:03 МСК. Конец: 2026-10-16 19:25 МСК.

Ветка: `claude/macro`. `MONTHLY=0` (16-е число — не первая пятница месяца),
п. 2а и полное перечитывание досье (п. 6, помимо `DOSSIER_DUE`) не выполнялись.

## Лента

```
FEEDS_STATS since=2026-10-09 items=45 new=45 sources_ok=7/7 minfin_last_id=40696
FEEDS_SOURCE cbr_events ok=True  fetched=100  kept=3
FEEDS_SOURCE cbr_press  ok=True  fetched=13   kept=2
FEEDS_SOURCE cons_bills ok=True  fetched=58   kept=7
FEEDS_SOURCE cons_week  ok=True  fetched=150  kept=12
FEEDS_SOURCE gov_docs   ok=True  fetched=20   kept=0
FEEDS_SOURCE minfin     ok=True  fetched=17   kept=5
FEEDS_SOURCE vedomosti  ok=True  fetched=200  kept=16
```

Все 7 источников лент — ok. Разбор заголовков по критерию отбора не
проводился — это пункт 2а, только для `MONTHLY=1`.

## Очередь протухших фактов (6 из `stale_queue`, кэп 15 не выбран)

| topic | решение |
|---|---|
| `factoring_leasing_no_data` | отрицательный факт; целевой повторный поиск (реформа лизинга, электронный факторинг под госконтракты) нового документа не нашёл — не тронут |
| `frp_zaymy` | источник `frprf.ru` недоступен (HTTP 403, антибот), `MACRO_PROXY` не задан — не тронут |
| `kip_stavka` | источник `frprf.ru` недоступен (HTTP 403) — не тронут |
| `promyshlennaya_ipoteka` | перепроверен словом в слово на том же источнике (kontur.ru) — влит, `harvested` обновлён |
| `repatriaciya_vyruchki` | статус переподтверждён + новый сигнал (ПМЭФ-2026, план Минфина до 2029 г.) — влит заменой |
| `transgranichnye_platezhi` | переподтверждён на текущей версии страницы, формулировка банковского перевода скорректирована под то, что подтверждается — влит заменой |

## Календарь (`calendar_due.py`): `DUE` 8 из 40

| рецепт | случилось? | решение |
|---|---|---|
| Заседание СД Банка России по ключевой ставке | нет (23.10.2026 ещё не наступило) | состояние подтверждено официальным календарём cbr.ru — обновлён |
| Обновление среднесрочного прогноза Банка России | нет | состояние подтверждено (прогноз выйдет 23.10.2026) — обновлён |
| Коэффициент-дефлятор патентов на 2027 год | нет | приказ Минэкономразвития ещё не издан (обычно октябрь–ноябрь) — не тронут |
| Лимит программы льготного кредитования МСП под ключевую ставку | нет (выборка лимита неизвестна) | формула ставки уточнена официальным пресс-релизом (Минтранс/Корпорация МСП) — обновлён |
| Перечень параллельного импорта и срок механизма | нет (перечень без изменений) | статус механизма на 2027 год подтверждён интервью замглавы Минпромторга ТАСС — обновлён |
| Перечень льготных ОКВЭД МСП 15% | нет | подтверждающей цитаты о новом перечне не нашлось — не тронут |
| Недельная инфляция Росстата | да (новые данные) | обновлён (вторичный источник — официальный бюллетень Росстата за эту неделю не найден) |
| Тариф страховых взносов ИТ-компаний на 2027 год | да (бюджет 2027–2029 внесён в Госдуму без изменений ИТ-льгот) | обновлён |

## Сверка

```
VERIFY_STATS items=9 ok=9 VERIFIED=7 VERIFIED_TEXT=2 proxy=no
VERIFY_HOST cbr.ru                       items=2 direct=2 proxy=0 unreachable=0
VERIFY_HOST icustoms.ru                  items=1 direct=1 proxy=0 unreachable=0
VERIFY_HOST kontur.ru                    items=1 direct=1 proxy=0 unreachable=0
VERIFY_HOST mintrans.gov.ru              items=1 direct=1 proxy=0 unreachable=0
VERIFY_HOST pnp.ru                       items=1 direct=1 proxy=0 unreachable=0
VERIFY_HOST profile.ru                   items=1 direct=1 proxy=0 unreachable=0
VERIFY_HOST tks.ru                       items=1 direct=1 proxy=0 unreachable=0
VERIFY_HOST vedomosti.ru                 items=1 direct=1 proxy=0 unreachable=0
```

9 кандидатов (3 факта + 6 рецептов календаря), все 9 подтверждены сверкой
(после 2 раундов правки цитат/чисел по исходным кандидатам — в рамках лимита
«не больше двух повторов»). `pending.json` — пуст.

## Вливание

```
MERGE macro.md: принято 3, отклонено 0, классы ['slow']
MERGE_STATS profile=macro.md replaced_by_id=2 replaced_by_topic=0 refreshed=1 appended=0 older_rejected=0 unknown_ids=0 stale_left=3
```

Влито 3 факта (2 замены + 1 перепроверка), `stale_left=3` — это
`factoring_leasing_no_data`, `frp_zaymy`, `kip_stavka`, оставшиеся в очереди
следующего прохода. Плюс обновлено 6 рецептов `reg_calendar` (замена по
имени, отдельного счётчика в `MERGE_STATS` нет).

## Досье

```
DOSSIER_DUE checked=2026-10-09 sections=6 due=2 problems=0
  DUE Внешний контур: ограничение — это платёж, а не пошлина — repatriaciya_vyruchki, transgranichnye_platezhi
  DUE Что из этого спрашивать у финансового директора — transgranichnye_platezhi
```

Оба раздела перечитаны на новых значениях опорных фактов — выводы по-прежнему
следуют из фактов (прямой перевод дёшев, но непредсказуем; платёжный агент —
рабочая альтернатива; статус репатриации — открытый вопрос на дату брифа),
правка текста не потребовалась. `PROBLEM` — нет. Шапка обновлена:
`Проверено: 2026-10-16`.

```
DOSSIER_DUE checked=2026-10-16 sections=6 due=0 problems=0
```

## Предохранители

```
FUSES_STATS facts 94 -> 94 removed=2 added=2 bytes 183198 -> 187379
FUSES OK
```

Путь — обычный (FUSES OK, не месячный проход): коммит и push прямо в
`claude/macro`.

⚠️ Объём слоя приближается к бюджету: 187 КБ из 200 КБ (94%), 94 факта из
150 (63%). Пока не предохранитель (порог не превышен), но в следующий
месячный проход (`MONTHLY=1`) стоит предложить кандидатов на вывод —
в первую очередь среди просроченных/узких мер господдержки с истёкшим
сроком действия.

## Недоступные домены

- `frprf.ru` — HTTP 403 (похоже на антибот), прямой маршрут; `MACRO_PROXY`
  в этом прогоне не задан. Затронуты факты `frp_zaymy`, `kip_stavka` —
  остались без изменений, уйдут в очередь следующего прохода.

## MACRO_RUN

MACRO_RUN week=2026-W42 monthly=0 queue=6 feeds=45 verified=9 merged=3 appended=0 pending=0 dossier_due=2 fuses=OK branch=claude/macro
