# Od surowej danej do P&L — jedna transakcja, cała droga

Krok 11 Etapu 2. Dokument istnieje po to, żeby właściciel projektu mógł
prześledzić **jedną konkretną transakcję** od bajtu u dostawcy do liczby w USD
i w każdym punkcie wiedzieć, co się z nią stało i dlaczego.

Nie jest to przykład dydaktyczny. Wszystkie liczby poniżej pochodzą
z rzeczywistego przebiegu na danych w repo i można je odtworzyć.

**Transakcja:** MNQ, short, 5 marca 2024, wejście 09:36 ET, wyjście 09:47 ET,
wynik **+77,80 USD netto**.

---

## Etap 0 — skąd bierze się bar

Databento, zbiór `GLBX.MDP3`, schemat `ohlcv-1m`, symbol `MNQH4`. Zamówione
przez `scripts/build_dataset.py` z obowiązkowym `--estimate-only` przed
zakupem (koszt całej historii MNQ: 14,15 USD).

Klucz API czytany **wyłącznie** z `os.environ["DATABENTO_API_KEY"]`, bez
wartości domyślnej — brak zmiennej kończy się czytelnym błędem, nie cichym
działaniem na połowie danych.

Zapis: `data/raw/` (poza gitem — odtwarzalne z manifestu, za duże dla repo).

## Etap 1 — surowy bar sygnału

Po deduplikacji i sortowaniu po `ts_event`:

```
ts_utc  2024-03-05 14:35:00+00:00
open    18075.00   high 18085.50   low 18056.50   close 18081.25
volume  13729      contract MNQH4
```

Kontrola jakości (`scripts/data_quality.py`): `low ≤ open,close ≤ high`,
monotoniczność czasu, `volume ≥ 0`. Bar przechodzi.

## Etap 2 — czas i sesja

`ts_utc` → ET przez `America/New_York`, **nigdy** przez stały offset (założenie
A2). 14:35 UTC = **09:35 ET**, czas zimowy.

`engine.sessions.trade_date` przypisuje bar do sesji rozpoczętej o 18:00 ET
4 marca → `trade_date = 2024-03-05`.
`engine.sessions.segment_of` → `rth_open` (09:30–10:00 ET).

Flagi z pipeline'u: `gap_kind=none`, `halt_window=False`, `short_day=False`,
`days_to_roll=6`, `dst_transition=False`, `data_condition=available`.

## Etap 3 — dwie serie cen, nie jedna

To jest miejsce, w którym najłatwiej o cichy błąd na kilkadziesiąt punktów.

| Kolumna | Wartość | Do czego |
|---|---|---|
| `close` (surowa) | **18081,25** | cena, która realnie widniała na tablicy MNQH4 |
| `px_raw` | 18081,25 | poziomy międzysesyjne (PDH/PDL, profil) |
| `px_adj` | **20561,25** | zwroty, statystyki, **P&L** |

Różnica **+2480,00** to skumulowany back-adjust różnicowy — suma luk
rolowaniowych od marca 2024 do dziś. Wewnątrz jednego kontraktu jest **stała**,
więc `to_bars(price="adj")` przesuwa cały bar (O/H/L/C) o tę samą liczbę
i zapisuje ją w barze jako `px_raw_offset = −2480,00`. Dzięki temu z serii
ciągłej da się odtworzyć cenę surową bez ponownego sięgania do pliku.

Bar podany silnikowi:

```
ts 2024-03-05 14:35:00+00:00
O 20555.00   H 20565.50   L 20536.50   C 20561.25   V 13729
segment rth_open   px_raw_offset −2480.00
```

Gdyby P&L liczyć na serii surowej, każde rolowanie wstawiałoby w wynik
sztuczny skok rzędu kilkudziesięciu punktów — „zysk" bez pokrycia. Gdyby
poziom „wczorajszy szczyt" liczyć na serii skorygowanej, rozjechałby się
w 4 dniach rolowania w roku. Stąd **dwie serie, każda do swojego zastosowania**
(założenie B1, pilnowane przez `engine.guards.assert_raw_series`).

## Etap 4 — sygnał

Strategia dostaje bar 09:35 ET i składa zlecenie:

```python
Order(side="short", kind="mkt", sl=20591.25, tp=20521.25)
```

SL 30 punktów nad ceną odniesienia, TP 40 punktów pod nią.

**Strategia nie widzi przyszłości fizycznie, nie umownie.** Otrzymuje
`HistoryView(bars, cutoff=i)` — obiekt, który przy próbie sięgnięcia po bar
*i+1* rzuca wyjątek. To nie jest konwencja do przestrzegania, tylko konstrukcja,
której nie da się obejść przez nieuwagę.

## Etap 5 — wypełnienie

Zlecenie złożone na barze 09:35 wykonuje się **najwcześniej na barze 09:36**
(założenie C1). Silnik nie zna trajektorii ceny wewnątrz bara 09:35 — wykonanie
w tym samym barze byłoby zgadywaniem kolejności, której dane M1 nie zawierają.

Bar wykonania:

```
09:36 ET   O 20561.25   H 20562.25   L 20540.25   C 20542.25   V 7190
```

