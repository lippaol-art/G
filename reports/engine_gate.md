# Bramka silnika — PLAN.pdf rozdz. 5.6

Wygenerowane przez `scripts/engine_gate_report.py`. Kryterium GO/NO-GO dla
calego projektu: bez kompletu zielonych nie powstaje zaden backtest hipotezy.

| Pole | Wartosc |
|---|---|
| Data | 2026-08-01T09:19:30+00:00 |
| Instrument | MNQ, kontrakt ciagly (px_adj) |
| Barow M1 | 2,551,265 |
| Zakres | 2019-05-05 22:03:00+00:00 -> 2026-07-30 23:59:00+00:00 |

## 1. Test zerowej przewagi

Losowy kierunek, losowy bracket +-10..40 pkt, **przed kosztami**. Moneta nie
wie nic o rynku, wiec kazda dodatnia przewaga jest przeciekiem informacji.
Lekko ujemna sredniej oczekujemy: regula "SL wygrywa" w barze spornym i wymog
przebicia limitu o tick to swiadome konserwatyzmy z tabeli 5.4.

| Seed | Transakcji | Srednia [USD] | t | Suma [USD] | Bary sporne |
|---|---|---|---|---|---|
| 1 | 2,326 | -1.26 | -1.14 | -2,927 | 13 |
| 2 | 2,247 | -0.83 | -0.74 | -1,863 | 3 |
| 3 | 2,236 | -1.94 | -1.63 | -4,346 | 5 |
| 7 | 2,357 | -0.93 | -0.85 | -2,189 | 9 |
| 42 | 2,328 | -0.63 | -0.57 | -1,471 | 6 |
| **lacznie** | **11,494** | **-1.11** | **-2.21** | **-12,796** | |

**Werdykt:** t = -2.21 przy progu |t| < 3.0. Brak sladu przewagi u strategii, ktora nie moze jej miec.

### Skad bierze sie ujemne odchylenie

Wynik lekko ujemny nie jest usterka i nie wolno go "naprawiac" — rozklad
ponizej pokazuje, ze pochodzi w calosci z mechanizmow, ktore mialy go
wywolac. Gdyby te pozycje sie nie zgadzaly, ujemna srednia oznaczalaby cos
innego niz konserwatyzm i wymagalaby sledztwa.

| Powod wyjscia | Transakcji | Udzial | Srednia [USD] | Suma [USD] |
|---|---|---|---|---|
| `stop_loss` | 5,706 | 49.6% | -50.52 | -288,295 |
| `take_profit` | 5,682 | 49.4% | +49.77 | +282,806 |
| `stop_gap` | 106 | 0.9% | -68.94 | -7,308 |

`stop_gap` to 0.9% transakcji, w ktorych open bara byl juz
poza stopem — wyjscie liczy sie po tym open, nie po cenie stopa (tabela 5.4).
Srednia strata jest tam wyrazniej gorsza od nominalu stopa i **tak ma byc**:
luka to realny koszt trzymania pozycji przez przerwe w handlu. Drugie zrodlo
to wymog przebicia limitu o tick przy jednoczesnym wyzwalaniu stopa samym
dotknieciem — asymetria swiadoma, opisana w tabeli 5.4.

## 2. Test znanego efektu — asymetria overnight/intraday

Linijka, nie strategia. Asymetria overnight/intraday na indeksach USA jest
jednym z najlepiej udokumentowanych faktow empirycznych (Cooper-Cliff-Gulen
2008, Lou-Polk-Skouras 2019). Silnik ma ja odtworzyc **co do znaku i rzedu
wielkosci** — inaczej nie mierzy rynku.

| Noga | Dni | Suma [pkt] | Srednio [pkt/dzien] | t |
|---|---|---|---|---|
| Overnight (16:00 -> 09:30) | 1,801 | +13,193 | +7.33 | +2.20 |
| Intraday (09:30 -> 16:00) | 1,802 | +3,956 | +2.20 | +0.51 |

**Udzial nocy w calosci ruchu: 76.9%** (prog akceptacji 50-150%).

> **To nie jest wynik badawczy i nie zuzywa licznika prob.** Pytanie, czy dryf
> nocny wygasl po 2020 roku (teza audytu 3 za NY Fed), wymaga rozbicia na lata
> i nalezy do badania W001. Tutaj patrzymy na caly zakres, bo linijka ma byc
> stabilna, nie czula na rezim.

## 3. Test symetrii long <-> short

Wyjscie czasowe (30 min), bez SL i TP — z bracketem lustro nie moglo by byc
dokladne, bo bar dotykajacy obu poziomow rozstrzygamy na korzysc stopa dla
obu stron naraz. Ta asymetria jest zamierzona; mieszanie jej z testem
symetrii ksiegowania zamazaloby obie rzeczy.

| Wariant | Transakcji | Suma [USD] |
|---|---|---|
| oryginal | 1,980 | +3184.00 |
| lustro   | 1,980 | -3184.00 |

**Maksymalny rozjazd pojedynczej transakcji: 0.0 USD** (wymagane: dokladnie 0).

## 4. Test determinizmu

Cala konstrukcja DSR opiera sie na zliczaniu prob. Gdyby ta sama proba
uruchomiona dwa razy dawala dwie liczby, licznik prob mierzylby fikcje.

| Przebieg | Seed | SHA-256 listy transakcji |
|---|---|---|
| A | 2024 | `c5da5e5ee580c7ed42d8236846bea3f1` |
| B | 2024 | `c5da5e5ee580c7ed42d8236846bea3f1` |
| C | 2025 | `b782736182a4dd29d631adf6d1ad5dfd` |

A == B: **True** (wymagane) — A != C: **True** (kontrola, ze ziarno w ogole dziala).

---

## Werdykt bramki

**GO.** Cztery testy z rozdz. 5.6 spelnione na pelnym zakresie danych.
Silnik moze byc uzywany do backtestow hipotez. Kolejny krok wg planu:
badanie W001 (zanik dryfu nocnego), potem partia 0 benchmarkow B01-B04.

Odtworzenie: `python3 scripts/engine_gate_report.py` oraz
`pytest tests/test_engine_on_real_data.py`.
