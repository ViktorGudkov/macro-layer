# Отчёт прогона 2026-W46 (2026-11-13, MONTHLY=0)

Исполнитель: Perplexity Computer (замена облачной рутины Claude Code), по `PROMPT.md` из `main`. Прокси нет. Сбор кандидатов — пять помощников (группы A–E, файлы `cand_*.json`, заметки `notes_*.md`); сверка, merge, предохранители, CHANGELOG и коммит — основной агент. Время прогона: 19:00–19:08 МСК.

Прогон выполнил Perplexity Computer вместо облачной рутины Claude Code, по тому же `PROMPT.md`; прокси нет.

- очередь 15, посев 20 (осталось 12 по счётчику скрипта до прогона), календарь 8 наступило / 3 случилось ([3] оценка исполнения бюджета за январь–октябрь, [26] ФЗ № 104-ФЗ, [22] законопроект № 33897-9), кандидатов 43 (35 фактов, включая fiscal_impulse_timing сверх списка, + 8 рецептов), подтверждено 37, влито 27 фактов (26 замен / 1 перепроверка) + 8 рецептов, отклонено merge 2, в pending 6 (+ 1 отрицательный факт без кандидата).
- Бюджет-2026 (отозванная в W46 сверка): federal_budget_2026, national_projects_funding, state_debt_borrowings — теперь по HTML-заключению Комитета СФ, budget_revenue_structure — по пояснительной записке к законопроекту на Гаранте; budget_expenditure_structure, tech_national_projects, zhkh_spending_trend — в pending (числа закона только в перемешанной брошюре, minfin.gov.ru 503).
- Существенные изменения: usn_vat_threshold — снижение порога НДС на УСН отложено (ФЗ от 04.07.2026 № 228-ФЗ: 20 млн до 2029 г.); psn_income_limit — лестница ПСН больше не совпадает с порогом НДС; tax_monitoring — тезис «снято одновременное соблюдение порогов» опровергнут текстом ст. 105.26; icr_kriterii — критерии ЦБ раскрыты (ICR < 3 и др.); kvota_inostrannye_rabotniki — исправлены реквизиты (ПП № 1920, а не № 1995).