- zlecenie rynkowe → cena bazowa = **OPEN bara 09:36 = 20561,25**
- `volume = 7190 > 0`, więc handel się odbywał; przy `volume == 0` silnik
  odmówiłby wykonania i podniósł licznik `skipped_zero_volume`
- poślizg dla segmentu `rth_open`: **0,50 pkt** (2 ticki)
- short **sprzedaje**, więc poślizg działa na niekorzyść: 20561,25 − 0,50

**Cena wejścia: 20560,75.**

## Etap 6 — życie pozycji

Od bara 09:37 silnik na każdym barze sprawdza tabelę rozstrzygnięć 5.4: czy bar
dotknął SL (20591,25), TP (20521,25), obu, czy żadnego.

Bary 09:37–09:46 nie dotykają żadnego poziomu. Na barze 09:47:

```
09:47 ET   O 20525.50   H 20526.50   L 20518.00   C 20519.75
```

`low = 20518,00 ≤ 20521,25` → **TP osiągnięty**. High tego bara nie sięga SL,
więc bar **nie jest sporny** — nie ma niejednoznaczności do rozstrzygania i tym
razem polityka SL_WINS nie ma nic do powiedzenia. Gdyby jeden bar dotknął obu
poziomów, silnik przyjąłby SL i podniósł `ambiguous_bars`; wynik przy przeciwnej
polityce jest wtedy raportowany jako obowiązkowe pasmo wrażliwości.

**Cena wyjścia: 20521,25** — poziom TP, bez poślizgu, bo zlecenie limitowe
wypełnia się po swojej cenie albo lepiej.

## Etap 7 — arytmetyka wyniku

```
punkty      = 20560,75 − 20521,25          = 39,50 pkt
brutto USD  = 39,50 × 2,00 USD/pkt          = 79,00 USD
prowizja    = 1,20 USD RT                            (round-turn, PLAN 3.2)
netto       = 79,00 − 1,20                  = 77,80 USD
ryzyko      = 20591,25 − 20560,75           = 30,50 pkt
R           = 39,50 / 30,50                 = 1,2951
```

Mnożnik MNQ to **2,00 USD za punkt** (0,50 USD za tick, 4 ticki na punkt).

Poślizg **nie jest opłatą** — siedzi w cenie wejścia jako część wykonania.
Prowizja jest opłatą i jest księgowana osobno. To rozróżnienie ma znaczenie
praktyczne: test symetrii z rozdz. 5.6 porównuje wyniki **brutto**, bo prowizja
jest identyczna dla long i short, a poślizg — nie.

Pełny koszt round-turn tej transakcji: 1,20 USD prowizji + 0,50 pkt poślizgu
wejścia (1,00 USD) = **2,20 USD**, czyli dokładnie baza kosztowa z założenia C3.

## Etap 8 — gdzie ta liczba trafia dalej

```
Trade → Result.trades
      → engine.metrics.summarize   (PF, Sharpe, Sortino, MDD, MAR, SQN)
      → validation/*               (DSR, PBO, CPCV, SPA, bootstrap)
      → reports/*.md               (raport hipotezy)
      → hypotheses/REGISTRY.md     (werdykt + licznik prób)
```

Pojedyncza transakcja nie jest wnioskiem o niczym. Podłoga to **400 transakcji**
(cel 800+), bo poniżej niej moc testu nie pozwala odróżnić przewagi od szumu
(założenie E1, `validation/power.py`).

---

## Co ta ścieżka pokazuje

Dziewięć etapów i w każdym istnieje sposób na cichy błąd o rząd wielkości
większy niż mierzona przewaga:

| Etap | Błąd, który nie rzuciłby wyjątku | Zabezpieczenie |
|---|---|---|
| 2 | stały offset zamiast strefy → RTH przesunięte o godzinę przez kilka tygodni w roku | `America/New_York`, baseline warstwa sesji |
| 3 | P&L na serii surowej → sztuczne skoki na rolowaniach | `to_bars(price="adj")`, `px_raw_offset` w barze |
| 4 | strategia zagląda o bar do przodu | `HistoryView` rzuca wyjątek |
| 5 | wykonanie po cenie z bara sygnału | kolejność zdarzeń wpisana w pętlę |
| 5 | wykonanie na barze bez obrotu | `bar.tradeable`, licznik `skipped_zero_volume` |
| 6 | bar sporny rozstrzygnięty po cichu na korzyść | licznik `ambiguous_bars` + obowiązkowe pasmo |
| 7 | poślizg policzony jako opłata → zły test symetrii | `pnl_usd_gross` osobno od `pnl_usd` |

Żaden z tych błędów nie zatrzymałby przebiegu. Każdy dałby ładniejszą krzywą
kapitału. Dlatego zabezpieczeniem jest konstrukcja, nie ostrożność.

**Odtworzenie:** dane `data/clean/mnq_1m_cont.parquet`, sesja 2024-03-05,
`Order(side="short", kind="mkt", sl=20591.25, tp=20521.25)` złożone na barze
14:35 UTC, domyślny `CostModel` i domyślny model poślizgu.
