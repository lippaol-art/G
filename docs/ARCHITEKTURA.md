# Mapa architektury i klasyfikacja krytyczności

**Dokument opisuje system taki, jaki jest — nie taki, jaki powinien być.**
Powstał 02.08.2026, przed jakimkolwiek refaktorem, i nie zmienia ani jednej
linii kodu.

Rozmiar systemu: **11 358 linii Pythona** w 62 plikach + 430 testów.

| Warstwa | Linie | Pliki | Rola |
|---|---|---|---|
| `engine/` | 3 147 | 14 | rdzeń: dane, sesje, wykonanie, koszty, metryki |
| `validation/` | 1 204 | 8 | aparat statystyczny, bez wiedzy o rynku |
| `scripts/` | 2 211 | 9 | pobieranie i budowa zbiorów, raporty jakości |
| `research/` | 4 683 | 13 | karty, pre-flighty, benchmarki — **zamrożone eksperymenty Gen1** |
| `tests/` | 4 324 | 18 | 430 testów |

---

## 1. Przepływ: od źródła do rejestru

```
ŹRÓDŁA ZEWNĘTRZNE
  Databento GLBX.MDP3 (MNQ, NQ, ES)   SEC EDGAR      BLS + Federal Reserve
  Databento XNAS/ARCX (K6: akcje)     8-K item 2.02  harmonogramy publikacji
        │                                   │                  │
        ▼                                   │                  │
  scripts/build_dataset.py                  │                  │
  scripts/build_k6.py                       │                  │
        │  data/raw/*.dbn  (poza repo)      │                  │
        ▼                                   │                  │
  scripts/make_clean.py ──► engine/dataset.py                  │
  scripts/make_k6_clean.py ─► engine/equities.py               │
        │        ├─ engine/roll.py      rolowanie + back-adjust │
        │        ├─ engine/sessions.py  segmenty, trade_date    │
        │        └─ engine/loader.py    walidacja schematu      │
        ▼                                   ▼                  ▼
  data/clean/*.parquet              scripts/build_earnings.py  scripts/build_macro.py
  px_raw · px_adj · segment         scripts/classify_earnings  engine/macro.py
  trade_date · flagi                engine/earnings.py
        │                           data/clean/earnings*.csv   data/clean/macro_events.csv
        │                                   │                  │
        └───────────────┬───────────────────┴──────────────────┘
                        ▼
                engine/features.py      ATR, VWAP, zakres ON, percentyle
                engine/ndx_sensitivity  wrażliwości indeksu (K6)
                        │
                        ▼
                KARTA HIPOTEZY          hypotheses/H0xx.md — specyfikacja zamrożona
                        │
                        ▼
                PRE-FLIGHT              research/W0xx_*.py — rozkłady, ZERO prób
                        │
                        ├──── NO-GO ──► REGISTRY.md, karta REJECTED
                        │
                        ▼ GO
                engine/backtest.py      pętla event-driven, kolejność zdarzeń
                        ├─ engine/costs.py     prowizja + poślizg per segment
                        └─ engine/guards.py    zakaz lookaheadu, HistoryView
                        │
                        ▼
                Result: trades, equity, rejected_orders, blocked_bars
                        │
                        ▼
                engine/metrics.py       PF, Sharpe (+Lo), Sortino, MDD, MAR, SQN
                        │
                        ▼
                validation/             dsr · cpcv · pbo · spa · walkforward · montecarlo
                        │
                        ▼
                reports/*.md + hypotheses/REGISTRY.md + validation/trial_counter.json
```

---

## 2. Moduły rdzenia — `engine/`

### `sessions.py` — 200 linii · **KRYTYCZNY**

| | |
|---|---|
| **Odpowiedzialność** | segmenty doby ET, `trade_date` od 18:00 ET, DST, dni skrócone, historyczny halt 15:15–15:30 CT (do 27.06.2021) |
| **Wejście** | `datetime` (UTC lub ET) |
| **Wyjście** | nazwa segmentu, `trade_date`, flagi |
| **Zależności** | brak (liść) |
| **Kluczowe założenia** | doba handlowa zaczyna się o 18:00 ET · segmenty rozłączne i pokrywające · konwersja przez `America/New_York`, nigdy przez stały offset |
| **Testy** | `test_sessions.py` (38) |
| **Raporty zależne** | **wszystkie** |

