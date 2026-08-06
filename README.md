# Projekt G — Laboratorium strategii MNQ

Systematyczne poszukiwanie oryginalnej, statystycznie zweryfikowanej strategii na kontrakcie
Micro E-mini Nasdaq-100 (MNQ), przy użyciu świec, wskaźników pochodnych i danych o zdarzeniach
makroekonomicznych.

**Dokument założyciel­ski: [`docs/PLAN.pdf`](docs/PLAN.pdf)** (49 stron) — plan operacyjny,
specyfikacja techniczna silnika, metodologia badawcza i katalog hipotez. Wersja 1.1, po czterech
niezależnych audytach zewnętrznych.

**Stan bieżący projektu: [`HANDOFF.md`](HANDOFF.md). `PLAN.*` to historyczny dokument wizji** —
nadal wiążący tam, gdzie definiuje metodę i progi, ale nieaktualizowany o postęp prac.

---

## Stan projektu

| Etap | Status |
|------|--------|
| Dokument założycielski v1.1 | ✅ zrobione |
| Etap 0 — fundament repo | ✅ zrobione |
| Etap 1 — dane rynkowe | ✅ MNQ/NQ/ES, bary M1 2019–2026, w `data/clean/` |
| Etap 2 — silnik i aparat walidacyjny | ✅ kompletny: **526 funkcji testowych, pokrycie 92%**, bramka 5.6 zaliczona (dokładną liczbę pilnuje strażnik — patrz HANDOFF) |
| Gen1 — 16 hipotez na barach M1 | ✅ zamknięta: **wszystkie odrzucone w pre-flightach**. Wniosek: M1 przewiduje amplitudę, nie kierunek ([SYNTEZA_GEN1.md](docs/SYNTEZA_GEN1.md)) |
| D5 — przepływ agresywny na danych MBO | 🔄 **w toku**: jednostka rozstrzygnięta (D5-C GO), dry run 8/8. Następny krok i bramka GO/NO-GO: **[HANDOFF.md](HANDOFF.md)** §4 |

**Licznik prób: 0.** Ani jedna karta nie doszła do backtestu — każda upadła na tańszej
bramce wstępnej. To jest wynik poprawny, a nie zaległość.

---

## Szybki start

```bash
pip install -e '.[dev]'
bash scripts/check_all.sh --szybko   # linter, typy, testy, strażnicy
```

`scripts/check_all.sh` jest **kanoniczną bramką** i odpowiada CI krok w krok. Pełny przebieg
(bez `--szybko`) dokłada bramkę silnika na realnych danych i golden baseline — tych dwóch
CI nie uruchamia, bo nie ma tam danych rynkowych.

### Klucz API Databento

Klucz czytany jest **wyłącznie ze zmiennej środowiskowej**. Nigdy nie trafia do repozytorium:

```bash
export DATABENTO_API_KEY="db-..."
python3 scripts/fetch_d5b2_month.py --wycena   # ZAWSZE najpierw wycena, nigdy zakup w ciemno
```

`.gitignore` blokuje `.env*`, `data/raw/` i pliki `.dbn`. Skrypt failuje z czytelnym błędem,
gdy zmiennej brak — nie ma wartości domyślnej. Metadane są darmowe, więc wycena nic nie
kosztuje; pobranie obciąża konto i **nie jest nigdy ponawiane automatycznie**.

Surowe pliki `.dbn.zst` żyją poza repozytorium — ścieżkę wskazuje `PROJECT_G_DATA_ROOT`
(patrz [`docs/URUCHOMIENIE_LOKALNE.md`](docs/URUCHOMIENIE_LOKALNE.md)).

---

## Struktura

