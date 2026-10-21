# Архів

Перенесено 29.09.2026 під час аудиту 4 (`AUDYT-4.md`). Файли не для роботи:
у них старі формулювання, чинні рішення — у `RISHENNYA.md`, порядок робіт — у
`PLAN-ZAHALNYI.md`. Посилання на ці файли в інших документах ведуть сюди.

| Що | Файли |
|---|---|
| Стан і перелік робіт до 25.09 | `STAN.md`, `STAN-CHATU.md`, `ZAVDANNYA.md` |
| Виконані завдання | `ZAVDANNYA-KROK9.md`, `ZAVDANNYA-DYZAIN.md`, `ZAVDANNYA-KOLIR.md`, `ZAVDANNYA-MAPLIBRE.md`, `ZAVDANNYA-PANEL.md`, `ZAVDANNYA-ADRESY.md`, `ZAVDANNYA-TEKSTY.md` |
| Виконані плани | `PLAN-TEKSTY.md`, `PLAN-ZVITY.md` |
| Аудити, знахідки яких закрито | `AUDYT-2-VYGLIAD.md`, `AUDYT-3-ZRUCHNIST.md`, `POMYLKA-ADRES.md` |
| Звіти виконавців | `ZVIT-TEKSTY-1..3.md`, `ZVIT-SUT.md`, `ZVIT-GPT.md`, `ZVIT-GPT-SUT.md` |
| Інструкція першого налаштування GitHub | `GITHUB.md` |
| Затверджені макети й знімки | `maket/` |
| Виконані завдання й звіти (перенесено 07.10.2026, ZAVDANNYA-33, А5) | `ZAVDANNYA-30.md`, `ZVIT-30.md`, `ZAVDANNYA-31.md`, `ZAVDANNYA-PROBLEMY-29.md` |
| Плани, що виконані чи перейшли в інше місце (07.10) | `PLAN-KROK7.md` (модель ризику — тепер METODYKA, розд. 4–5), `PLAN-BAZA.md` (план спільної бази — у приватному `dani-edrsr`, після 1.0) |
| Аудит 4 і передача чату «Проблеми» (07.10) | `AUDYT-4.md`, `PEREDACHA-PROBLEMY.md` |
| Інструкція про токен спільної бази — перехід скасовано (07.10, RISHENNYA 36.11) | `INSTRUKTSIYA-DANI.md` |
| Чеклист «Карта 1.0» — злито в `SPECYFIKATSIYA.md` (20.10, RISHENNYA 36.31.3); «Після 1.0» — у PLAN-ZAHALNYI, «Відкладено» | `KARTA-1.0.md` |
| Виконані завдання й звіти, аудит 5 (21.10, RISHENNYA 36.30.4, S-Н.7) | `ZAVDANNYA-32.md` … `ZAVDANNYA-37.md`, `ZVIT-32.md`, `ZVIT-33.md`, `AUDYT-5.md` |
| Разові скрипти (21.10, 36.30.5) | `kod/diag_1551.py`, `kod/diag_faktory.py` (PIDKHID, «чинники»), `kod/step0d_population.py` |

Видалено тоді ж (є в історії git): локальні `.bat` старого ручного конвеєра
(`0d`, `1`, `2`, `2b`, `2c`, `4`, `DIAGNOSTYKA`, `FABULY`, `ONOVYTY`,
`PERERAHUVATY`, `ROZVIDKA-TEKSTIV`, `ZNIMOK`) — усе це тепер робить GitHub
Actions; разові діагностики адрес `src/diag_addr*.py`, `src/diag_case.py`,
`src/diag_fabula.py`; `src/sut.py` (суть фабули відкочено 24.09);
`src/export_snapshot.py` (знімок бази пише сам `step1_download.py`);
`src/step6_base.py`, `step6_intro.py`, `step6_research.py`, `step6_state.py`,
`step6_theme.py` — генератори старих документів, замінені `step6_zvity.py`
(збірку перевірено: карта й чотири звіти збираються без змін).
Лишилися `3-MAP.bat`, `PODYVYTYSYA.bat`, `PEREVIRKA.bat` — ними перевіряють
карту локально (CLAUDE.md).

07.10.2026: `1551-SKHOZHI-UMOVY.md` — не в архів, а в `doslidzhennya/` (його пише
`problems.py --1551-md`). 21.10 туди ж — `NAPRYAM-PROBLEMY.md` (на його
додаток Б посилається публічний звіт «Проблеми»), `ZVIT-KROK7.md` і
`ZVIT-1551-ZAKONOMIRNOSTI.md` (їх пише workflow «Оновлення карти», тепер у
`doslidzhennya/`): вони чинні, тож не в архів, але й не в корінь (S-Н.7).
