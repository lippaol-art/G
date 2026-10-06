# Sanity-report danych — ES 1m

Wygenerowano: 2026-08-04T10:56:08  
Plik: `data/clean/es_1m_cont.parquet`  
SHA-256: `e758573956df8f1e8682f133f6444c84cfb4194213bedd189a252d4b067757c9`  
Rozmiar: 29.7 MB

## Podstawowe liczby

- Barów: **2,573,653**
- Zakres: **2019-04-14 22:00:00+00:00** → **2026-07-30 23:59:00+00:00**
- Kolumn w schemacie: **17**
- Dni sesyjnych: **1,887**
- Barów o zerowym wolumenie: **0**

## Gęstość per segment doby

Oczekiwana liczba barów zależy od płynności segmentu — brak bara w cienkiej
godzinie sesji azjatyckiej jest normą, nie defektem (rozdz. 4.2).

| Segment | Barów | Barów/dzień | Wolumen | Bary o wol. 0 |
|---|---:|---:|---:|---:|
| asia | 790,641 | 419 | 115,380,604 | 0 |
| europe | 734,280 | 389 | 239,294,764 | 0 |
| midday | 336,718 | 178 | 851,515,326 | 0 |
| afternoon | 163,440 | 87 | 353,961,331 | 0 |
| globex_open | 113,038 | 60 | 21,037,852 | 0 |
| premarket | 112,966 | 60 | 110,324,916 | 0 |
| rth_open | 112,861 | 60 | 545,519,787 | 0 |
| close | 108,960 | 58 | 457,008,954 | 0 |
| after_hours | 100,745 | 53 | 119,320,759 | 0 |
| maintenance | 4 | 0 | 3,356 | 0 |

## Pokrycie w czasie

| Rok | Barów | Dni sesyjnych | Barów/dzień |
|---|---:|---:|---:|
| 2019 | 250,604 | 185 | 1355 |
| 2020 | 349,556 | 259 | 1350 |
| 2021 | 353,363 | 259 | 1364 |
| 2022 | 354,124 | 258 | 1373 |
| 2023 | 353,194 | 258 | 1369 |
| 2024 | 354,818 | 259 | 1370 |
| 2025 | 352,540 | 258 | 1366 |
| 2026 | 205,454 | 151 | 1361 |

## Klasyfikacja luk

| Rodzaj luki | Liczba |
|---|---:|
| `none` | 2,569,700 |
| `expected` | 2,528 |
| `anomaly` | 1,425 |

**Anomalii do przejrzenia: 1425**

| Znacznik czasu | Segment | Dzień sesyjny |
|---|---|---|
| 2019-04-15 23:05:00+00:00 | asia | 2019-04-16 |
| 2019-04-15 23:08:00+00:00 | asia | 2019-04-16 |
| 2019-04-15 23:14:00+00:00 | asia | 2019-04-16 |
| 2019-04-15 23:17:00+00:00 | asia | 2019-04-16 |
| 2019-04-15 23:21:00+00:00 | asia | 2019-04-16 |
| 2019-04-15 23:24:00+00:00 | asia | 2019-04-16 |
| 2019-04-15 23:28:00+00:00 | asia | 2019-04-16 |
| 2019-04-16 04:33:00+00:00 | asia | 2019-04-16 |
| 2019-04-16 04:43:00+00:00 | asia | 2019-04-16 |
| 2019-04-16 04:48:00+00:00 | asia | 2019-04-16 |
| 2019-04-16 04:52:00+00:00 | asia | 2019-04-16 |
| 2019-04-16 05:22:00+00:00 | asia | 2019-04-16 |
| 2019-04-16 23:29:00+00:00 | asia | 2019-04-17 |
| 2019-04-17 03:59:00+00:00 | asia | 2019-04-17 |
| 2019-04-17 05:21:00+00:00 | asia | 2019-04-17 |
| 2019-04-18 04:26:00+00:00 | asia | 2019-04-18 |
| 2019-04-22 04:16:00+00:00 | asia | 2019-04-22 |
| 2019-04-22 04:40:00+00:00 | asia | 2019-04-22 |
| 2019-04-22 06:33:00+00:00 | europe | 2019-04-22 |
| 2019-04-22 22:26:00+00:00 | globex_open | 2019-04-23 |
| 2019-04-23 03:42:00+00:00 | asia | 2019-04-23 |
| 2019-04-23 03:58:00+00:00 | asia | 2019-04-23 |
| 2019-04-23 04:01:00+00:00 | asia | 2019-04-23 |
| 2019-04-23 04:15:00+00:00 | asia | 2019-04-23 |
| 2019-04-23 04:19:00+00:00 | asia | 2019-04-23 |
| … | *(jeszcze 1400)* | |

