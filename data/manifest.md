# Manifest danych

Kazda regeneracja `data/clean/` dopisuje wpis. Wersja schematu i data
pobrania sa PRZYPIETE — dostawca zmienil normalizacje GLBX.MDP3 w lipcu
2026, wiec bez tego nie odtworzymy, na czym liczone byly wyniki.

---

## MNQ 2026-07-31T22:19:14

| Pole | Wartosc |
|---|---|
| Plik | `data/clean/mnq_1m_cont.parquet` |
| SHA-256 | `7b9be5aa8cccb1e0debfcf8291bfd1c4c6a12138e723c074fdd4ffb31400f4c2` |
| Rozmiar | 35.2 MB |
| Dataset | GLBX.MDP3, schema ohlcv-1m, stype_in=parent |
| Zakres | 2019-05-05 22:03:00+00:00 -> 2026-07-30 23:59:00+00:00 |
| Barow surowych | 3,812,494 |
| Po deduplikacji | 3,812,494 |
| Barow koncowo | 2,551,265 |
| Kontraktow | 33 |
| Rolowan | 29 |
| Naruszen OHLC (odrzucone) | 0 |
| Ujemny wolumen (odrzucone) | 0 |
| Barow o zerowym wolumenie | 0 |
| Barow w dniach degraded | 10,630 |
| Luk oczekiwanych | 2,322 |
| **Luk anomalnych** | **3,304** |

### Rolowania
- 2019-06-17: MNQM9 -> MNQU9 (spread +27.00)
- 2019-09-13: MNQU9 -> MNQZ9 (spread +24.25)
- 2019-12-13: MNQZ9 -> MNQH0 (spread +28.25)
- 2020-03-13: MNQH0 -> MNQM0 (spread -13.50)
- 2020-06-15: MNQM0 -> MNQU0 (spread -14.25)
- 2020-09-14: MNQU0 -> MNQZ0 (spread -13.00)
- 2020-12-11: MNQZ0 -> MNQH1 (spread -1.00)
- 2021-03-15: MNQH1 -> MNQM1 (spread -9.25)
- 2021-06-11: MNQM1 -> MNQU1 (spread -8.25)
- 2021-09-10: MNQU1 -> MNQZ1 (spread -5.75)
- 2021-12-10: MNQZ1 -> MNQH2 (spread +6.00)
- 2022-03-14: MNQH2 -> MNQM2 (spread -3.25)
- 2022-06-13: MNQM2 -> MNQU2 (spread +29.25)
- 2022-09-12: MNQU2 -> MNQZ2 (spread +83.00)
- 2022-12-12: MNQZ2 -> MNQH3 (spread +116.50)
- 2023-03-13: MNQH3 -> MNQM3 (spread +127.25)
- 2023-06-12: MNQM3 -> MNQU3 (spread +183.75)
- 2023-09-11: MNQU3 -> MNQZ3 (spread +198.25)
- 2023-12-12: MNQZ3 -> MNQH4 (spread +210.50)
- 2024-03-11: MNQH4 -> MNQM4 (spread +245.00)
- 2024-06-17: MNQM4 -> MNQU4 (spread +273.50)
- 2024-09-16: MNQU4 -> MNQZ4 (spread +231.75)
- 2024-12-17: MNQZ4 -> MNQH5 (spread +297.75)
- 2025-03-18: MNQH5 -> MNQM5 (spread +206.25)
- 2025-06-16: MNQM5 -> MNQU5 (spread +227.75)
- 2025-09-16: MNQU5 -> MNQZ5 (spread +238.50)
- 2025-12-16: MNQZ5 -> MNQH6 (spread +236.75)
- 2026-03-17: MNQH6 -> MNQM6 (spread +223.00)
- 2026-06-15: MNQM6 -> MNQU6 (spread +299.75)

---

## NQ 2026-07-31T22:19:57

| Pole | Wartosc |
|---|---|
| Plik | `data/clean/nq_1m_cont.parquet` |
| SHA-256 | `fd2d18d5c9acd5f640009ac41b60099a6f25150c2546ec038e86532f38ec0550` |
| Rozmiar | 35.4 MB |
| Dataset | GLBX.MDP3, schema ohlcv-1m, stype_in=parent |
| Zakres | 2019-04-14 22:00:00+00:00 -> 2026-07-30 23:59:00+00:00 |
| Barow surowych | 3,327,087 |
| Po deduplikacji | 3,327,087 |
| Barow koncowo | 2,573,758 |
| Kontraktow | 34 |
| Rolowan | 29 |
| Naruszen OHLC (odrzucone) | 0 |
| Ujemny wolumen (odrzucone) | 0 |
| Barow o zerowym wolumenie | 0 |
| Barow w dniach degraded | 10,628 |
| Luk oczekiwanych | 2,349 |
| **Luk anomalnych** | **844** |

