# Warstwa K6 — kontrola jakosci

*Wygenerowane przez `scripts/make_k6_clean.py`, 2026-08-01.*

Barow M1: **12,927,690**, symboli: 10, zakres 2019-05-06 -> 2026-07-29

## Splity — kazdy kandydat, takze odrzucony

Detektor wymaga DWOCH warunkow naraz: wspolczynnik ceny bliski prostemu
ulamkowi ORAZ wolumen skalujacy sie tym samym czynnikiem. Krach po wynikach
spelnia pierwszy, ale nie drugi — i wlasnie dlatego nie jest korygowany.

| Symbol | Dzien | Cena x | Wolumen x | Wspolczynnik | Werdykt |
|---|---|---|---|---|---|
| AAPL | 2020-08-31 | 3.871 | 4.44 | 4.000 | **SPLIT** |
| AMZN | 2022-06-06 | 19.600 | 13.04 | 20.000 | **SPLIT** |
| AVGO | 2020-03-16 | 1.249 | 1.41 | — | ruch rynku (stosunek ceny 1.249 nie odpowiada zadnem) |
| AVGO | 2024-07-15 | 9.920 | 9.49 | 10.000 | **SPLIT** |
| GOOGL | 2022-07-18 | 20.514 | 18.91 | 20.000 | **SPLIT** |
| META | 2022-02-03 | 1.358 | 4.08 | — | ruch rynku (stosunek ceny 1.358 nie odpowiada zadnem) |
| META | 2022-10-27 | 1.326 | 2.76 | — | ruch rynku (stosunek ceny 1.326 nie odpowiada zadnem) |
| NVDA | 2021-07-20 | 4.038 | 2.32 | 4.000 | **SPLIT** |
| NVDA | 2024-06-10 | 9.935 | 5.62 | 10.000 | **SPLIT** |
| SOXX | 2024-03-07 | 2.900 | 2.94 | 3.000 | **SPLIT** |
| TSLA | 2020-08-31 | 4.441 | 5.49 | 5.000 | **SPLIT** |
| TSLA | 2020-09-08 | 1.267 | 0.72 | — | ruch rynku (stosunek ceny 1.267 nie odpowiada zadnem) |
| TSLA | 2022-08-25 | 3.010 | 2.38 | 3.000 | **SPLIT** |

Przyjetych jako splity: **9**, odrzuconych jako ruch rynku: **4**.

## Sklejenie tickerow — co zostalo odrzucone i dlaczego

Symbol nie identyfikuje spolki jednoznacznie w czasie. Odciecie po dacie
jest obustronne, bo zanieczyszczenie idzie z obu stron:

| Zrodlo | Okres | Ceny | Werdykt |
|---|---|---|---|
| FB | 2019-05 → 2022-06-08 | jak Facebook | **przyjete** jako historia META |
| FB | 2025-2026 (470 rekordow) | inna spolka | odrzucone |
| META | 2021-06-30 → 2022-01-28 (38 920 rekordow) | **11.73-17.17 USD** | odrzucone |
| META | od 2022-06-09 | jak Meta Platforms | **przyjete** |

Wiersz trzeci jest najgrozniejszy: symbol META istnial PRZED przejeciem go
przez Meta Platforms i nalezal do spolki notowanej po ~15 USD, podczas gdy
Facebook kosztowal wtedy 300-380 USD. Wszystkie 147 dni tych notowan pokrywa
sie z dniami, dla ktorych mamy juz FB. Sklejenie po samej nazwie dolozyloby
dzienne zwroty rzedu +/-95% i zatrulo sume wazona skladnikow indeksu.

## Pokrycie per symbol

| Symbol | Barow | Dni | Pierwszy | Ostatni |
|---|---|---|---|---|
| AAPL | 1,455,217 | 1,813 | 2019-05-06 | 2026-07-29 |
| AMZN | 1,334,610 | 1,813 | 2019-05-06 | 2026-07-29 |
| AVGO | 967,314 | 1,813 | 2019-05-06 | 2026-07-29 |
| GOOGL | 1,233,348 | 1,813 | 2019-05-06 | 2026-07-29 |
| META | 1,271,204 | 1,813 | 2019-05-06 | 2026-07-29 |
| MSFT | 1,315,916 | 1,813 | 2019-05-06 | 2026-07-29 |
| NVDA | 1,442,896 | 1,813 | 2019-05-06 | 2026-07-29 |
| QQQ | 1,484,206 | 1,813 | 2019-05-06 | 2026-07-29 |
| SOXX | 831,295 | 1,813 | 2019-05-06 | 2026-07-29 |
| TSLA | 1,591,684 | 1,813 | 2019-05-06 | 2026-07-29 |

Odtworzenie: `python3 scripts/make_k6_clean.py`