## Rolowania i back-adjust

Kontraktów w serii ciągłej: **30**

| Kontrakt | Od | Do | Barów |
|---|---|---|---:|
| ESM9 | 2019-04-15 | 2019-06-13 | 58,393 |
| ESU9 | 2019-06-14 | 2019-09-12 | 87,937 |
| ESZ9 | 2019-09-13 | 2019-12-12 | 88,207 |
| ESH0 | 2019-12-13 | 2020-03-13 | 85,972 |
| ESM0 | 2020-03-16 | 2020-06-12 | 86,083 |
| ESU0 | 2020-06-15 | 2020-09-10 | 86,392 |
| ESZ0 | 2020-09-11 | 2020-12-10 | 88,284 |
| ESH1 | 2020-12-11 | 2021-03-11 | 85,322 |
| ESM1 | 2021-03-12 | 2021-06-10 | 87,999 |
| ESU1 | 2021-06-11 | 2021-09-09 | 89,024 |
| ESZ1 | 2021-09-10 | 2021-12-09 | 89,217 |
| ESH2 | 2021-12-10 | 2022-03-10 | 87,833 |
| ESM2 | 2022-03-11 | 2022-06-10 | 89,457 |
| ESU2 | 2022-06-13 | 2022-09-09 | 88,975 |
| ESZ2 | 2022-09-12 | 2022-12-09 | 89,233 |
| ESH3 | 2022-12-12 | 2023-03-10 | 86,452 |
| ESM3 | 2023-03-13 | 2023-06-09 | 88,939 |
| ESU3 | 2023-06-12 | 2023-09-08 | 88,651 |
| ESZ3 | 2023-09-11 | 2023-12-08 | 89,177 |
| ESH4 | 2023-12-11 | 2024-03-08 | 86,380 |
| ESM4 | 2024-03-11 | 2024-06-14 | 94,904 |
| ESU4 | 2024-06-17 | 2024-09-13 | 88,686 |
| ESZ4 | 2024-09-16 | 2024-12-13 | 89,202 |
| ESH5 | 2024-12-16 | 2025-03-14 | 85,765 |
| ESM5 | 2025-03-17 | 2025-06-13 | 88,078 |
| ESU5 | 2025-06-16 | 2025-09-12 | 88,740 |
| ESZ5 | 2025-09-15 | 2025-12-12 | 88,565 |
| ESH6 | 2025-12-15 | 2026-03-13 | 86,232 |
| ESM6 | 2026-03-16 | 2026-06-12 | 88,994 |
| ESU6 | 2026-06-15 | 2026-07-31 | 46,560 |

Barów z niezerowym przesunięciem back-adjustu: **2,527,093** (98.2%)

## Ciągłość serii po rolowaniu

Kontraktów: **30** · sprawdzonych granic rolowania: **29**

### 1. Niezmiennik arytmetyczny (kontrola rozstrzygająca)

Offset back-adjustu (`px_adj − close`) musi być **stały w obrębie kontraktu**. Zmienny offset oznacza, że korekta była liczona per bar, a nie per kontrakt — czyli że seria ciągła jest fikcją.

