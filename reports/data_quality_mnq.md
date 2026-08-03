# Sanity-report danych — MNQ 1m

Wygenerowano: 2026-08-03T00:25:10  
Plik: `data/clean/mnq_1m_cont.parquet`  
SHA-256: `7b9be5aa8cccb1e0debfcf8291bfd1c4c6a12138e723c074fdd4ffb31400f4c2`  
Rozmiar: 35.2 MB

## Podstawowe liczby

- Barów: **2,551,265**
- Zakres: **2019-05-05 22:03:00+00:00** → **2026-07-30 23:59:00+00:00**
- Kolumn w schemacie: **17**
- Dni sesyjnych: **1,873**
- Barów o zerowym wolumenie: **0**

## Gęstość per segment doby

Oczekiwana liczba barów zależy od płynności segmentu — brak bara w cienkiej
godzinie sesji azjatyckiej jest normą, nie defektem (rozdz. 4.2).

| Segment | Barów | Barów/dzień | Wolumen | Bary o wol. 0 |
|---|---:|---:|---:|---:|
| asia | 783,004 | 418 | 170,986,111 | 0 |
| europe | 727,882 | 389 | 252,933,111 | 0 |
| midday | 334,165 | 178 | 657,485,812 | 0 |
| afternoon | 162,180 | 87 | 239,085,977 | 0 |
| premarket | 112,020 | 60 | 96,814,033 | 0 |
| rth_open | 112,019 | 60 | 454,953,916 | 0 |
| globex_open | 111,865 | 60 | 26,555,242 | 0 |
| close | 108,120 | 58 | 189,768,797 | 0 |
| after_hours | 100,009 | 53 | 41,765,076 | 0 |
| maintenance | 1 | 0 | 17 | 0 |

## Pokrycie w czasie

| Rok | Barów | Dni sesyjnych | Barów/dzień |
|---|---:|---:|---:|
| 2019 | 228,342 | 171 | 1335 |
| 2020 | 348,779 | 259 | 1347 |
| 2021 | 353,460 | 259 | 1365 |
| 2022 | 354,133 | 258 | 1373 |
| 2023 | 353,444 | 258 | 1370 |
| 2024 | 355,065 | 259 | 1371 |
| 2025 | 352,587 | 258 | 1367 |
| 2026 | 205,455 | 151 | 1361 |

## Klasyfikacja luk

| Rodzaj luki | Liczba |
|---|---:|
| `none` | 2,545,639 |
| `anomaly` | 3,304 |
| `expected` | 2,322 |

**Anomalii do przejrzenia: 3304**

| Znacznik czasu | Segment | Dzień sesyjny |
|---|---|---|
| 2019-05-05 22:12:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 22:17:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 22:23:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 22:25:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 22:29:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 22:33:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 22:36:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 22:40:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 22:42:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 22:46:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 22:51:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 22:53:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 22:57:00+00:00 | globex_open | 2019-05-06 |
| 2019-05-05 23:00:00+00:00 | asia | 2019-05-06 |
| 2019-05-05 23:04:00+00:00 | asia | 2019-05-06 |
| 2019-05-05 23:06:00+00:00 | asia | 2019-05-06 |
| 2019-05-05 23:09:00+00:00 | asia | 2019-05-06 |
| 2019-05-05 23:12:00+00:00 | asia | 2019-05-06 |
| 2019-05-05 23:19:00+00:00 | asia | 2019-05-06 |
| 2019-05-05 23:21:00+00:00 | asia | 2019-05-06 |
| 2019-05-05 23:23:00+00:00 | asia | 2019-05-06 |
| 2019-05-05 23:33:00+00:00 | asia | 2019-05-06 |
| 2019-05-05 23:37:00+00:00 | asia | 2019-05-06 |
| 2019-05-05 23:40:00+00:00 | asia | 2019-05-06 |
| 2019-05-05 23:43:00+00:00 | asia | 2019-05-06 |
| … | *(jeszcze 3279)* | |

## Rolowania i back-adjust

Kontraktów w serii ciągłej: **30**