```
engine/          rdzeń silnika backtestowego
  sessions.py    segmentacja doby w ET, DST, kalendarz CME, klasyfikacja luk
  costs.py       model kosztów i poślizgu (baza 2.20 USD RT, skalowanie zmiennością)
  backtest.py    tabela rozstrzygnięć wewnątrzbarowych, warstwa ryzyka
  guards.py      blokada lookaheadu, zakaz volume==0, rozdzielenie serii
  roll.py        rolowanie wolumenowe, back-adjust różnicowy, px_raw/px_adj
  features.py    ATR, VWAP, percentyle, poziomy referencyjne (tylko px_raw)
  metrics.py     PF, Sharpe + poprawka Lo, Sortino, MDD, MAR, SQN, koncentracja
  dataset.py     pipeline raw -> clean
  loader.py      GRANICA — wymaga danych w data/clean/
  cme_calendar.py    kalendarz CME z opublikowanych reguł, zweryfikowany na danych
  databento_io.py    granica metadane/pobieranie; brak ponawiania pobrań jest celowy
  mbo_events.py      kanoniczna jednostka D5-B2 (akcja agresywna per Trade)
  paths.py           PROJECT_G_DATA_ROOT; clean_dir() zawsze w repo
  macro.py, earnings.py, equities.py, ndx_sensitivity.py   zdarzenia i warstwa K6

validation/      aparat statystyczny
  dsr.py         Deflated Sharpe Ratio, SR₀ wg FST, N_eff przez klastrowanie ONC
  power.py       moc testu i planowanie wielkości próby
  walkforward.py okna 12m/3m, purge + embargo, lockbox
  cpcv.py        Combinatorial Purged CV — 15 ścieżek zamiast jednej
  pbo.py         Probability of Backtest Overfitting (bramka < 0.20)
  spa.py         test SPA Hansena
  montecarlo.py  permutacja, bootstrap blokowy BCa, syntetyki
  trial_counter.json   globalny licznik prób — wejście do DSR

hypotheses/
  REGISTRY.md    katalog hipotez: benchmarki, przeformułowane, kandydaci
  H0xx.md        karty pojedynczych hipotez wraz z werdyktami

research/        skrypty badawcze W0xx — zamrożone po wydaniu werdyktu
reports/         wyniki badań i audytów, cytowane z rejestru

scripts/
  check_all.sh           kanoniczna bramka lokalna = CI + golden baseline
  fetch_d5b2_month.py    zakup 21 sesji MBO — bieżący krok
  golden_baseline.py     zamrożenie wyników liczbowych projektu

golden/          baseline v14 + ZMIANY.md z uzasadnieniem każdej zmiany
data/KOSZTY.md   każdy wydany dolar, łącznie z ponownymi naliczeniami
tests/           pytest — w tym regresja na liczbach opublikowanych w PLAN.pdf
docs/            dokument założycielski (HTML + PDF) i specyfikacje etapów
```

---

## Zasady, które są wbudowane w kod, nie w dyscyplinę

**Zero lookahead.** Strategia widzi wyłącznie dane do bieżącego bara. Sygnał na close →
wykonanie na open następnego bara.

**Konserwatyzm przy niejednoznaczności.** Gdzie bar M1 nie rozstrzyga kolejności zdarzeń,
silnik wybiera wariant gorszy dla strategii. Backtest ma prawo zaniżać wynik; nie ma prawa
go zawyżać.

**Zakaz wykonania przy zerowym wolumenie.** Brak transakcji w minucie znaczy, że nie było
gdzie się wykonać. Databento nie drukuje takiego bara — i to jest poprawny opis rynku,
nie luka w danych.

**Globalny licznik prób.** Każdy backtest podnosi poprzeczkę dla ostatecznego zwycięzcy.
Limit: ≤ 10 wariantów na hipotezę. Przy 30 wariantach certyfikacji nie przechodzi nawet
strategia o Sharpe 1.5.

**System dwustopniowy.** `PROMISING` (przewaga ekonomiczna) i `CERTIFIED` (DSR ≥ 0.95).
Tylko drugi poziom uprawnia do rozmowy o realnym kapitale. Droga między nimi prowadzi przez
forward paper trading, bo tylko on dokłada dane bez zużywania prób.

---

## Testy jako kontrakt z dokumentem

Moduły `dsr.py`, `power.py` i `costs.py` mają **testy regresyjne na liczbach opublikowanych
w PLAN.pdf**. Jeśli implementacja rozjedzie się z dokumentem, test jest czerwony — albo
dokument kłamie, albo kod ma błąd, a oba przypadki wymagają reakcji.

Przykłady weryfikowanych tabel: DSR(SR, N_eff) przy T=1500 dni; liczba dni OOS do certyfikacji;
liczność próby dla mocy 50/80/90%; roczne koszty przy różnej częstotliwości handlu.

---

## Zastrzeżenie

Projekt badawczo-inżynieryjny. Nie stanowi doradztwa inwestycyjnego. Handel kontraktami futures
wiąże się z istotnym ryzykiem straty, mogącej przekroczyć zainwestowany kapitał. Żaden wynik
backtestu ani symulacji nie gwarantuje wyników rzeczywistych. Decyzja o realnym kapitale należy
wyłącznie do właściciela projektu.