### `roll.py` — 246 linii · **KRYTYCZNY**

| | |
|---|---|
| **Odpowiedzialność** | rolowanie wolumenowe, back-adjust **różnicowy**, rozdzielenie `px_raw` / `px_adj` |
| **Wejście** | bary wielu kontraktów |
| **Wyjście** | daty rolowań, skumulowane przesunięcia |
| **Zależności** | brak (liść) |
| **Kluczowe założenia** | korekta jest **addytywna** dla futures (znaczenie ma różnica cen) · `px_raw` do poziomów międzysesyjnych, `px_adj` do P&L (PLAN 4.3) |
| **Testy** | `test_roll_metrics.py` (32) |
| **Raporty zależne** | wszystkie używające cen |

### `loader.py` — 158 linii · **KRYTYCZNY**

| | |
|---|---|
| **Odpowiedzialność** | wczytanie parquet, walidacja schematu, `to_bars` |
| **Kluczowe założenia** | kolumny `open/high/low/close` w pliku są **RAW**; przesunięcie = `px_adj − close`, stałe w obrębie kontraktu |
| **Testy** | `test_features_loader.py` (22), `test_dataset_pipeline.py` (21) |

### `dataset.py` — 334 linie · **KRYTYCZNY**

| | |
|---|---|
| **Odpowiedzialność** | pipeline raw→clean: dedup, walidacja OHLC, klasyfikacja luk `expected` vs `anomaly`, mapowanie kontraktów, segmenty, flagi |
| **Zależności** | `loader`, `roll`, `sessions` |
| **Kluczowe założenia** | brak bara ≠ luka w danych (OHLCV drukuje się tylko przy transakcji) · forward-fill dozwolony dla wskaźników, **zakazany dla barów wejścia/SL** |
| **Testy** | `test_dataset_pipeline.py` (21) |

### `backtest.py` — 529 linii · **KRYTYCZNY — największy pojedynczy moduł**

| | |
|---|---|
| **Odpowiedzialność** | pętla event-driven, kolejność zdarzeń w barze, zlecenia oczekujące, OCO, wygasanie zleceń dziennych, bramka ryzyka |
| **Zależności** | `costs`, `guards` |
| **Kluczowe założenia** | **koszty są domyślne** (`CostModel()` gdy nie podano) · sygnał na barze *i* wykonuje się najwcześniej na *i+1* · strategia widzi wyłącznie `HistoryView(bars, cutoff=i)` · wypełnienie limita wymaga penetracji ≥ 1 tick · stop przeskoczony luką wypełnia się na **otwarciu** |
| **Testy** | `test_runner_loop.py` (29), `test_backtest_resolution.py` (21), `test_engine_on_real_data.py` (16) |

### `costs.py` — 122 linie · **KRYTYCZNY**

| | |
|---|---|
| **Odpowiedzialność** | prowizja 1.20 USD RT, poślizg bazowy per segment × mnożnik zmienności, poślizg stop-gap skalowany luką |
| **Kluczowe założenia** | baza 1 tick/stronę = **2.20 USD RT**; konserwatyzm w stress-teście ×2, nie w bazie |
| **Testy** | `test_costs_power.py` (28) |

### `guards.py` — 135 linii · **KRYTYCZNY**

| | |
|---|---|
| **Odpowiedzialność** | `HistoryView` odcinający przyszłość, `assert_raw_series`, kontrola izolacji warstw |
| **Testy** | `test_guards.py` (29) — w tym strażnik pakowalności i zakaz `hash()` jako ziarna |

### `metrics.py` — 247 linii · **KRYTYCZNY**

| | |
|---|---|
| **Odpowiedzialność** | PF, Sharpe + poprawka Lo, Sortino, MDD, MAR, SQN, koncentracja, rozkłady |
| **Kluczowe założenia** | **metryki w R są niezdefiniowane bez stopa** → NaN + flaga `r_metrics_valid` (W003) · koncentracja NaN przy sumie ≤ 0 |
| **Testy** | `test_roll_metrics.py` (32) |