### Rolowania
- 2019-06-14: NQM9 -> NQU9 (spread +27.25)
- 2019-09-13: NQU9 -> NQZ9 (spread +22.75)
- 2019-12-13: NQZ9 -> NQH0 (spread +26.00)
- 2020-03-16: NQH0 -> NQM0 (spread -16.75)
- 2020-06-15: NQM0 -> NQU0 (spread -11.00)
- 2020-09-14: NQU0 -> NQZ0 (spread -14.50)
- 2020-12-14: NQZ0 -> NQH1 (spread +6.25)
- 2021-03-15: NQH1 -> NQM1 (spread -12.00)
- 2021-06-14: NQM1 -> NQU1 (spread -7.25)
- 2021-09-13: NQU1 -> NQZ1 (spread -7.75)
- 2021-12-10: NQZ1 -> NQH2 (spread +1.50)
- 2022-03-14: NQH2 -> NQM2 (spread -3.25)
- 2022-06-13: NQM2 -> NQU2 (spread +29.00)
- 2022-09-12: NQU2 -> NQZ2 (spread +83.25)
- 2022-12-12: NQZ2 -> NQH3 (spread +116.75)
- 2023-03-13: NQH3 -> NQM3 (spread +122.25)
- 2023-06-12: NQM3 -> NQU3 (spread +183.50)
- 2023-09-11: NQU3 -> NQZ3 (spread +198.75)
- 2023-12-11: NQZ3 -> NQH4 (spread +212.25)
- 2024-03-11: NQH4 -> NQM4 (spread +245.00)
- 2024-06-17: NQM4 -> NQU4 (spread +272.25)
- 2024-09-16: NQU4 -> NQZ4 (spread +230.75)
- 2024-12-17: NQZ4 -> NQH5 (spread +299.75)
- 2025-03-18: NQH5 -> NQM5 (spread +207.25)
- 2025-06-16: NQM5 -> NQU5 (spread +226.75)
- 2025-09-16: NQU5 -> NQZ5 (spread +237.75)
- 2025-12-15: NQZ5 -> NQH6 (spread +247.25)
- 2026-03-16: NQH6 -> NQM6 (spread +217.50)
- 2026-06-15: NQM6 -> NQU6 (spread +302.00)

---

## ES 2026-07-31T22:20:44

| Pole | Wartosc |
|---|---|
| Plik | `data/clean/es_1m_cont.parquet` |
| SHA-256 | `52c320b03562797f80c0d110dcf49dca7ccab7170202a33a03f8f5ed8bdef4c2` |
| Rozmiar | 29.7 MB |
| Dataset | GLBX.MDP3, schema ohlcv-1m, stype_in=parent |
| Zakres | 2019-04-14 22:00:00+00:00 -> 2026-07-30 23:59:00+00:00 |
| Barow surowych | 3,573,156 |
| Po deduplikacji | 3,573,156 |
| Barow koncowo | 2,573,653 |
| Kontraktow | 33 |
| Rolowan | 29 |
| Naruszen OHLC (odrzucone) | 0 |
| Ujemny wolumen (odrzucone) | 0 |
| Barow o zerowym wolumenie | 0 |
| Barow w dniach degraded | 10,625 |
| Luk oczekiwanych | 2,350 |
| **Luk anomalnych** | **1,603** |

### Rolowania
- 2019-06-14: ESM9 -> ESU9 (spread +4.50)
- 2019-09-13: ESU9 -> ESZ9 (spread +2.50)
- 2019-12-13: ESZ9 -> ESH0 (spread +3.50)
- 2020-03-16: ESH0 -> ESM0 (spread -11.00)
- 2020-06-15: ESM0 -> ESU0 (spread -11.00)
- 2020-09-11: ESU0 -> ESZ0 (spread -10.25)
- 2020-12-11: ESZ0 -> ESH1 (spread -7.25)
- 2021-03-12: ESH1 -> ESM1 (spread -8.75)
- 2021-06-11: ESM1 -> ESU1 (spread -9.00)
- 2021-09-10: ESU1 -> ESZ1 (spread -9.00)
- 2021-12-10: ESZ1 -> ESH2 (spread -7.50)
- 2022-03-11: ESH2 -> ESM2 (spread -9.00)
- 2022-06-13: ESM2 -> ESU2 (spread +3.25)
- 2022-09-12: ESU2 -> ESZ2 (spread +18.75)
- 2022-12-12: ESZ2 -> ESH3 (spread +33.00)
- 2023-03-13: ESH3 -> ESM3 (spread +32.00)
- 2023-06-12: ESM3 -> ESU3 (spread +45.25)
- 2023-09-11: ESU3 -> ESZ3 (spread +49.50)
- 2023-12-11: ESZ3 -> ESH4 (spread +52.50)
- 2024-03-11: ESH4 -> ESM4 (spread +62.75)
- 2024-06-17: ESM4 -> ESU4 (spread +67.75)
- 2024-09-16: ESU4 -> ESZ4 (spread +61.00)
- 2024-12-16: ESZ4 -> ESH5 (spread +73.25)
- 2025-03-17: ESH5 -> ESM5 (spread +51.50)
- 2025-06-16: ESM5 -> ESU5 (spread +53.50)
- 2025-09-15: ESU5 -> ESZ5 (spread +57.50)
- 2025-12-15: ESZ5 -> ESH6 (spread +57.25)
- 2026-03-16: ESH6 -> ESM6 (spread +50.50)
- 2026-06-15: ESM6 -> ESU6 (spread +65.25)
