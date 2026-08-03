# Sanity-report danych — NQ 1m

Wygenerowano: 2026-08-03T00:25:11  
Plik: `data/clean/nq_1m_cont.parquet`  
SHA-256: `fd2d18d5c9acd5f640009ac41b60099a6f25150c2546ec038e86532f38ec0550`  
Rozmiar: 35.4 MB

## Podstawowe liczby

- Barów: **2,573,758**
- Zakres: **2019-04-14 22:00:00+00:00** → **2026-07-30 23:59:00+00:00**
- Kolumn w schemacie: **17**
- Dni sesyjnych: **1,887**
- Barów o zerowym wolumenie: **0**

## Gęstość per segment doby

Oczekiwana liczba barów zależy od płynności segmentu — brak bara w cienkiej
godzinie sesji azjatyckiej jest normą, nie defektem (rozdz. 4.2).

| Segment | Barów | Barów/dzień | Wolumen | Bary o wol. 0 |
|---|---:|---:|---:|---:|
| asia | 790,989 | 419 | 60,397,748 | 0 |
| europe | 734,065 | 389 | 105,798,468 | 0 |
| midday | 336,720 | 178 | 322,295,558 | 0 |
| afternoon | 163,440 | 87 | 126,015,059 | 0 |
| globex_open | 113,067 | 60 | 10,357,476 | 0 |
| premarket | 112,913 | 60 | 45,268,166 | 0 |
| rth_open | 112,860 | 60 | 219,466,804 | 0 |
| close | 108,960 | 58 | 121,923,673 | 0 |
| after_hours | 100,743 | 53 | 30,219,529 | 0 |
| maintenance | 1 | 0 | 6 | 0 |

## Pokrycie w czasie

| Rok | Barów | Dni sesyjnych | Barów/dzień |
|---|---:|---:|---:|
| 2019 | 250,879 | 185 | 1356 |
| 2020 | 348,913 | 259 | 1347 |
| 2021 | 353,433 | 259 | 1365 |
| 2022 | 354,113 | 258 | 1373 |
| 2023 | 353,398 | 258 | 1370 |
| 2024 | 355,014 | 259 | 1371 |
| 2025 | 352,564 | 258 | 1367 |
| 2026 | 205,444 | 151 | 1361 |

## Klasyfikacja luk

| Rodzaj luki | Liczba |
|---|---:|
| `none` | 2,570,565 |
| `expected` | 2,349 |
| `anomaly` | 844 |

**Anomalii do przejrzenia: 844**

| Znacznik czasu | Segment | Dzień sesyjny |
|---|---|---|
| 2019-04-14 23:10:00+00:00 | asia | 2019-04-15 |
| 2019-04-15 22:20:00+00:00 | globex_open | 2019-04-16 |
| 2019-04-15 22:52:00+00:00 | globex_open | 2019-04-16 |
| 2019-04-15 23:27:00+00:00 | asia | 2019-04-16 |
| 2019-04-16 23:39:00+00:00 | asia | 2019-04-17 |
| 2019-04-21 22:00:00+00:00 | globex_open | 2019-04-22 |
| 2019-04-22 22:26:00+00:00 | globex_open | 2019-04-23 |
| 2019-04-23 22:59:00+00:00 | globex_open | 2019-04-24 |
| 2019-04-29 04:59:00+00:00 | asia | 2019-04-29 |
| 2019-04-30 22:28:00+00:00 | globex_open | 2019-05-01 |
| 2019-05-01 00:53:00+00:00 | asia | 2019-05-01 |
| 2019-05-01 05:19:00+00:00 | asia | 2019-05-01 |
| 2019-05-14 23:33:00+00:00 | asia | 2019-05-15 |
| 2019-05-24 04:28:00+00:00 | asia | 2019-05-24 |
| 2019-05-26 23:04:00+00:00 | asia | 2019-05-27 |
| 2019-05-27 22:00:00+00:00 | globex_open | 2019-05-28 |
| 2019-05-28 04:12:00+00:00 | asia | 2019-05-28 |
| 2019-05-30 22:19:00+00:00 | globex_open | 2019-05-31 |
| 2019-05-30 22:42:00+00:00 | globex_open | 2019-05-31 |
| 2019-06-04 03:58:00+00:00 | asia | 2019-06-04 |
| 2019-06-13 22:56:00+00:00 | globex_open | 2019-06-14 |
| 2019-06-14 03:38:00+00:00 | asia | 2019-06-14 |
| 2019-06-14 03:44:00+00:00 | asia | 2019-06-14 |
| 2019-06-14 03:47:00+00:00 | asia | 2019-06-14 |
| 2019-06-14 03:53:00+00:00 | asia | 2019-06-14 |
| … | *(jeszcze 819)* | |

## Rolowania i back-adjust

Kontraktów w serii ciągłej: **30**

