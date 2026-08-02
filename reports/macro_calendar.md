# Kalendarz publikacji makro — BLS i Federal Reserve

*Wygenerowane przez `scripts/build_macro.py`, 2026-08-02. Zakres 2019-05-06 → 2026-07-30.*

**310 zdarzen w probie podstawowej** (321 w kalendarzu lacznie).

Zrodla urzedowe i darmowe; **godzina pochodzi z dokumentu, nie z konwencji**.
Harmonogram BLS podaje ja w osobnej kolumnie, strona komunikatu FOMC we frazie
"For release at 2:00 p.m.". Uzasadnienie: docstring `engine/macro.py`.

## 1. Pokrycie

| Typ | N | Oczekiwane | Zrodlo |
|---|---|---|---|
| CPI | 85 | 87 | BLS |
| PPI | 86 | 87 | BLS |
| NFP | 82 | 87 | BLS |
| FOMC (komunikat) | 57 | 58 | Federal Reserve |

| Rok | CPI | PPI | NFP | FOMC |
|---|---|---|---|---|
| 2019 | 8 | 8 | 7 | 5 |
| 2020 | 11 | 12 | 12 | 7 |
| 2021 | 12 | 12 | 11 | 8 |
| 2022 | 12 | 12 | 12 | 8 |
| 2023 | 12 | 12 | 11 | 8 |
| 2024 | 12 | 12 | 12 | 8 |
| 2025 | 11 | 10 | 11 | 8 |
| 2026 | 7 | 8 | 6 | 5 |

## 2. Godziny publikacji

| Godzina ET | N |
|---|---|
| 08:30 | 253 |
| 14:00 | 57 |

Stalosc godzin jest **kontrola strefy czasowej**: publikacje maja stala godzine
**scienna**, a nie staly offset UTC. Konwersja przez `America/New_York` obsluguje
zmiane czasu sama; recznie wpisany offset bylby bledny przez pol roku.

## 3. Dwa etapy posiedzenia FOMC

**56 z 57 posiedzen ma konferencje prasowa** okolo
30 minut po komunikacie.

Ma to bezposrednia konsekwencje dla H003: okno 5-60 minut po komunikacie
**obejmuje w calosci konferencje**, wiec mierzyloby mieszanke dwoch zdarzen
informacyjnych. Karta mierzy wynik **przed konferencja**, a decyzja zapadla
przed policzeniem czegokolwiek.

## 4. Dzialania nadzwyczajne — wykluczone z proby podstawowej

**7 komunikatow poza harmonogramem posiedzen.** Wykluczone
z proby podstawowej **z mechanizmu, nie z danych**: karta bada rynek, ktory
kompresuje sie przed ZNANYM terminem publikacji, a dzialanie nadzwyczajne
jest z definicji nieoczekiwane — okna rownowagi w sensie karty nie ma.

| Data | Konferencja prasowa |
|---|---|
| 2019-10-11 | nie |
| 2020-03-03 | tak |
| 2020-03-15 | tak |
| 2020-03-23 | nie |
| 2020-03-31 | nie |
| 2020-08-27 | nie |
| 2025-08-22 | nie |

**Uwaga na pulapke:** obecnosc konferencji prasowej NIE odroznia posiedzen
planowych od nadzwyczajnych — marcowe ciecia awaryjne 2020 mialy konferencje.
Rozroznienie bierzemy z listy posiedzen na kalendarzu Fedu.

## 5. Kontrola jakosci

| Kontrola | Wynik |
|---|---|
| Duplikaty (typ, data) | 0 |
| Zdarzenia w dniu bez sesji | 5 |
| Kolizje: dwie publikacje tego samego dnia i o tej samej godzinie | 0 |
| Godziny inne niz 08:30 / 14:00 | 0 |
| Zdarzenia w dniu SKROCONYM (zostaja w probie, oznaczone) | 1 |

Zdarzenia w dniu bez sesji (raportowane, nie usuwane):

- FOMC 2020-03-15 17:00 ET
- CPI 2020-04-10 08:30 ET
- NFP 2021-04-02 08:30 ET
- NFP 2023-04-07 08:30 ET
- NFP 2026-04-03 08:30 ET

---

Dane: `data/clean/macro_events.csv`. Odtworzenie: `python3 scripts/build_macro.py`
