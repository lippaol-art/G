# Manifest danych

Kazda regeneracja `data/clean/` dopisuje wpis. Wersja schematu i data
pobrania sa PRZYPIETE — dostawca zmienil normalizacje GLBX.MDP3 w lipcu
2026, wiec bez tego nie odtworzymy, na czym liczone byly wyniki.

---

## MNQ 2026-07-31T21:36:10

| Pole | Wartosc |
|---|---|
| Plik | `data/clean/mnq_1m_cont.parquet` |
| SHA-256 | `a8c59a0961ce390bd4727524731a29378c354572fef57e7ee7f7713c4cbe04a0` |
| Rozmiar | 16.4 MB |
| Dataset | GLBX.MDP3, schema ohlcv-1m, stype_in=parent |
| Zakres | 2019-05-05 22:03:00+00:00 -> 2026-07-30 17:58:00+00:00 |
| Barow surowych | 3,812,494 |
| Po deduplikacji | 3,812,494 |
| Barow koncowo | 868,307 |
| Kontraktow | 33 |
| Rolowan | 30 |
| Naruszen OHLC (odrzucone) | 0 |
| Ujemny wolumen (odrzucone) | 0 |
| Barow o zerowym wolumenie | 0 |
| Barow w dniach degraded | 5,433 |
| Luk oczekiwanych | 790 |
| **Luk anomalnych** | **57,840** |

### Rolowania
- 2019-06-17: MNQM9 -> MNQU9 (spread +27.00)
- 2019-09-13: MNQU9 -> MNQZ9 (spread +24.25)
- 2019-06-20: MNQZ9 -> MNQM0 (spread +92.75)
- 2019-08-01: MNQM0 -> MNQH0 (spread +32.00)
- 2020-03-03: MNQU0 -> MNQZ0 (spread +24.50)
- 2020-12-11: MNQZ0 -> MNQH1 (spread -1.00)
- 2020-07-23: MNQH1 -> MNQM1 (spread -5.75)
- 2020-08-24: MNQM1 -> MNQU1 (spread +34.00)
- 2020-11-13: MNQU1 -> MNQZ1 (spread +25.00)
- 2021-12-10: MNQZ1 -> MNQH2 (spread +6.00)
- 2022-03-14: MNQH2 -> MNQM2 (spread -3.25)
- 2022-06-13: MNQM2 -> MNQU2 (spread +29.25)
- 2021-09-20: MNQU2 -> MNQZ2 (spread -400.00)
- 2022-02-02: MNQZ2 -> MNQH3 (spread +217.25)
- 2022-03-21: MNQH3 -> MNQM3 (spread +100.00)
- 2023-06-12: MNQM3 -> MNQU3 (spread +183.75)
- 2022-12-05: MNQU3 -> MNQZ3 (spread +166.50)
- 2023-02-03: MNQZ3 -> MNQH4 (spread +157.75)
- 2023-05-25: MNQH4 -> MNQM4 (spread +175.00)
- 2023-08-31: MNQM4 -> MNQU4 (spread +230.00)
- 2023-11-03: MNQU4 -> MNQZ4 (spread +140.00)
- 2024-01-12: MNQZ4 -> MNQH5 (spread +95.00)
- 2024-04-26: MNQH5 -> MNQM5 (spread +155.50)
- 2024-10-21: MNQM5 -> MNQU5 (spread +95.00)
- 2024-10-29: MNQU5 -> MNQZ5 (spread +0.00)
- 2025-01-31: MNQZ5 -> MNQH6 (spread +617.00)
- 2025-04-09: MNQH6 -> MNQM6 (spread -836.75)
- 2026-06-15: MNQM6 -> MNQU6 (spread +299.75)
- 2026-03-20: MNQZ6 -> MNQH7 (spread +444.50)
- 2026-05-08: MNQH7 -> MNQM7 (spread +96.25)

---

## MNQ 2026-07-31T21:38:36