### `features.py` — 147 linii · **ZMIENIA SYGNAŁ**

ATR, VWAP sesyjny, σ_VWAP, zakres ON, percentyle kroczące, poziomy referencyjne
przez `assert_raw_series`. Testy: `test_features_loader.py` (22),
`test_w010_vwap.py` (5).

### `equities.py` — 362 linie · **ZMIENIA PRÓBKĘ**

Splity (korekta **multiplikatywna**, inaczej niż futures) i sklejanie tickerów
(FB→META). Dwa niezależne warunki detekcji: cena i wolumen. Testy:
`test_equities.py` (42), w tym 13 zmierzonych przypadków jako regresja.

### `earnings.py` — 242 linie · **ZMIENIA PRÓBKĘ**

Kalendarz 8-K item 2.02. Czas przyjęcia ze **strony indeksu złożenia**, nie z API
`submissions` — to pole bywa czasem ET z sufiksem `Z`. Testy: `test_earnings.py` (28).

### `macro.py` — 227 linii · **ZMIENIA PRÓBKĘ**

Kalendarz BLS + Fed. Godzina z dokumentu, klasyfikacja planowe/nieplanowe
z etykiet Fedu. Testy: `test_macro.py` (18).

### `ndx_sensitivity.py` — 198 linii · **ZMIENIA SYGNAŁ**

Wrażliwości indeksu z regresji kroczącej, bez lookaheadu. Testy:
`test_ndx_sensitivity.py` (15).

---

## 3. Warstwa walidacyjna — `validation/`

Nie zna rynku ani instrumentu. Operuje na szeregach liczb.

| Moduł | Linie | Rola | Testy |
|---|---|---|---|
| `dsr.py` | 243 | DSR + SR₀ wg FST, σ_SR z rozrzutu prób, N_eff przez ONC | `test_dsr.py` (33) |
| `cpcv.py` | 145 | Combinatorial Purged CV, C(6,2)=15 ścieżek | `test_validation_framework.py` (32) |
| `pbo.py` | 138 | PBO przez CSCV, bramka < 0.20 | jw. |
| `walkforward.py` | 162 | okna 12m/3m, purge + embargo | jw. |
| `spa.py` | 159 | SPA Hansena | `test_montecarlo_spa.py` (22) |
| `montecarlo.py` | 215 | permutacja, bootstrap BCa blokowy, syntetyki | jw. |
| `power.py` | 142 | liczność próby z członem mocy | `test_costs_power.py` (28) |

**Wszystkie KRYTYCZNE FINANSOWO w zakresie, w jakim służą certyfikacji.**

---

## 4. Dozwolony kierunek zależności

Zweryfikowany, nie deklarowany:

```
validation/   ──── nie importuje niczego wewnętrznego (liść)
engine/       ──── importuje wyłącznie engine.*
scripts/      ──── importuje engine.*
research/     ──── importuje engine.*, validation.*, research.*
tests/        ──── importuje wszystko
```

**Sprawdzone: rdzeń nie importuje ani `research`, ani `scripts`.**

### Jedyne odstępstwo warte odnotowania

`research/W011` i `research/W012` importują `zbuduj()` z `research/W009`. To
znaczy, że **W009 przestał być jednorazowym skryptem i stał się współdzieloną
infrastrukturą badawczą** — fakt istotny dla audytu kodu: nie wolno go traktować
jak zamrożony eksperyment, bo dwa raporty od niego zależą.

---

## 5. Klasyfikacja krytyczności

### 🔴 KRYTYCZNE FINANSOWO — błąd tworzy fałszywy P&L

