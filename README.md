# Projekt G — Laboratorium strategii MNQ

Systematyczne poszukiwanie oryginalnej, statystycznie zweryfikowanej strategii na kontrakcie
Micro E-mini Nasdaq-100 (MNQ), przy użyciu świec, wskaźników pochodnych i danych o zdarzeniach
makroekonomicznych.

**Dokument założyciel­ski: [`docs/PLAN.pdf`](docs/PLAN.pdf)** (49 stron) — plan operacyjny,
specyfikacja techniczna silnika, metodologia badawcza i katalog hipotez. Wersja 1.1, po czterech
niezależnych audytach zewnętrznych.

---

## Stan projektu

| Etap | Status |
|------|--------|
| Dokument założycielski v1.1 | ✅ zrobione |
| Etap 0 — fundament repo | ✅ zrobione |
| Etap 2 — silnik i aparat walidacyjny | ✅ kompletny: 322 testy, pokrycie 92% |
| Pipeline danych, kalendarz CME, sanity-report, bramka silnika | ✅ kod gotowy, czeka na dane |
| Etap 1 — pobranie danych | ⛔ **zablokowane**: host `hist.databento.com` odrzucany przez politykę egress. Procedura wznowienia: **[HANDOFF.md](HANDOFF.md)** |
| Etap 3 — fabryka hipotez | oczekuje na dane |

---

## Szybki start

```bash
pip install -e '.[dev]'
PYTHONPATH=. pytest -q
```

### Klucz API Databento

Klucz czytany jest **wyłącznie ze zmiennej środowiskowej**. Nigdy nie trafia do repozytorium:

```bash
export DATABENTO_API_KEY="db-..."
python3 scripts/build_dataset.py --estimate-only   # najpierw szacunek kosztu
```

`.gitignore` blokuje `.env*`, `data/raw/` i pliki `.dbn`. Skrypt failuje z czytelnym błędem,
gdy zmiennej brak — nie ma wartości domyślnej.

---

## Struktura

```
engine/          rdzeń silnika backtestowego
  sessions.py    segmentacja doby w ET, DST, klasyfikacja luk
  calendar_cme.py kalendarz giełdy generowany z reguł — święta i dni skrócone
  costs.py       model kosztów i poślizgu (baza 2.20 USD RT, skalowanie zmiennością)
  backtest.py    główna pętla, tabela rozstrzygnięć wewnątrzbarowych, warstwa ryzyka
  clean.py       pipeline raw → clean (osiem kroków rozdz. 4.2)
  sanity.py      raport jakości danych (rozdz. 4.6)
  guards.py      blokada lookaheadu, zakaz volume==0, rozdzielenie serii
  roll.py        rolowanie wolumenowe, back-adjust różnicowy, px_raw/px_adj
  features.py    ATR, VWAP, percentyle, poziomy referencyjne (tylko px_raw)
  metrics.py     PF, Sharpe + poprawka Lo, Sortino, MDD, MAR, SQN, koncentracja
  loader.py      GRANICA — wymaga danych w data/clean/

validation/      aparat statystyczny
  engine_checks.py cztery testy silnika z rozdz. 5.6 — bramka przed eksploracją
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

scripts/
  build_dataset.py     pobranie danych (czeka na odblokowanie sieci)
  sanity_report.py     raport jakości → reports/data_quality.md
  engine_validation.py bramka silnika: cztery testy z rozdz. 5.6

tests/           pytest — w tym regresja na liczbach opublikowanych w PLAN.pdf
docs/            dokument założycielski (HTML + PDF)
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