Влито:
- `kip_stavka`: c76577d9 → 1bab1d1b. Решение Минпромторга России от 23.03.2026 № 24-64132-01596-Р (Версия 4), текст на портале ГАРАНТ. «в размере значения 30 процентов ключевой ставки Центрального банка Российской Федерации, действующей на каждую дату начисления процентов за пользовани»
- `bezrabotica`: c6096844 → 734c3864. Банк России, презентационные материалы (PDF), слайд «Безработица». «Общий уровень безработицы, % 2,2% сентябрь 2026 года На исторических минимумах»
- `budget_plan_revision`: c711ced0 → 5a16d304. Пояснительная записка к проекту федерального закона № 615-9 «О федеральном бюджете на 2027 год и на плановый п. «Дефицит (-) / Профицит (+) -5 626,5 -7 344,9»
- `cfa_raskrytie_2026`: 6676cac3 → 4747e4b8. Банк России, Вестник Банка России № 21 (2610) от 01.07.2026; Указание Банка России от 26.03.2026 № 7315-У. «* Официально опубликовано на сайте Банка России 18.06.2026.»
- `icr_kriterii`: 2ddf8cba → 8c926dbe. Банк России, страница «Надбавки к коэффициентам риска» (Указание Банка России от 16.12.2024 № 6960-У). «компания имеет повышенную долговую нагрузку, то есть коэффициент покрытия процентов операционной прибылью с учетом амортизации составляет менее 3»
- `parallelnyi_import`: 28669628 → ff4b2094. Гарант, текст приказа Минпромторга России от 26.09.2025 № 4769 (с пометками о датах вступления в силу пунктов). «группы 84 ТН ВЭД ЕАЭС: а) в пункте 283 слово "TORNEO," исключ»
- `parallelnyi_import_kriterii`: bb0d0190 → fd015683. РИА Новости со ссылкой на комментарий Минпромторга России (вторичный источник; официального текста с перечисле. «наличие на территории Российской Федерации аналогов продукции и их производство в достаточном количестве для покрытия спроса конечных потребителей»
- `prochie_kanaly_msp`: 6c414b49 → d96b325d. Корпорация МСП, новость «Более 1,2 млрд рублей привлекли МСП по новой льготной программе кредитования» от 17.0. «До конца года бизнес может привлечь по программе 150 млрд рублей.»
- `programma_1764`: d4890b08 → b13fa0f8. Корпорация МСП, страница «Программа стимулирования кредитования МСП с субсидией минэкономразвития России». «МСП от 25 млн до 2 млрд руб. Срок до 10 лет»
- `konteinernyi_park`: b015326e → 476703fa. Retail.ru со ссылкой на председателя НАОКС Артёма Замараева, 11.09.2026 (вторичный источник; официальной стати. «11 сентября 2026, 14:38»
- `kovenanty_no_data`: b4ae5a6e → 8cb325f0. Банк России, «Обзор финансовой стабильности. IV квартал 2025 – I квартал 2026 года» (опубликован 1 июня 2026 г. «Для ограничения рисков закредитованности крупных компаний с 01.03.2026 макропруденциальная надбавка на прирост долга была повышена на 60 п.п., до 100%»
- `budget_revenue_structure`: 0f3f42ab → b4585547. Пояснительная записка к проекту федерального закона № 1026181-8 «О федеральном бюджете на 2026 год и на планов. «Поступление нефтегазовых доходов в федеральный бюджет в 2026 году прогнозируется в объеме 8 918,5 млрд рублей (3,8% к ВВП)»
- `federal_budget_2026`: 1f44440c → 32012d01. Совет Федерации, заключение Комитета по бюджету и финансовым рынкам по ФЗ «О федеральном бюджете на 2026 год и. «Дефицит федерального бюджета составит в 2026 году 3 786,4 млрд рублей (1,6% ВВП)»
- `national_projects_funding`: bfaec049 → 31e5bb09. Совет Федерации, заключение Комитета по бюджету и финансовым рынкам по ФЗ «О федеральном бюджете на 2026 год и. «а также на национальный проект «Инфраструктура для жизни»: 1 364,1 млрд рублей в 2026 году, 1 656,7 млрд рублей в 2027 году и 2 008,1 млрд рублей в 20»
- `state_debt_borrowings`: 7e569214 → d699b797. Совет Федерации, заключение Комитета по бюджету и финансовым рынкам по ФЗ «О федеральном бюджете на 2026 год и. «Основными источниками финансирования дефицита федерального бюджета в 2026–2028 годах будут государственные заимствования»
- `psn_income_limit`: 7d7d72c5 → b543edb9. ФНС России, спецраздел «Налоги 2026». «Налогоплательщик утрачивает право на ПСН с периода, который приходится на 2026 год, если за 2025 год или в течение 2026 года доходы превысили 20 млн р»
- `psn_loss_of_right`: b012eb90 → 0753689f. УФНС России по Ульяновской области, «С 1 января вступает в силу снижение лимита предельных доходов на ПСН» (na. «то право на применение ПСН утрачивается с начала действия патента, действующего в период такого превышения»
- `software_vat_exemption`: babb238d → aa0a7061. Письмо Минфина России от 06.05.2026 № 03-07-08/37981 (Гарант). «Абзацем вторым указанной нормы установлены ограничения: положения данного подпункта не применяются, если передаваемые права состоят в получении возмож»
- `tax_monitoring`: 21927345 → 2ec99227. НК РФ, ст. 105.26 (Гарант). «организация вправе обратиться в налоговый орган с заявлением о проведении налогового мониторинга при одновременном соблюдении следующих условий»
- `usn_vat_reduced_rates`: d90bbbdf → d90bbbdf. ФНС России, спецраздел «Налоги 2026». «Если есть освобождение от НДС или применяется ставка НДС 5 или 7 %, «входной» и «ввозной» НДС включается в стоимость приобретенных товаров (работ, усл»
- `usn_vat_threshold`: 044a6bd2 → 093f0291. Федеральный закон от 04.07.2026 № 228-ФЗ (Гарант). «Согласно изменениям порог доходов за 2025-2028 гг. составит 20 млн руб., за 2029 г. - 15 млн руб., за 2030 и последующие годы - 10 млн руб.»
- `vat_rate`: 585d6ffd → a07008bd. ФНС России, спецраздел «Налоги 2026». «рассчитывать НДС по общеустановленным ставкам, применяя 22% (10%) и вычеты»
- `dolya_inostrannykh_rabotnikov`: 7eb400d2 → b06da84f. ГАРАНТ — текст постановления Правительства РФ от 05.12.2025 № 1995 «Об установлении на 2026 год допустимой дол. «р) деятельность по обслуживанию зданий и территорий (код 81 ) - в размере 70 процентов общей численности работников, используемых указанными хозяйству»
- `kadrovyi_deficit`: a0d43334 → 6389d0da. Коммерсантъ, 29.04.2026, со ссылкой на прогноз РСПП (вторичный источник). «Согласно прогнозу Российского союза промышленников и предпринимателей (РСПП), дефицит кадров на рынке до 2030 года может составить более 3 млн работни»
- `kvota_inostrannye_rabotniki`: 0fbdcbd7 → 6c95605d. ГАРАНТ — текст постановления Правительства РФ от 28.11.2025 № 1920. «3. Утвердить на 2026 год квоты на выдачу иностранным гражданам, прибывающим в Российскую Федерацию на основании визы: 278940 приглашений на въезд в Ро»
- `mrot`: 50e2a8c5 → 91bcd4e0. ГАРАНТ — текст Федерального закона от 28.11.2025 № 429-ФЗ. «С 1 января 2026 г. МРОТ увеличится на 20,7% и составит 27 093 руб.»
- `fiscal_impulse_timing`: 5e513be6 → bfe57f65. Интерфакс со ссылкой на краткую ежемесячную информацию Минфина, «Дефицит бюджета РФ за 10 месяцев составил 5,2. «Доходы бюджета в январе-октябре увеличились на 11% год к году и составили 33,176 трлн рублей»

Не подтверждено / не влито:
- `factoring_leasing_no_data` — — — отрицательный, документа нет
- `frp_zaymy` — UNREACHABLE — direct: http 403
- `komplaens_platezhi` — UNREACHABLE — direct: http 502
- `parallelnyi_import_srok` — VERIFIED — отклонено гейтом merge: as_of 2026-01-01 < 2026-10-02 (старый факт не тронут)
- `budget_expenditure_structure` — UNREACHABLE — direct: http 503
- `tech_national_projects` — UNREACHABLE — direct: http 503
- `zhkh_spending_trend` — UNREACHABLE — direct: http 503
- `splitting_amnesty` — VERIFIED — отклонено гейтом merge: as_of 2024-07-12 < 2026-07 (старый факт не тронут)
- `kvota_invalidy_sout` — UNREACHABLE — direct: http 403

Недоступные домены: minfin.gov.ru (503), rosstat.gov.ru, consultant.ru, economy.gov.ru, sozd.duma.gov.ru, budget.gov.ru, мсп.рф, minpromtorg.gov.ru, mintrans.gov.ru, alta.ru, rspp.ru (502), frprf.ru, gisp.gov.ru, www.garant.ru (403; base.garant.ru открывается); сканы без текста на publication.pravo.gov.ru; sttlogistics.ru — 502 при общей сверке (у помощника открывался).


## Ленты (FEEDS_STATS)
```
FEEDS_STATS since=2026-11-06 items=30 new=30 sources_ok=5/7 minfin_last_id=40737 FAILED=cons_bills,cons_week
FEEDS_SOURCE cbr_events ok=True  fetched=100  kept=3    
FEEDS_SOURCE cbr_press  ok=True  fetched=13   kept=2    
FEEDS_SOURCE cons_bills ok=False fetched=0    kept=0    RuntimeError: http 502
FEEDS_SOURCE cons_week  ok=False fetched=0    kept=0    RuntimeError: archive http 502
FEEDS_SOURCE gov_docs   ok=True  fetched=20   kept=6    
FEEDS_SOURCE minfin     ok=True  fetched=0    kept=0    
FEEDS_SOURCE vedomosti  ok=True  fetched=200  kept=19   
```

## Посев (SEED_DUE)
`SEED_DUE due=20 left=12 skipped=17 cap=20`

## Сверка (VERIFY_HOST)
```
VERIFY_STATS items=43 ok=37 UNREACHABLE=6 VERIFIED=33 VERIFIED_TEXT=4 proxy=no
VERIFY_HOST base.garant.ru               items=12 direct=12 proxy=0 unreachable=0
VERIFY_HOST budget.council.gov.ru        items=3 direct=3 proxy=0 unreachable=0
VERIFY_HOST cbr.ru                       items=4 direct=4 proxy=0 unreachable=0
VERIFY_HOST corpmsp.ru                   items=4 direct=4 proxy=0 unreachable=0
VERIFY_HOST frprf.ru                     items=1 direct=0 proxy=0 unreachable=1
VERIFY_HOST garant.ru                    items=1 direct=0 proxy=0 unreachable=1
VERIFY_HOST interfax.ru                  items=2 direct=2 proxy=0 unreachable=0
VERIFY_HOST kommersant.ru                items=1 direct=1 proxy=0 unreachable=0
VERIFY_HOST minfin.gov.ru                items=3 direct=0 proxy=0 unreachable=3
VERIFY_HOST mintrud.gov.ru               items=1 direct=1 proxy=0 unreachable=0
VERIFY_HOST nalog.gov.ru                 items=7 direct=7 proxy=0 unreachable=0
VERIFY_HOST retail.ru                    items=1 direct=1 proxy=0 unreachable=0
VERIFY_HOST ria.ru                       items=1 direct=1 proxy=0 unreachable=0
VERIFY_HOST sttlogistics.ru              items=1 direct=0 proxy=0 unreachable=1
VERIFY_HOST x-compliance.ru              items=1 direct=1 proxy=0 unreachable=0
  x byudzhet   budget_expenditure_structure UNREACHABLE direct: http 503
  x byudzhet   tech_national_projects       UNREACHABLE direct: http 503
  x byudzhet   zhkh_spending_trend          UNREACHABLE direct: http 503
  x trud       kvota_invalidy_sout          UNREACHABLE direct: http 403
  x podderzhka frp_zaymy                    UNREACHABLE direct: http 403
  x vneshtorg  komplaens_platezhi           UNREACHABLE direct: http 502
```

## Merge и предохранители
```
MERGE macro.md: принято 27, отклонено 2, классы ['annual', 'slow']
MERGE_STATS profile=macro.md replaced_by_id=26 replaced_by_topic=0 refreshed=1 appended=0 older_rejected=2 unknown_ids=0 stale_left=11
  ✗ Налоговая амнистия за дробление бизнеса (ст. 6 ФЗ от 12.07.2024 № 176-ФЗ) действ — старее кешевого: as_of 2024-07-12 < 2026-07 — кеш не тронут, находка остаётся в market_<ИНН>.json
  ✗ Механизм параллельного импорта действует в 2026 году: Федеральным законом от 15. — старее кешевого: as_of 2026-01-01 < 2026-10-02 — кеш не тронут, находка остаётся в market_<ИНН>.json
FUSES_STATS facts 96 -> 96 removed=26 added=26 bytes 193126 -> 198728
FUSES OK
```

## Решения: очередь и посев
| Блок | id | Тема | Решение |
|---|---|---|---|
| очередь | 080dd617 | finansirovanie/factoring_leasing_no_data | pending: кандидата нет — отрицательный факт, принятого документа не найдено (правило 4), факт не тронут |
| очередь | 6d072f80 | podderzhka/frp_zaymy | pending: UNREACHABLE — direct: http 403 |
| очередь | c76577d9 | podderzhka/kip_stavka | влит (замена c76577d9 → 1bab1d1b) |
| очередь | c6096844 | trud/bezrabotica | влит (замена c6096844 → 734c3864) |
| очередь | c711ced0 | byudzhet/budget_plan_revision | влит (замена c711ced0 → 5a16d304) |
| очередь | 6676cac3 | finansirovanie/cfa_raskrytie_2026 | влит (замена 6676cac3 → 4747e4b8) |
| очередь | 2ddf8cba | finansirovanie/icr_kriterii | влит (замена 2ddf8cba → 8c926dbe) |
| очередь | bd57820c | vneshtorg/komplaens_platezhi | pending: UNREACHABLE — direct: http 502 |
| очередь | 28669628 | vneshtorg/parallelnyi_import | влит (замена 28669628 → ff4b2094) |
| очередь | bb0d0190 | vneshtorg/parallelnyi_import_kriterii | влит (замена bb0d0190 → fd015683) |
| очередь | 763ecc54 | vneshtorg/parallelnyi_import_srok | pending: отклонено гейтом merge: as_of 2026-01-01 < 2026-10-02 (старый факт не тронут) |
| очередь | 6c414b49 | podderzhka/prochie_kanaly_msp | влит (замена 6c414b49 → d96b325d) |
| очередь | d4890b08 | podderzhka/programma_1764 | влит (замена d4890b08 → b13fa0f8) |
| очередь | b015326e | vneshtorg/konteinernyi_park | влит (замена b015326e → 476703fa) |
| очередь | b4ae5a6e | finansirovanie/kovenanty_no_data | влит (замена b4ae5a6e → 8cb325f0) |
| посев | 693682ef | byudzhet/budget_expenditure_structure | pending: UNREACHABLE — direct: http 503 |
| посев | 0f3f42ab | byudzhet/budget_revenue_structure | влит (замена 0f3f42ab → b4585547) |
| посев | 1f44440c | byudzhet/federal_budget_2026 | влит (замена 1f44440c → 32012d01) |
| посев | bfaec049 | byudzhet/national_projects_funding | влит (замена bfaec049 → 31e5bb09) |
| посев | 7e569214 | byudzhet/state_debt_borrowings | влит (замена 7e569214 → d699b797) |
| посев | 602882e9 | byudzhet/tech_national_projects | pending: UNREACHABLE — direct: http 503 |
| посев | 77da7b1e | byudzhet/zhkh_spending_trend | pending: UNREACHABLE — direct: http 503 |
| посев | 7d7d72c5 | nalogi/psn_income_limit | влит (замена 7d7d72c5 → b543edb9) |
| посев | b012eb90 | nalogi/psn_loss_of_right | влит (замена b012eb90 → 0753689f) |
| посев | babb238d | nalogi/software_vat_exemption | влит (замена babb238d → aa0a7061) |
| посев | 77f025bc | nalogi/splitting_amnesty | pending: отклонено гейтом merge: as_of 2024-07-12 < 2026-07 (старый факт не тронут) |
| посев | 21927345 | nalogi/tax_monitoring | влит (замена 21927345 → 2ec99227) |
| посев | d90bbbdf | nalogi/usn_vat_reduced_rates | перепроверен (claim слово в слово) |
| посев | 044a6bd2 | nalogi/usn_vat_threshold | влит (замена 044a6bd2 → 093f0291) |
| посев | 585d6ffd | nalogi/vat_rate | влит (замена 585d6ffd → a07008bd) |
| посев | 7eb400d2 | trud/dolya_inostrannykh_rabotnikov | влит (замена 7eb400d2 → b06da84f) |
| посев | a0d43334 | trud/kadrovyi_deficit | влит (замена a0d43334 → 6389d0da) |
| посев | 0fbdcbd7 | trud/kvota_inostrannye_rabotniki | влит (замена 0fbdcbd7 → 6c95605d) |
| посев | 99e6503c | trud/kvota_invalidy_sout | pending: UNREACHABLE — direct: http 403 |
| посев | 50e2a8c5 | trud/mrot | влит (замена 50e2a8c5 → 91bcd4e0) |
| сверх (событие рецепта [3]) | 5e513be6 | byudzhet/fiscal_impulse_timing | влит (замена 5e513be6 → bfe57f65) |

## Решения: календарь
| Рецепт | Решение |
|---|---|
| [24] Квота на иностранных работников по визе на 2027 год | рецепт обновлён: постановление не принято; Минтруд 30.10.2026 вынес на обсуждение проект с квотой 382,8 тыс. (mintrud.gov.ru/employment/migration/655) |
| [3] Ежемесячная оценка исполнения федерального бюджета | случилось (10.11.2026): январь–октябрь — доходы 33,176 трлн, расходы 38,41 трлн, дефицит 5,234 трлн (2,3% ВВП); рецепт обновлён, факт fiscal_impulse_timing заменён; источник Интерфакс (вторичный, minfin.gov.ru 503) |
| [4] Перечень приоритетных отраслей для пониженных взносов МСП | рецепт обновлён: перечень по-прежнему распоряжение № 4125-р, изменений не найдено (nalog.gov.ru) |
| [26] Перечень льготных ОКВЭД для тарифа взносов МСП 15% | случилось: ФЗ от 25.04.2026 № 104-ФЗ (суммирование доходов по основному и дополнительным ОКВЭД для доли 70%); рецепт обновлён (nalog.gov.ru) |
| [18] Указ о репатриации и обязательной продаже валютной выручки | рецепт обновлён: нового документа нет; последний установленный норматив 0% — по 30.04.2026 (base.garant.ru/3958573) |
| [14] Статус приёма заявок по программе 1764 | рецепт обновлён: приостановки нет, КС − 3,5%, 25 млн – 2 млрд ₽, до 10 лет (corpmsp.ru) |
| [13] Исчерпание лимита программы льготного кредитования МСП (150 млрд) | рецепт обновлён: о выборке лимита сообщений нет; последняя официальная цитата — Корпорация МСП 17.08.2026 (corpmsp.ru) |
| [22] Перечень товаров для параллельного импорта | случилось (13.11.2026): Правительство внесло в Госдуму законопроект № 33897-9 о продлении полномочий по ст. 18 № 46-ФЗ на 2027 год; рецепт обновлён; источник x-compliance.ru (вторичный, sozd.duma.gov.ru 502) |


## Заметки для пользователя
- Даты as_of: у kip_stavka, icr_kriterii, programma_1764 as_of = 2026-11-13 (норма подтверждена действующей страницей на эту дату; даты самих документов старше as_of заменяемых фактов). У kovenanty_no_data as_of оставлен 2026-10-09: это статистика обзора, дата прогона была бы неверной.
- splitting_amnesty и parallelnyi_import_srok подтверждены сверкой, но отклонены гейтом даты merge (as_of старых фактов — даты прошлых проверок). Требуют ручного решения.
- Сигналы на ручной разбор (не влиты): МРОТ-2027 = 28 935 руб. принят в I чтении (только вторичка) — кандидат на рецепт-инициативу; ФРП «Проекты развития», по выдаче поиска, теперь 100–2000 млн ₽ (frprf.ru 403); после ФЗ № 104-ФЗ мог устареть факт об отмене льготы МСП по взносам (см. notes_B.md); Минпромторг готовит переформатированный перечень параллельного импорта (вторичка).
- Из этой среды недоступна большая часть российских госсайтов (minfin 503, rosstat/economy/sozd/budget/minpromtorg 502, frprf 403). Нужен прокси с российским IP (`MACRO_PROXY`), иначе бюджетные и росстатовские пункты будут уходить в pending.


## Добор 2026-11-13 через туннель (домашний Keenetic)

- MACRO_PROXY (туннель) поднят. Сверка: 3 кандидата, VERIFIED 3; merge: принято 3 (frp_zaymy, kvota_invalidy_sout, komplaens_platezhi); FUSES OK. Файлы: `runs/2026-W46/addon/`.
- Бюджетные факты budget_expenditure_structure, tech_national_projects, zhkh_spending_trend остаются в pending: нет связной подписанной цитаты с числами закона (см. CHANGELOG).
- Ленты: FEEDS_STATS since=2026-11-06 items=51 new=51 sources_ok=7/7 minfin_last_id=40751. tools/feeds.py не берёт MACRO_PROXY, поэтому запускался с переменными curl https_proxy/HTTPS_PROXY на туннель.


## Добор 2026-11-14: бюджетные факты по открытой части закона

- budget_expenditure_structure и zhkh_spending_trend — по приложению 14 к ФЗ № 426-ФЗ на ГАРАНТе (только открытая часть расходов); tech_national_projects — по прил. № 4 к Бюджетному прогнозу до 2042 г. (распоряжение № 3702-р, столбец 2026 = данные закона).
- Сверка: 3 VERIFIED (1 повтор); merge: принято 3; FUSES OK. Файлы: `runs/2026-W46/addon2/`. Pending по W46 бюджету — 0.