| Kontrakt | Od | Do | Barów |
|---|---|---|---:|
| NQM9 | 2019-04-15 | 2019-06-13 | 58,452 |
| NQU9 | 2019-06-14 | 2019-09-12 | 88,019 |
| NQZ9 | 2019-09-13 | 2019-12-12 | 88,269 |
| NQH0 | 2019-12-13 | 2020-03-13 | 85,949 |
| NQM0 | 2020-03-16 | 2020-06-12 | 85,535 |
| NQU0 | 2020-06-15 | 2020-09-11 | 87,753 |
| NQZ0 | 2020-09-14 | 2020-12-11 | 88,286 |
| NQH1 | 2020-12-14 | 2021-03-12 | 85,326 |
| NQM1 | 2021-03-15 | 2021-06-11 | 88,035 |
| NQU1 | 2021-06-14 | 2021-09-10 | 89,055 |
| NQZ1 | 2021-09-13 | 2021-12-09 | 87,850 |
| NQH2 | 2021-12-10 | 2022-03-11 | 89,213 |
| NQM2 | 2022-03-14 | 2022-06-10 | 88,077 |
| NQU2 | 2022-06-13 | 2022-09-09 | 88,977 |
| NQZ2 | 2022-09-12 | 2022-12-09 | 89,229 |
| NQH3 | 2022-12-12 | 2023-03-10 | 86,444 |
| NQM3 | 2023-03-13 | 2023-06-09 | 88,984 |
| NQU3 | 2023-06-12 | 2023-09-08 | 88,735 |
| NQZ3 | 2023-09-11 | 2023-12-08 | 89,230 |
| NQH4 | 2023-12-11 | 2024-03-08 | 86,448 |
| NQM4 | 2024-03-11 | 2024-06-14 | 94,967 |
| NQU4 | 2024-06-17 | 2024-09-13 | 88,743 |
| NQZ4 | 2024-09-16 | 2024-12-16 | 90,602 |
| NQH5 | 2024-12-17 | 2025-03-17 | 85,779 |
| NQM5 | 2025-03-18 | 2025-06-13 | 86,697 |
| NQU5 | 2025-06-16 | 2025-09-15 | 90,124 |
| NQZ5 | 2025-09-16 | 2025-12-12 | 87,207 |
| NQH6 | 2025-12-15 | 2026-03-13 | 86,226 |
| NQM6 | 2026-03-16 | 2026-06-12 | 88,988 |
| NQU6 | 2026-06-15 | 2026-07-31 | 46,559 |

Barów z niezerowym przesunięciem back-adjustu: **2,527,199** (98.2%)

## Ciągłość serii po rolowaniu

Kontraktów: **30** · sprawdzonych granic rolowania: **29**

### 1. Niezmiennik arytmetyczny (kontrola rozstrzygająca)

Offset back-adjustu (`px_adj − close`) musi być **stały w obrębie kontraktu**. Zmienny offset oznacza, że korekta była liczona per bar, a nie per kontrakt — czyli że seria ciągła jest fikcją.

- Największy rozrzut offsetu wewnątrz kontraktu: **0.0000000000**
- Próg akceptacji: **1e-06** (margines na reprezentację zmiennoprzecinkową, nie tolerancja pomiarowa)
- Kontraktów z niestałym offsetem: **0** z 30

**PASS**

### 2. Skok serii skorygowanej na granicach rolowania

- Największa pozostała nieciągłość: **349.25 pkt**
- Data: **2026-06-15**, kontrakty: **NQM6 → NQU6**
- Mediana skoku na granicach: **17.50 pkt**

**Kontrola znaku** — rezyduum back-adjustu byłoby systematyczne, czyli miałoby jeden znak i średnią bliską pominiętemu spreadowi:

- Skoków dodatnich: **17 z 29**
- Średni skok ze znakiem: **+5.25 pkt**, t = **+0.34**

Brak przewagi znaku wyklucza systematyczne rezyduum korekty. Podniesiona **wielkość** skoków przy zerowym **kierunku** to podpis zmienności repozycjonowania, nie błędu adjustmentu.

### 3. `engine.roll.verify_continuity` — alarm wstępny

Zgłoszonych granic: **18** z 29.

⚠️ **Ta liczba nie jest miarą jakości danych.** Kryterium funkcji brzmi „skok ≥ |spread|”, a spread rolowania MNQ to kilkanaście–kilkadziesiąt punktów, więc każdy zwykły dzień o ruchu 50+ punktów zostaje zgłoszony. Skrajny przykład z tych danych: 2020-03-13, ruch 659 pkt w szczycie krachu covidowego, opisany jako „back-adjust nie zadziałał” przy spreadzie −13,50 pkt.

Kryterium **nie zostało zmienione**, żeby raport przeszedł — to byłoby dostrajanie progu pod wynik. Rozstrzygająca jest kontrola 1; ta sekcja istnieje, bo PLAN 4.6 wymaga wywołania tej funkcji, a jej ograniczenie ma być jawne, nie ukryte (test regresyjny: `test_ZNANE_OGRANICZENIE_duzy_ruch_rynku_daje_falszywy_alarm`).

### Werdykt ciągłości: **PASS**

## Outliery zakresu

Barów o zakresie > 0.5% w jednej minucie: **1,857** (0.072%)

Dziesięć skrajnych:

| Znacznik | Zakres | Segment |
|---|---:|---|
| 2022-11-10 13:30:00+00:00 | 4.05% | premarket |
| 2022-10-13 12:30:00+00:00 | 3.62% | premarket |
| 2025-04-09 17:19:00+00:00 | 3.35% | midday |
| 2020-03-16 13:45:00+00:00 | 3.08% | rth_open |
| 2022-07-13 12:30:00+00:00 | 3.05% | premarket |
| 2020-03-15 22:00:00+00:00 | 2.93% | globex_open |
| 2022-09-13 12:30:00+00:00 | 2.81% | premarket |
| 2025-04-06 22:00:00+00:00 | 2.37% | globex_open |
| 2020-03-03 15:00:00+00:00 | 2.26% | rth_open |
| 2025-04-07 15:14:00+00:00 | 2.16% | midday |

---

*Raport generowany przez `scripts/data_quality.py` wg specyfikacji PLAN.pdf rozdz. 4.6.*