| Pole | Wartosc |
|---|---|
| Plik | `data/clean/mnq_1m_cont.parquet` |
| SHA-256 | `633afc77779cd89c462d36b71f51252ac2ae2da1553794d7054f25879eb626a3` |
| Rozmiar | 1.7 MB |
| Dataset | GLBX.MDP3, schema ohlcv-1m, stype_in=parent |
| Zakres | 2026-01-27 16:19:00+00:00 -> 2026-07-30 23:59:00+00:00 |
| Barow surowych | 3,812,494 |
| Po deduplikacji | 3,812,494 |
| Barow koncowo | 82,229 |
| Kontraktow | 33 |
| Rolowan | 30 |
| Naruszen OHLC (odrzucone) | 0 |
| Ujemny wolumen (odrzucone) | 0 |
| Barow o zerowym wolumenie | 0 |
| Barow w dniach degraded | 1 |
| Luk oczekiwanych | 57 |
| **Luk anomalnych** | **31** |

### Rolowania
- 2026-05-08: MNQH7 -> MNQM7 (spread +96.25)
- 2019-06-17: MNQM9 -> MNQU9 (spread +27.00)
- 2019-09-13: MNQU9 -> MNQZ9 (spread +24.25)
- 2019-12-13: MNQZ9 -> MNQH0 (spread +28.25)
- 2020-03-13: MNQH0 -> MNQM0 (spread -13.50)
- 2019-11-15: MNQM0 -> MNQU0 (spread +22.00)
- 2020-03-03: MNQU0 -> MNQZ0 (spread +24.50)
- 2020-12-11: MNQZ0 -> MNQH1 (spread -1.00)
- 2020-07-23: MNQH1 -> MNQM1 (spread -5.75)
- 2020-08-24: MNQM1 -> MNQU1 (spread +34.00)
- 2020-11-13: MNQU1 -> MNQZ1 (spread +25.00)
- 2021-12-10: MNQZ1 -> MNQH2 (spread +6.00)
- 2022-03-14: MNQH2 -> MNQM2 (spread -3.25)
- 2022-06-13: MNQM2 -> MNQU2 (spread +29.25)
- 2021-09-20: MNQU2 -> MNQZ2 (spread -400.00)
- 2022-02-02: MNQZ2 -> MNQH3 (spread +217.25)
- 2022-03-21: MNQH3 -> MNQM3 (spread +100.00)
- 2023-06-12: MNQM3 -> MNQU3 (spread +183.75)
- 2022-12-05: MNQU3 -> MNQZ3 (spread +166.50)
- 2023-02-03: MNQZ3 -> MNQH4 (spread +157.75)
- 2023-05-25: MNQH4 -> MNQM4 (spread +175.00)
- 2023-08-31: MNQM4 -> MNQU4 (spread +230.00)
- 2023-11-03: MNQU4 -> MNQZ4 (spread +140.00)
- 2024-01-12: MNQZ4 -> MNQH5 (spread +95.00)
- 2024-04-26: MNQH5 -> MNQM5 (spread +155.50)
- 2024-10-21: MNQM5 -> MNQU5 (spread +95.00)
- 2024-10-29: MNQU5 -> MNQZ5 (spread +0.00)
- 2025-01-31: MNQZ5 -> MNQH6 (spread +617.00)
- 2025-04-09: MNQH6 -> MNQM6 (spread -836.75)
- 2026-06-15: MNQM6 -> MNQU6 (spread +299.75)

---

## MNQ 2026-07-31T21:40:41

| Pole | Wartosc |
|---|---|
| Plik | `data/clean/mnq_1m_cont.parquet` |
| SHA-256 | `394b6ce3b19c2576b22ae394f193626edbc87707048034c748a27c804cc53fdc` |
| Rozmiar | 47.8 MB |
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

## MNQ 2026-07-31T21:43:48

| Pole | Wartosc |
|---|---|
| Plik | `data/clean/mnq_1m_cont.parquet` |
| SHA-256 | `394b6ce3b19c2576b22ae394f193626edbc87707048034c748a27c804cc53fdc` |
| Rozmiar | 47.8 MB |
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