| Kontrakt | Od | Do | Barów |
|---|---|---|---:|
| MNQM9 | 2019-05-06 | 2019-06-14 | 39,054 |
| MNQU9 | 2019-06-17 | 2019-09-12 | 85,511 |
| MNQZ9 | 2019-09-13 | 2019-12-12 | 87,811 |
| MNQH0 | 2019-12-13 | 2020-03-12 | 84,341 |
| MNQM0 | 2020-03-13 | 2020-06-12 | 86,822 |
| MNQU0 | 2020-06-15 | 2020-09-11 | 87,760 |
| MNQZ0 | 2020-09-14 | 2020-12-10 | 86,923 |
| MNQH1 | 2020-12-11 | 2021-03-12 | 86,698 |
| MNQM1 | 2021-03-15 | 2021-06-10 | 86,685 |
| MNQU1 | 2021-06-11 | 2021-09-09 | 89,042 |
| MNQZ1 | 2021-09-10 | 2021-12-09 | 89,234 |
| MNQH2 | 2021-12-10 | 2022-03-11 | 89,220 |
| MNQM2 | 2022-03-14 | 2022-06-10 | 88,080 |
| MNQU2 | 2022-06-13 | 2022-09-09 | 88,980 |
| MNQZ2 | 2022-09-12 | 2022-12-09 | 89,235 |
| MNQH3 | 2022-12-12 | 2023-03-10 | 86,458 |
| MNQM3 | 2023-03-13 | 2023-06-09 | 88,995 |
| MNQU3 | 2023-06-12 | 2023-09-08 | 88,754 |
| MNQZ3 | 2023-09-11 | 2023-12-11 | 90,615 |
| MNQH4 | 2023-12-12 | 2024-03-08 | 85,080 |
| MNQM4 | 2024-03-11 | 2024-06-14 | 94,980 |
| MNQU4 | 2024-06-17 | 2024-09-13 | 88,755 |
| MNQZ4 | 2024-09-16 | 2024-12-16 | 90,615 |
| MNQH5 | 2024-12-17 | 2025-03-17 | 85,785 |
| MNQM5 | 2025-03-18 | 2025-06-13 | 86,697 |
| MNQU5 | 2025-06-16 | 2025-09-15 | 90,135 |
| MNQZ5 | 2025-09-16 | 2025-12-15 | 88,590 |
| MNQH6 | 2025-12-16 | 2026-03-16 | 86,235 |
| MNQM6 | 2026-03-17 | 2026-06-12 | 87,615 |
| MNQU6 | 2026-06-15 | 2026-07-31 | 46,560 |

Barów z niezerowym przesunięciem back-adjustu: **2,504,705** (98.2%)

## Ciągłość serii po rolowaniu

Kontraktów: **30** · sprawdzonych granic rolowania: **29**

### 1. Niezmiennik arytmetyczny (kontrola rozstrzygająca)

Offset back-adjustu (`px_adj − close`) musi być **stały w obrębie kontraktu**. Zmienny offset oznacza, że korekta była liczona per bar, a nie per kontrakt — czyli że seria ciągła jest fikcją.

- Największy rozrzut offsetu wewnątrz kontraktu: **0.0000000000**
- Próg akceptacji: **1e-06** (margines na reprezentację zmiennoprzecinkową, nie tolerancja pomiarowa)
- Kontraktów z niestałym offsetem: **0** z 30

**PASS**

### 2. Skok serii skorygowanej na granicach rolowania

- Największa pozostała nieciągłość: **354.25 pkt**
- Data: **2026-06-15**, kontrakty: **MNQM6 → MNQU6**
- Mediana skoku na granicach: **13.00 pkt**

**Kontrola znaku** — rezyduum back-adjustu byłoby systematyczne, czyli miałoby jeden znak i średnią bliską pominiętemu spreadowi:

- Skoków dodatnich: **15 z 29**
- Średni skok ze znakiem: **+4.17 pkt**, t = **+0.28**

Brak przewagi znaku wyklucza systematyczne rezyduum korekty. Podniesiona **wielkość** skoków przy zerowym **kierunku** to podpis zmienności repozycjonowania, nie błędu adjustmentu.

### 3. `engine.roll.verify_continuity` — alarm wstępny

Zgłoszonych granic: **17** z 29.

⚠️ **Ta liczba nie jest miarą jakości danych.** Kryterium funkcji brzmi „skok ≥ |spread|”, a spread rolowania MNQ to kilkanaście–kilkadziesiąt punktów, więc każdy zwykły dzień o ruchu 50+ punktów zostaje zgłoszony. Skrajny przykład z tych danych: 2020-03-13, ruch 659 pkt w szczycie krachu covidowego, opisany jako „back-adjust nie zadziałał” przy spreadzie −13,50 pkt.

Kryterium **nie zostało zmienione**, żeby raport przeszedł — to byłoby dostrajanie progu pod wynik. Rozstrzygająca jest kontrola 1; ta sekcja istnieje, bo PLAN 4.6 wymaga wywołania tej funkcji, a jej ograniczenie ma być jawne, nie ukryte (test regresyjny: `test_ZNANE_OGRANICZENIE_duzy_ruch_rynku_daje_falszywy_alarm`).

### Werdykt ciągłości: **PASS**

## Outliery zakresu

Barów o zakresie > 0.5% w jednej minucie: **1,945** (0.076%)

Dziesięć skrajnych:

| Znacznik | Zakres | Segment |
|---|---:|---|
| 2022-11-10 13:30:00+00:00 | 3.41% | premarket |
| 2025-04-09 17:19:00+00:00 | 3.30% | midday |
| 2020-03-16 13:45:00+00:00 | 2.99% | rth_open |
| 2022-10-13 12:30:00+00:00 | 2.82% | premarket |
| 2022-07-13 12:30:00+00:00 | 2.80% | premarket |
| 2022-09-13 12:30:00+00:00 | 2.70% | premarket |
| 2025-04-06 22:00:00+00:00 | 2.55% | globex_open |
| 2020-03-03 15:00:00+00:00 | 2.27% | rth_open |
| 2022-12-13 13:30:00+00:00 | 2.13% | premarket |
| 2025-04-07 15:14:00+00:00 | 2.13% | midday |

---

*Raport generowany przez `scripts/data_quality.py` wg specyfikacji PLAN.pdf rozdz. 4.6.*