# Weryfikacja założenia A3 — halt CME 15:15–15:30 CT

Granica z dokumentacji CME: **2021-06-27** (halt zniesiony).
Okno w czasie ET: **16:15–16:30**.

A3 było jedynym założeniem kalendarzowym przyjętym z dokumentacji bez
sprawdzenia na własnych danych (`docs/ZALOZENIA.md`). To go zamyka.

## Problem identyfikacyjny

Dane M1 **nie mogą w zasadzie** odróżnić formalnego zamknięcia od braku
transakcji — Databento nie drukuje bara przy zerowym obrocie (założenie B4).
Sam brak barów w oknie haltu niczego by nie dowodził.

Rozstrzyga dopiero **kontrola sąsiedztwa**: te same dni, okna 15 minut tuż
przed i tuż po oknie haltu. Gęsto wypełnione sąsiedztwo przy pustym oknie
czyni wyjaśnienie „akurat nie było transakcji” ilościowo nie do utrzymania.

## Wynik

Gęstość = udział wypełnionych minut z 15 możliwych na dzień.

| Instr. | Okres | Dni | Barów 16:15–16:30 | Dni z barem | Gęstość okna | Gęstość 16:00–16:15 |
|---|---|---:|---:|---:|---:|---:|
| MNQ | < 2021-06-27 | 555 | 4 | 4 (0.7%) | **0.05%** | 96.2% |
| MNQ | ≥ 2021-06-27 | 1,318 | 19,020 | 1,268 (96.2%) | **96.21%** | 96.2% |
| NQ | < 2021-06-27 | 569 | 4 | 4 (0.7%) | **0.05%** | 96.3% |
| NQ | ≥ 2021-06-27 | 1,318 | 19,020 | 1,268 (96.2%) | **96.21%** | 96.2% |
| ES | < 2021-06-27 | 569 | 6 | 6 (1.1%) | **0.07%** | 96.3% |
| ES | ≥ 2021-06-27 | 1,318 | 19,020 | 1,268 (96.2%) | **96.21%** | 96.2% |

Kontrast jest kategoryczny: przed granicą okno haltu jest puste w ~99%
dni, podczas gdy sąsiadujące okno 16:00–16:15 **tych samych dni** jest
wypełnione niemal w komplecie. Po granicy okno haltu ma dokładnie tę samą
gęstość co sąsiedztwo.

## Wyjątki przed granicą — wszystkie na krawędzi okna

| Instrument | Data | Minuta ET | Wolumen |
|---|---|---:|---:|
| MNQ | 2020-03-30 | 16:29 | 2 |
| MNQ | 2020-03-31 | 16:29 | 35 |
| MNQ | 2020-04-01 | 16:29 | 20 |
| MNQ | 2020-04-02 | 16:29 | 25 |
| NQ | 2019-11-07 | 16:15 | 1 |
| NQ | 2020-03-30 | 16:29 | 5 |
| NQ | 2020-03-31 | 16:29 | 62 |
| NQ | 2020-04-01 | 16:29 | 16 |
| ES | 2019-05-30 | 16:15 | 5 |
| ES | 2019-11-20 | 16:15 | 8 |
| ES | 2020-03-30 | 16:29 | 269 |
| ES | 2020-03-31 | 16:29 | 165 |
| ES | 2020-04-01 | 16:29 | 259 |
| ES | 2020-04-02 | 16:29 | 103 |

**Żaden wyjątek nie leży w środku okna.** Wszystkie przypadają na minutę
16:15 (pierwsza minuta przerwy) albo 16:29 (ostatnia przed wznowieniem),
z wolumenem rzędu jednostek do kilkuset. To wydruki na krawędzi przerwy —
dokładnie to, jak halt wygląda w rozdzielczości minutowej.

## Dni po granicy bez barów w oknie

- **MNQ**: 50 dni; mediana barów w dobie **1140** wobec **1380** w dniu typowym. Przykłady: 2021-07-05, 2021-09-06, 2021-11-25, 2021-11-26, 2022-01-17, 2022-02-21.
- **NQ**: 50 dni; mediana barów w dobie **1140** wobec **1380** w dniu typowym. Przykłady: 2021-07-05, 2021-09-06, 2021-11-25, 2021-11-26, 2022-01-17, 2022-02-21.
- **ES**: 50 dni; mediana barów w dobie **1140** wobec **1380** w dniu typowym. Przykłady: 2021-07-05, 2021-09-06, 2021-11-25, 2021-11-26, 2022-01-17, 2022-02-21.

To święta amerykańskie (Labor Day, Good Friday, MLK, Presidents Day,
Memorial Day, 4 lipca, dzień żałoby narodowej 2025-01-09) — sesja kończy
się przed 16:15, więc brak barów jest oczekiwany.

## Werdykt

**A3 potwierdzone empirycznie na MNQ, NQ i ES.**

Granica z dokumentacji CME zgadza się z danymi co do dnia, a kontrola
sąsiedztwa wyklucza wyjaśnienie „brak transakcji”. Zachowuję jednak
ograniczenie dowodowe: **bary M1 nie dowodzą formalnego zamknięcia**,
tylko braku obrotu nieodróżnialnego od niego przy tej rozdzielczości.
Dowodem wprost byłby komunikat CME albo dane `trades`/statusowe.

W praktyce różnica nie ma znaczenia dla projektu: silnik i tak nie może
wykonać zlecenia bez wolumenu (`bar.tradeable`), więc konsekwencja jest
identyczna niezależnie od tego, która interpretacja jest formalnie prawdziwa.

Granica zabezpieczona testem
`tests/test_sessions.py::TestHaltHistoryczny::test_granica_A3_zgodna_z_danymi`.

---

*Raport generowany przez `scripts/verify_a3_halt.py`. Zero zużytych prób —
kontrola danych, nie badanie P&L.*