| Moduł | Dlaczego |
|---|---|
| `engine/sessions.py` | zła sesja = zły segment = zły koszt i zła klasyfikacja zdarzenia |
| `engine/roll.py` | zły back-adjust = fałszywy P&L na granicy kontraktów |
| `engine/loader.py` | zły schemat lub złe przesunięcie = wszystko dalej fałszywe |
| `engine/dataset.py` | zła klasyfikacja luk = wykonanie na barze, którego nie było |
| `engine/backtest.py` | kolejność zdarzeń, lookahead, wypełnienia |
| `engine/costs.py` | zaniżony koszt zamienia stratę w zysk |
| `engine/guards.py` | ostatnia linia obrony przed lookaheadem |
| `engine/metrics.py` | metryki wchodzące do certyfikacji |
| `validation/*` | bramki DSR/PBO/SPA decydujące o statusie karty |

**Zmiana wymaga:** golden output przed i po · test regresyjny · jawne
porównanie zachowania · brak zmiany wyników poza wcześniej zadeklarowaną poprawką.

### 🟠 ZMIENIAJĄCE PRÓBKĘ LUB SYGNAŁ

`engine/features.py` · `engine/equities.py` · `engine/earnings.py` ·
`engine/macro.py` · `engine/ndx_sensitivity.py` · `scripts/classify_earnings.py` ·
`scripts/build_earnings.py` · `scripts/build_macro.py` · `scripts/build_k6.py` ·
`scripts/make_clean.py` · `scripts/make_k6_clean.py` · `research/W0*.py`

**Zmiana wymaga:** golden output wyników zależnych raportów · jawne wskazanie,
które karty trzeba przeliczyć.

### 🟢 RAPORTUJĄCE

`scripts/data_quality.py` (część opisowa) · `scripts/engine_gate_report.py`
(formatowanie) · generatory Markdown wewnątrz `research/W0*.py` · tabele.

**Zmiana wymaga:** tylko zielonego CI.

---

## 6. Najważniejsze założenia całego systemu

Wyliczone tu, rozwinięte w `docs/ZALOZENIA.md`.

1. Doba handlowa zaczyna się o **18:00 ET**; `trade_date` od tego momentu.
2. `px_raw` do poziomów międzysesyjnych, `px_adj` do zwrotów i P&L.
3. Back-adjust futures jest **różnicowy**, korekta splitów akcji
   **multiplikatywna**.
4. Sygnał z bara *i* wykonuje się najwcześniej na barze *i+1*.
5. Przy dotknięciu SL i TP w jednym barze domyślnie **wygrywa SL**; pasmo
   wrażliwości jest metryką obowiązkową.
6. Koszt bazowy **2.20 USD RT**; stress ×2 jest warunkiem bramki, nie bazą.
7. Brak bara oznacza brak transakcji, nie lukę w danych.
8. Zdarzenia pochodzą z **rejestrów**, nigdy z reakcji ceny.
9. Pre-flight nie zużywa próby; każdy backtest zużywa.
10. Strefa czasowa zawsze przez `America/New_York`, nigdy przez stały offset.

---

## 7. Co ta mapa ujawniła

Trzy rzeczy warte odnotowania, **bez wprowadzania zmian**:

1. **`research/W009` jest de facto biblioteką**, nie skryptem — W011 i W012
   importują z niego `zbuduj()`. Przy audycie kodu należy go przenieść do
   współdzielonej infrastruktury badawczej albo świadomie zostawić z adnotacją.
2. **`engine/backtest.py` ma 529 linii i jest największym modułem krytycznym.**
   To naturalny kandydat do rozbicia, ale też miejsce, gdzie refaktor jest
   najbardziej niebezpieczny — pokryty 66 testami z trzech plików.
3. **`scripts/` miesza dwie role**: pobieranie danych (`build_*`) i raportowanie
   jakości (`data_quality`, `engine_gate_report`). Podział byłby czytelniejszy,
   ale nie jest pilny.

Żadna z tych obserwacji nie jest teraz realizowana. Wchodzą do raportu
proponowanego refaktoru, który wymaga osobnej decyzji.

---

## 8. Punkt odniesienia

Stan opisany w tej mapie jest zamrożony w golden baseline w commicie
**`a1aba1c0c47fce2e958374e2614e5744b6882027`** (tag `gen1-baseline`).
Każda późniejsza zmiana zachowania systemu ma wpis w `golden/ZMIANY.md`
z poprzednim i nowym hashem oraz listą zmienionych kluczy.
