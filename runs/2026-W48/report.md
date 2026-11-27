# Отчёт прогона 2026-W48 (2026-11-27, MONTHLY=0)

Подготовка, сверка, вливание и оформление: 19:01:25–19:11:48 МСК, до коммита. Все шесть штатных тестовых файлов прошли без ошибок. Туннель Keenetic (MACRO_PROXY) поднялся и использовался.

Прогон выполнен без помощников. Очередь 15; посев 0, осталось 0; календарь 8 к проверке, 6 новых событий, 8 рецептов обновлено. Ленты: 63 записи из 7 источников, без месячного разбора. Кандидатов 26 (18 фактов и 8 рецептов), подтверждено 26. Влито 16 фактов (15 замен, 1 перепроверка, 0 добавлений) и 8 рецептов. Pending сверки: 0; 2 подтверждённых факта отклонены гейтом даты, ещё 1 пункт оставлен без изменения после поиска. Undecided: 0; FUSES OK. Туннель MACRO_PROXY работал; недоступных доменов в финальной сверке нет.

Влито:
- `budget_execution_7m2026`: `85a087e1` → `e39f9d05`. [Минфин](https://minfin.gov.ru/ru/press-center/?id_4=40744): «По итогам января-октября 2026 года федеральный бюджет сложился с дефицитом в размере 5 234 млрд рублей».
- `cbr_forecast_corp_credit`: `29d0e87c` → `7adeeb6d`. [Банк России](https://www.cbr.ru/Content/Document/File/198897/forecast_261023.pdf): «…к организациям 12,5 9–12 6–11 8–13 8–13».
- `cbr_forecast_gdp`: `8f0c964c` → `9bfcb31f`. [Банк России](https://www.cbr.ru/Content/Document/File/198897/forecast_261023.pdf): «Валовой внутренний продукт 1,0 0,5–1,0 1,0–2,0 1,5–2,5 1,5–2,5».
- `cbr_forecast_inflation`: `77f57b18` → `4eae4c30`. [Банк России](https://www.cbr.ru/Content/Document/File/198897/forecast_261023.pdf): «Инфляция, в %, декабрь к декабрю предыдущего года 5,6 7,1–7,6 4,0 4,0 4,0».
- `cbr_forecast_keyrate`: `9f3a32b6` → `637ec3ba`. [Банк России](https://cbr.ru/dkp/mp_dec/decision_key_rate/comment_05112026/): «Средняя ключевая ставка в 2026 году составит 14,6%». В PDF надстрочная сноска была ошибочно прочитана как сотая доля процента.
- `cbr_forecast_oil`: `709bf97a` → `bb8c9fe2`. [Банк России](https://www.cbr.ru/Content/Document/File/198897/forecast_261023.pdf): «Цена нефти для налогообложения6, в среднем за год, долл. США за баррель 56 72 55 50 50».
- `contribution_base_2026`: `0da88320` → `3ecaf0bd`. [ФНС](https://www.nalog.gov.ru/rn86/news/activities_fts/16596985/): «Федеральный МРОТ на 2026 год установлен в размере 27 093 руб.».
- `it_benefits_2026`: `c782c043` → `427b4fe1`. [Письмо Минфина](https://base.garant.ru/414074925/): «применяют единый пониженный тариф страховых взносов в размере 15,0 процента в пределах установленной единой предельной величины базы».
- `msp_70pct_rule`: `ee9c002e` → `ee9c002e`, перепроверен. [ФНС](https://www.nalog.gov.ru/rn28/news/activities_fts/16626207/): «установлена возможность суммирования доходов от осуществления основного вида экономической деятельности и дополнительных видов».
- `msp_insurance_contributions`: `39a3e7c1` → `1c8c5519`. [ФНС](https://www.nalog.gov.ru/rn28/news/activities_fts/16626207/): «Ставка составляет 7,6% с выплат, превышающих полуторакратный МРОТ в месяц», для обрабатывающих производств.
- `national_regime_procurement`: `3edfccc4` → `49d5a67a`. [ПП № 1875](https://base.garant.ru/483437396/): «Установить минимальную обязательную долю закупок товаров российского происхождения по перечню согласно приложению N 3».
- `ndfl_scale`: `ad1b9d7a` → `724d53ba`. [ФНС](https://www.nalog.gov.ru/rn64/news/activities_fts/16654690/print/): «Повышенная ставка применяется не ко всей сумме дохода, а только к той части, которая превышает установленный порог».
- `federal_budget_2027_2029_draft`: `12dacbb1` → `5f2149b9`. [СОЗД, текст к третьему чтению](https://sozd.duma.gov.ru/download/1f1e67e1-387a-6508-81b3-755a07bd0ba3): «общий объем расходов федерального бюджета в сумме 48 740 443 433,7 тыс. рублей».
- `budget_2027_2029_project`: `af1b8de8` → `4c87c485`. [СОЗД, текст к третьему чтению](https://sozd.duma.gov.ru/download/1f1e67e1-387a-6508-81b3-755a07bd0ba3): «дефицит федерального бюджета на 2028 год в сумме 5 119 598 949,8 тыс. рублей и дефицит федерального бюджета на 2029 год в сумме 5 245 222 764,3 тыс. рублей».
- `fiscal_rule_oil_price`: `5ec6e021` → `2315d62c`. [СОЗД, текст к третьему чтению](https://sozd.duma.gov.ru/download/1f1e681b-2b9a-69b6-be42-9b4dc2b56d24): «50 долларов США за один баррель в 2027 - 2030 годах».
- `mrot_2027`: `3c5de462` → `baaba7af`. [СОЗД, текст к третьему чтению](https://sozd.duma.gov.ru/download/1f1e7430-c964-6e32-8914-5f1fc997872e): «Установить минимальный размер оплаты труда с 1 января 2027 года в сумме 28 935 рублей в месяц».

Не влито:
- `repatriaciya_vyruchki`: `OLDER_REJECTED`. [Текст постановления № 698](http://pravo.gov.ru/proxy/ips/?doc_itself=&backlink=1&nd=608613238&page=1&rdk=2) подтверждает окончание именно этого постановления 30.04.2026 и нулевые нормативы в последней редакции, но `2026-05-01 < 2026-10-16`. Более поздний акт о продлении не подтверждён.
- `223fz_gap`: `OLDER_REJECTED`. [ПП № 835](http://www.consultant.ru/document/cons_doc_LAW_538584/92d969e26a4326c5d02fa79b8f9cf4994ee5633b/) подтверждает поправки к национальному режиму, не к тексту самого 223-ФЗ; `2026-07-03 < 2026-08-20`.
- `factoring_leasing_no_data`: без замены. [Проект № 36262-9](https://sozd.duma.gov.ru/bill/36262-9) касается лизинга и кредитных историй, но не заменяет отрицательный факт о вступивших в силу изменениях по факторингу и лизингу.

## Решения по очереди

| Пункт | Тема | Решение | Где проверено |
|---|---|---|---|
| `080dd617` | `factoring_leasing_no_data` | без замены: найден проект, но не вступившая норма | [Документ](https://sozd.duma.gov.ru/bill/36262-9) |
| `a6010869` | `repatriaciya_vyruchki` | не влит: `OLDER_REJECTED` (2026-05-01 < 2026-10-16) | [Документ](http://pravo.gov.ru/proxy/ips/?doc_itself=&backlink=1&nd=608613238&page=1&rdk=2) |
| `85a087e1` | `budget_execution_7m2026` | влит как замена | [Документ](https://minfin.gov.ru/ru/press-center/?id_4=40744) |
| `29d0e87c` | `cbr_forecast_corp_credit` | влит как замена | [Документ](https://www.cbr.ru/Content/Document/File/198897/forecast_261023.pdf) |
| `8f0c964c` | `cbr_forecast_gdp` | влит как замена | [Документ](https://www.cbr.ru/Content/Document/File/198897/forecast_261023.pdf) |
| `77f57b18` | `cbr_forecast_inflation` | влит как замена | [Документ](https://www.cbr.ru/Content/Document/File/198897/forecast_261023.pdf) |
| `9f3a32b6` | `cbr_forecast_keyrate` | влит как замена | [Документ](https://cbr.ru/dkp/mp_dec/decision_key_rate/comment_05112026/) |
| `709bf97a` | `cbr_forecast_oil` | влит как замена | [Документ](https://www.cbr.ru/Content/Document/File/198897/forecast_261023.pdf) |
| `0239e303` | `223fz_gap` | не влит: `OLDER_REJECTED` (2026-07-03 < 2026-08-20); найден подзаконный акт, не поправка к тексту 223-ФЗ | [Документ](http://www.consultant.ru/document/cons_doc_LAW_538584/92d969e26a4326c5d02fa79b8f9cf4994ee5633b/) |
| `0da88320` | `contribution_base_2026` | влит как замена | [Документ](https://www.nalog.gov.ru/rn86/news/activities_fts/16596985/) |
| `c782c043` | `it_benefits_2026` | влит как замена | [Документ](https://base.garant.ru/414074925/) |
| `ee9c002e` | `msp_70pct_rule` | перепроверен, ID сохранён | [Документ](https://www.nalog.gov.ru/rn28/news/activities_fts/16626207/) |
| `39a3e7c1` | `msp_insurance_contributions` | влит как замена | [Документ](https://www.nalog.gov.ru/rn28/news/activities_fts/16626207/) |
| `3edfccc4` | `national_regime_procurement` | влит как замена | [Документ](https://base.garant.ru/483437396/) |
| `ad1b9d7a` | `ndfl_scale` | влит как замена | [Документ](https://www.nalog.gov.ru/rn64/news/activities_fts/16654690/print/) |

## Посев

Посевных пунктов нет. Пакет не сокращался.

## Решения по календарю

| Пункт | Событие или состояние | Решение и источник |
|---|---|---|
| 2 | Бюджет 2027–2029 | Рецепт обновлён: новое событие: одобрение Советом Федерации; подписание и публикация не подтверждены. Отдельный закон о поправках в бюджет-2026 в проверенных материалах не установлен. [Официальный источник](http://council.gov.ru/events/news/178688/) |
| 31 | Недельная инфляция | Рецепт обновлён: новая публикация за 17–23 ноября: 100,30% за неделю, 100,60% с начала месяца, 106,72% с начала года. [Официальный источник](https://rosstat.gov.ru/storage/mediabank/177_25-11-2026.pdf) |
| 32 | № 1340887-8, состав зарплаты на уровне МРОТ | Рецепт обновлён: новое событие: комитет рекомендовал отклонение; палата ещё не отклонила. [Официальный источник](https://sozd.duma.gov.ru/bill/1340887-8) |
| 33 | № 1341083-8, квоты для участников СВО | Рецепт обновлён: первого чтения не подтверждено, состояние «На рассмотрении» сверено. [Официальный источник](https://sozd.duma.gov.ru/bill/1341083-8) |
| 34 | № 1341173-8, инвестиционный налоговый вычет | Рецепт обновлён: первого чтения не подтверждено, состояние «На рассмотрении» сверено. [Официальный источник](https://sozd.duma.gov.ru/bill/1341173-8) |
| 35 | № 1342678-8, налог на прибыль для производителей анимации | Рецепт обновлён: новое событие: принято в первом чтении; поправки до 02.12.2026; не общая льгота для МСП. [Официальный источник](https://sozd.duma.gov.ru/bill/1342678-8) |
| 36 | № 617-9, налоговый пакет и маркетплейсы | Рецепт обновлён: новое событие: одобрение пакета Советом Федерации; факт о блокировке не создавался. Описание думской редакции: [КонсультантПлюс](https://www.consultant.ru/law/hotdocs/96392.html). [Официальный источник](http://council.gov.ru/events/news/178692/) |
| 37 | № 38674-9, базовый законопроект о единой ТОР | Рецепт обновлён: новое событие: внесён; отзывы до 04.12.2026; примерная программа на декабрь; это не вступление налогового режима в силу. [Официальный источник](https://sozd.duma.gov.ru/bill/38674-9) |

## Проверки и следующий шаг

Для исполнения бюджета за январь–октябрь использован [предварительный релиз Минфина](https://minfin.gov.ru/ru/press-center/?id_4=40744). В бюджетном пакете на 2027–2029 годы отделены цифры из парламентской редакции от факта [одобрения Советом Федерации](http://council.gov.ru/events/news/178688/); подписание и опубликование не утверждаются.

Открытых решений нет. Для следующей проверки: официальные публикации бюджетного и налогового пакета, включая точный объём обязанностей маркетплейсов; более поздний акт по валютной выручке, если появится; документ с подходящей датой и предметом для `223fz_gap`. Два отказа гейта даты не входят в `pending.json`, который содержит не прошедших сверку, а не не прошедших merge.

Все домены финальных кандидатов ответили прямо или через туннель. Отдельные принятые тексты на СОЗД доступны как PDF без извлекаемого текстового слоя; проверены извлекаемые файлы к третьему чтению, а стадии сверены по сообщениям палат.

## Ленты

```text
FEEDS_STATS since=2026-11-20 items=63 new=63 sources_ok=7/7 minfin_last_id=40792
FEEDS_SOURCE cbr_events ok=True  fetched=100  kept=3
FEEDS_SOURCE cbr_press  ok=True  fetched=11   kept=1
FEEDS_SOURCE cons_bills ok=True  fetched=55   kept=9
FEEDS_SOURCE cons_week  ok=True  fetched=112  kept=9
FEEDS_SOURCE gov_docs   ok=True  fetched=20   kept=1
FEEDS_SOURCE minfin     ok=True  fetched=18   kept=6
FEEDS_SOURCE vedomosti  ok=True  fetched=200  kept=34
```

## Посев: вывод инструмента

```text
SEED_DUE due=0 left=0 skipped=14 cap=20
```

## Сверка: вывод инструмента

```text
warning: The `fitz` API is deprecated and will be removed in future. Use `import pymupdf` instead.
VERIFY_STATS items=26 ok=26 VERIFIED=24 VERIFIED_TEXT=2 proxy=yes
VERIFY_HOST base.garant.ru               items=2 direct=2 proxy=0 unreachable=0
VERIFY_HOST cbr.ru                       items=5 direct=5 proxy=0 unreachable=0
VERIFY_HOST consultant.ru                items=1 direct=0 proxy=1 unreachable=0
VERIFY_HOST council.gov.ru               items=2 direct=2 proxy=0 unreachable=0
VERIFY_HOST minfin.gov.ru                items=1 direct=0 proxy=1 unreachable=0
VERIFY_HOST nalog.gov.ru                 items=4 direct=4 proxy=0 unreachable=0
VERIFY_HOST pravo.gov.ru                 items=1 direct=0 proxy=1 unreachable=0
VERIFY_HOST rosstat.gov.ru               items=1 direct=0 proxy=1 unreachable=0
VERIFY_HOST sozd.duma.gov.ru             items=9 direct=0 proxy=9 unreachable=0
```

## Вливание и предохранители

```text
MERGE macro.md: принято 16, отклонено 2, классы ['annual', 'slow']
MERGE_STATS profile=macro.md replaced_by_id=15 replaced_by_topic=0 refreshed=1 appended=0 older_rejected=2 unknown_ids=0 stale_left=9
  ✗ Подтверждённое изменение правил закупок по 223-ФЗ: постановление Правительства Р — старее кешевого: as_of 2026-07-03 < 2026-08-20 — кеш не тронут, находка остаётся в market_<ИНН>.json
  ✗ Истёк срок действия постановления Правительства РФ № 698 о реализации указа об о — старее кешевого: as_of 2026-05-01 < 2026-10-16 — кеш не тронут, находка остаётся в market_<ИНН>.json
FUSES_STATS facts 96 -> 96 removed=15 added=15 bytes 205818 -> 199188
FUSES OK
```