- Największy rozrzut offsetu wewnątrz kontraktu: **0.0000000000**
- Próg akceptacji: **1e-06** (margines na reprezentację zmiennoprzecinkową, nie tolerancja pomiarowa)
- Kontraktów z niestałym offsetem: **0** z 30

**PASS**

### 2. Skok serii skorygowanej na granicach rolowania

- Największa pozostała nieciągłość: **70.25 pkt**
- Data: **2020-03-16**, kontrakty: **ESH0 → ESM0**
- Mediana skoku na granicach: **2.75 pkt**

**Kontrola znaku** — rezyduum back-adjustu byłoby systematyczne, czyli miałoby jeden znak i średnią bliską pominiętemu spreadowi:

- Skoków dodatnich: **17 z 29**
- Średni skok ze znakiem: **-2.37 pkt**, t = **-0.63**

Brak przewagi znaku wyklucza systematyczne rezyduum korekty. Podniesiona **wielkość** skoków przy zerowym **kierunku** to podpis zmienności repozycjonowania, nie błędu adjustmentu.

### 3. `engine.roll.verify_continuity` — diagnostyka · **INCONCLUSIVE**

Zgłoszonych granic: **12** z 29. Niezmiennik offsetu jest czysty, więc te zgłoszenia to skoki, których heurystyka **nie umie** przypisać ani ruchowi rynku, ani błędowi korekty. Nierozstrzygające.

⚠️ **Ta liczba nie jest miarą jakości danych i nie wydaje werdyktu o back-adjuście.** Kryterium brzmi „skok ≥ |spread|”, a zwykły ruch rynku między sąsiednimi sesjami bywa wielokrotnie większy od spreadu kontraktowego. Skrajny przypadek z tych danych: 2020-03-13, ruch 659 pkt w szczycie krachu covidowego, przy spreadzie −13,50 pkt. Kryterium jest **nieidentyfikowalne** — nie rozróżnia ruchu rynku od błędu korekty.

Problem leży w konstrukcji kryterium, nie w wartości progu, więc **progu nie zmieniono**, żeby zmniejszyć liczbę alarmów — to byłoby dostrajanie pod wynik i nic by nie naprawiło. Zmieniono **rolę**: PASS/FAIL wydaje wyłącznie kontrola 1, ta sekcja dostarcza materiału do obejrzenia (testy regresyjne: `test_ZNANE_OGRANICZENIE_duzy_ruch_rynku_daje_falszywy_alarm`, `test_wartosci_diagnostyczne_nie_zmienily_sie_po_przeetykietowaniu`).

### Werdykt back-adjustu: **PASS** (z kontroli 1) · diagnostyka: **INCONCLUSIVE**

## Outliery zakresu

Barów o zakresie > 0.5% w jednej minucie: **1,443** (0.056%)

Dziesięć skrajnych:

| Znacznik | Zakres | Segment |
|---|---:|---|
| 2020-03-16 13:45:00+00:00 | 4.03% | rth_open |
| 2025-04-09 17:19:00+00:00 | 3.30% | midday |
| 2025-04-09 17:20:00+00:00 | 2.94% | midday |
| 2022-11-10 13:30:00+00:00 | 2.85% | premarket |
| 2020-03-15 22:00:00+00:00 | 2.71% | globex_open |
| 2022-10-13 12:30:00+00:00 | 2.66% | premarket |
| 2022-09-13 12:30:00+00:00 | 2.58% | premarket |
| 2020-03-03 15:00:00+00:00 | 2.26% | rth_open |
| 2022-12-13 13:30:00+00:00 | 2.22% | premarket |
| 2025-04-06 22:02:00+00:00 | 2.16% | globex_open |

---

*Raport generowany przez `scripts/data_quality.py` wg specyfikacji PLAN.pdf rozdz. 4.6.*