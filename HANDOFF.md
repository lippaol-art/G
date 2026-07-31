# HANDOFF — wznowienie pracy nad Projektem G

**Ten dokument jest napisany dla sesji, która nie widziała poprzedniej rozmowy.**
Kontener jest efemeryczny, więc wszystko potrzebne do kontynuacji jest tutaj i w repo.

Data: 31.07.2026 · Branch: `claude/financial-strategy-handoff-53s418`

---

## 1. Stan projektu w dziesięciu liniach

Budujemy laboratorium badawcze do znalezienia oryginalnej strategii na MNQ (Micro E-mini
Nasdaq-100). Dokument założycielski `docs/PLAN.pdf` (49 stron, wersja 1.1 po czterech
niezależnych audytach zewnętrznych) jest **jedynym źródłem prawdy** — kod ma go realizować,
a nie odwrotnie.

Gotowe: fundament repo, **kompletny silnik backtestowy z główną pętlą**, aparat walidacyjny,
**pipeline raw → clean**, **kalendarz CME**, **sanity-report**, **aparat walidacji samego
silnika**, strażnicy niezmienników, CI. **322 testy zielone, pokrycie 92%, ruff czysty.**

Niegotowe: **pobranie danych rynkowych (Etap 1)**. Bez nich nie da się uruchomić ani jednego
badania. **Blokada sieciowa została zdjęta 31.07.2026** — API Databento jest osiągalne,
brakuje wyłącznie klucza w zmiennych środowiska (sekcja 2).

Po stronie kodu **nie zostało już nic, co dałoby się zrobić bez danych** — cała reszta
listy z sekcji 6 czeka na Etap 1.

| Commit | Zawartość |
|--------|-----------|
| `78b864d` | Dokument v1.1 po audytach (49 stron) |
| `8626064` | Etap 0 + rdzeń silnika (sessions, costs, backtest) + DSR, power |
| `2a743a2` | Strażnicy niezmienników + CI |
| `05dd571` | Framework walidacji + roll, features, metrics, loader |
| `a82b0c4` | Główna pętla backtestu (rozdz. 5.3) + naprawa instalacji pakietu |
| `f99a421` | Pipeline raw → clean (rozdz. 4.2) + kalendarz CME |
| `305ed8a` | Sanity-report jakości danych (rozdz. 4.6) |
| `d04d374` | Walidacja silnika (rozdz. 5.6) + flat-by jako predykat |

---

## 2. Sieć: ODBLOKOWANA (31.07.2026) — zostaje klucz API

**Bloker, który zatrzymywał projekt przez dwie sesje, został zdjęty.** Właściciel przestawił
sieć środowiska chmurowego na **Full**. Zmiana zadziałała **natychmiast, w trwającej sesji** —
wbrew wcześniejszej hipotezie, że polityka jest wiązana wyłącznie przy starcie.

### Stan potwierdzony pomiarem

```
$ curl -o /dev/null -w "%{http_code}\n" https://hist.databento.com/v0/metadata.list_datasets
401          # API odpowiada; 401 = brak klucza, nie brak sieci
$ pip install -e '.[data]'   →  databento 0.82.0, klient tworzy się poprawnie
```

Wcześniejszy objaw (`curl: (56) CONNECT tunnel failed, response 403`) już nie występuje;
`$HTTPS_PROXY/__agentproxy/status` nie notuje nowych odmów.

**Uwaga na pierwszy request:** zaraz po zmianie polityki pierwsze połączenie z
`hist.databento.com` wygasło po 20 s, a dopiero kolejne zwróciło 401. Timeout na zimnym
połączeniu **nie jest** blokadą polityki — odmowa polityki ma zawsze postać `403` przy
CONNECT i ląduje w `recentRelayFailures`. Nie wyciągaj z jednego timeoutu wniosku, że sieć
nadal jest zamknięta.

### Weryfikacja jedną komendą

```bash
curl -sS --max-time 60 -o /dev/null -w "%{http_code}\n" \
  -u "$DATABENTO_API_KEY:" https://hist.databento.com/v0/metadata.list_datasets
```

| Wynik | Znaczenie |
|-------|-----------|
| `200` | klucz działa — **ruszaj z Etapem 1** (sekcja 4) |
| `401` | sieć OK, brak albo zły klucz — patrz sekcja 3 |
| `000` + błąd 56 | wróciła blokada polityki egress |
| `000` + błąd 28 | timeout; **powtórz raz**, zanim uznasz to za blokadę |

### Co zostało do zrobienia po stronie środowiska

`DATABENTO_API_KEY` **nie było ustawione w żadnej dotychczasowej sesji**. To jedyna rzecz,
która dzieli projekt od Etapu 1. Trzeba je wpisać w **Environment variables** środowiska
(format `.env`, jedna para `KLUCZ=wartość` na linię) na `claude.ai/code` — ikona chmurki
w rzędzie nad polem wiadomości, koło zębate przy środowisku.

**Zmienne środowiskowe są kopiowane raz, przy starcie sesji** — inaczej niż polityka
sieciowa. Klucz dodany do konfiguracji pojawi się więc dopiero w **następnej** sesji, nie
w trwającej.

### Ograniczenie, o którym trzeba wiedzieć

Środowiska chmurowe **nie mają osobnego magazynu sekretów**: wartość zmiennej jest czytelna
dla każdego, kto używa tego środowiska. Stąd zalecenie: klucz o możliwie wąskich
uprawnieniach, rotowany po zakończeniu pobierania danych. Alternatywa całkowicie omijająca
problem: właściciel pobiera dane lokalnie u siebie (`scripts/build_dataset.py`) i wgrywa
gotowe parquet do `data/clean/` — reszta pipeline'u działa bez zmian i bez klucza w chmurze.

### Czego NIE robić, jeśli blokada wróci

- **Nie ponawiać** odmów polityki w pętli. Dokumentacja proxy (`/root/.ccr/README.md`) mówi
  wprost: odmowy 403/407 należy zgłaszać, nie obchodzić.
- **Nie szukać obejść** (inny host, tunel, wyłączenie weryfikacji TLS). To naruszenie
  polityki organizacji, a nie problem techniczny do rozwiązania.

---

## 3. Klucz API — obowiązkowa rotacja

Poprzedni klucz został wklejony do czatu, więc **znajduje się w transkrypcie rozmowy**.
Traktuj go jako spalony.

1. Wygeneruj **nowy** klucz w panelu Databento, stary unieważnij.
2. Przekaż go jako **sekret środowiska**, nie przez czat — przetrwa restart kontenera,
   co przy projekcie wieloletnim ma realne znaczenie.
3. Kod czyta wyłącznie `os.environ["DATABENTO_API_KEY"]`. Nigdzie nie ma wartości domyślnej
   i nie wolno jej dodawać.
4. `.gitignore` blokuje `.env*`, `data/raw/`, `*.dbn`. Strażnik
   `tests/test_guards.py::TestSecrets` skanuje repo pod kątem wzorców kluczy, a CI robi to
   samo na **całej historii gita**.

---

## 4. Etap 1 krok po kroku

```bash
# 0. Sprawdź, czy sieć odblokowana (patrz sekcja 2)

# 1. Klucz w środowisku
export DATABENTO_API_KEY="db-..."

# 2. Zależności
pip install -e '.[dev,data]'

# 3. NAJPIERW szacunek kosztu — nigdy nie pobieraj w ciemno
python3 scripts/build_dataset.py --estimate-only
```

Oczekiwany koszt: **25–60 USD** za MNQ + NQ, OHLCV-1m, od 2019-04-14 (start produktu MNQ)
do dziś. Nowe konto Databento ma **125 USD kredytów startowych**, więc praktyczny koszt
tej fazy wynosi zero. Jeśli szacunek wychodzi radykalnie wyżej — zatrzymaj się i zapytaj
właściciela, coś jest nie tak z parametrami zapytania.

```bash
# 4. Pobranie
python3 scripts/build_dataset.py

# 5. Czyszczenie i budowa kontraktu ciągłego — kod GOTOWY, brakuje spięcia
#    z formatem plików dostawcy (patrz niżej)
python3 - <<'PY'
import polars as pl
from engine.calendar_cme import PROJECT_CALENDAR
from engine.clean import build_continuous, manifest_entry

raw = pl.read_parquet("data/raw/mnq_ohlcv-1m.parquet")   # patrz uwaga o .dbn
df, report = build_continuous(raw, PROJECT_CALENDAR)
df.write_parquet("data/clean/mnq_1m_cont.parquet")
print(report.n_clean, "barów,", len(report.rolls), "rolowań,",
      report.anomaly_gaps, "luk-anomalii")
PY

# 6. Sanity-report — kod GOTOWY
python3 scripts/sanity_report.py --symbol mnq --schema-version "..." --downloaded 2026-08-01

# 7. Walidacja silnika — BRAMKA, patrz sekcja 5
python3 scripts/engine_validation.py --symbol mnq

# 8. Commit oczyszczonych danych
git add data/clean/*.parquet data/manifest.md reports/data_quality.md
git commit -m "data: MNQ+NQ OHLCV-1m 2019-2026, kontrakt ciągły"
```

**Jedyne, co w kroku 5 wymaga dopisania:** `scripts/build_dataset.py` zapisuje pliki `.dbn.zst`
dostawcy, a `build_continuous` przyjmuje ramkę polars z kolumnami
`ts_event, symbol, open, high, low, close, volume`. Konwersja to jedno wywołanie
`db.DBNStore.from_file(...).to_df()` plus przemianowanie kolumn i **przeskalowanie cen**
(Databento podaje je jako liczby całkowite ×1e-9). Świadomie tego nie zgadywaliśmy w ciemno:
dokładne nazwy kolumn i skala zależą od wersji schematu, a zgadnięta konwersja cen jest
błędem, który nie rzuca wyjątkiem — po prostu przesuwa wszystkie wyniki o rząd wielkości.
Sprawdź na pierwszym pobranym pliku i dopisz w tym miejscu.

**Do `data/manifest.md` wpisz obowiązkowo:** zakres dat, wersję schematu dostawcy, datę
pobrania i sumy kontrolne. Databento zmienił normalizację `GLBX.MDP3` w lipcu 2026 —
bez przypiętej wersji nie odtworzysz później, na czym liczone były wyniki.

---

## 5. Po pobraniu danych: udowodnij, że silnik działa

**Zanim uruchomisz jakiekolwiek badanie**, silnik musi przejść testy z `docs/PLAN.pdf`
rozdz. 5.6. Niesprawdzony silnik produkuje śmieci z dokładnością do sześciu miejsc
po przecinku.

Komplet jest zaimplementowany w `validation/engine_checks.py`. Jedna komenda:

```bash
python3 scripts/engine_validation.py --symbol mnq     # kod 0 = bramka otwarta
```

| Test | Oczekiwany wynik | Co oznacza porażka |
|------|------------------|--------------------|
| **Zerowa przewaga** — losowe wejścia, symetryczny SL/TP | wynik ≈ −(koszty × liczba transakcji) | przeciek informacji w silniku |
| **Znany efekt** — kup na close RTH / sprzedaj na open | zgodność z bezpośrednim rachunkiem na barach co do znaku i rzędu wielkości | silnik źle mierzy — to linijka, nie strategia |
| **Symetria** — long na serii vs short na jej odbiciu | wynik lustrzany co do punktu | błąd w obsłudze jednej ze stron |
| **Determinizm** — dwa przebiegi z tym samym ziarnem | wyniki bitowo identyczne | nieziarnowana losowość gdzieś w ścieżce |

**Kryterium zerowej przewagi jest jednostronne** i tak ma zostać. Wynik brutto liczymy przed
prowizją, ale po poślizgu, a silnik jest po tej stronie konserwatywny z założenia (stop na
dotknięcie, limit dopiero po przebiciu o tick) — zdrowy silnik daje na rzucie monetą wynik
ujemny, i to tym pewniej, im większa próba. Test dwustronny odrzucałby poprawny silnik tym
częściej, im więcej mamy danych. Czerwone światło zapala wyłącznie rzut monetą, który
**zarabia**.

Testy `@pytest.mark.needs_data` (w `tests/test_features_loader.py`, `tests/test_sanity_report.py`
i `tests/test_engine_checks.py`) odblokują się automatycznie, gdy pojawi się
`data/clean/mnq_1m_cont.parquet`.

---

## 6. Czego jeszcze nie ma w kodzie

Wszystko poniżej wymaga danych albo zewnętrznego źródła — **nie ma już zadania, które dałoby
się wykonać bez Etapu 1.**

| Element | Uwagi |
|---------|-------|
| Konwersja `.dbn` → ramka polars | Jedyna brakująca linijka pipeline'u; wymaga obejrzenia realnego pliku dostawcy (patrz uwaga w sekcji 4). |
| Kalendarz zdarzeń makro | PLAN rozdz. 4.5. Scraping do `data/clean/events.csv`. Sanity-report ma już gotową kontrolę pokrycia (CPI/NFP co miesiąc, 8 posiedzeń FOMC rocznie) i będzie ją zgłaszał jako pozycję do przeglądu, dopóki pliku nie ma. |
| Weryfikacja kalendarza CME | `engine/calendar_cme.py` **generuje** kalendarz z reguł i ma flagę `verified=False`. Reguły nie przewidzą sesji odwołanej doraźnie (żałoba narodowa, awaria giełdy). Porównaj z kalendarzem opublikowanym przez CME, uzupełnij `DORAZNE_ZAMKNIECIA` i ustaw `verified=True`. |
| Weryfikacja krzyżowa danych | PLAN rozdz. 4.6 — pełny miesiąc plus 10 sesji ze źródła niezależnego. Sanity-report wypisuje gotową listę sesji i ekstrema do porównania; sam krok wymaga drugiego źródła. |
| Warstwa danych K6 | PLAN rozdz. 4.7 — ES, wagi NDX, ceny after-hours megacapów. Potrzebna dopiero do partii 2. |

### Co przybyło w tej sesji

| Moduł | Zawartość |
|-------|-----------|
| `engine/backtest.py::run` | Główna pętla (rozdz. 5.3): wykonanie na open następnego bara, limity ryzyka przed strategią, blackout wokół zdarzeń rangi 1, flat-by, mark-to-market. |
| `engine/clean.py` | Osiem kroków pipeline'u raw → clean (rozdz. 4.2). |
| `engine/calendar_cme.py` | Kalendarz CME generowany z reguł. **Uwaga: CME to nie NYSE** — w większość świąt federalnych kontrakty indeksowe handlują się do 12:00 CT, więc są to dni skrócone, nie dni bez sesji. Pełne zamknięcia: Wielki Piątek, Boże Narodzenie, Nowy Rok. |
| `engine/sanity.py`, `scripts/sanity_report.py` | Raport jakości danych (rozdz. 4.6) → `reports/data_quality.md`. |
| `validation/engine_checks.py`, `scripts/engine_validation.py` | Cztery testy silnika z rozdz. 5.6. |

---

## 7. Pierwsze zadanie badawcze po danych

**Test zaniku dryfu nocnego.** Rozstrzyga los karty H004 i jest tani — kilkadziesiąt minut.

Zewnętrzne badania (cytowane w audycie oryginalności) wskazują, że dryf overnight na
indeksach US wygasł po 2020 roku: ~3.7% rocznie w latach 1998–2020 wobec wartości bliskiej
zeru w 2021–2025. **Nie przyjmujemy tego na wiarę ani nie odrzucamy** — sprawdzamy na
własnych danych:

1. Dekompozycja zwrotów close→open rok po roku, 2019–2026, z przedziałami ufności.
2. Porównanie z zwrotami wewnątrzsesyjnymi (open→close).
3. Wynik → `hypotheses/REGISTRY.md`, sekcja wniosków przekrojowych.

- **Dryf obecny w ostatnich latach** → H004 wchodzi do badań z pytaniem o warunkowość reżimową.
- **Dryf wygasł** → H004 schodzi do benchmarków, a my mamy własny, policzony dowód zaniku
  znanego efektu i nie budujemy na nim niczego.

Potem: **partia 0** (uruchomienie benchmarków B01–B04 z parametrami z literatury — nie zużywają
licznika prób), następnie **partia 1** (H011, H005, H010).

---

## 8. Zasady, których nie wolno naruszyć

1. **Limit 10 wariantów na hipotezę.** Nie jest to preferencja stylistyczna, tylko wynik
   tabeli wykonalności DSR: przy 30 wariantach certyfikacji nie przechodzi nawet strategia
   o Sharpe 1.5. Licznik w `validation/trial_counter.json` jest wspólny dla całego projektu.
2. **Test oryginalności przed testem statystycznym.** Każda karta musi mieć nazwany publiczny
   benchmark i nazwaną **różnicę mechanizmu** (nie parametrów) — inaczej schodzi do benchmarków
   zanim spali choć jedną próbę. PLAN rozdz. 8.4.
3. **Zero syntetycznych danych w badaniach.** Ręcznie budowane bary w testach jednostkowych to
   fixture'y i są w porządku; żaden wniosek o rynku nie może pochodzić z danych innych niż realne.
4. **Nie uruchamiaj eksploracji, zanim testy silnika z sekcji 5 nie są zielone.**
5. **Wyniki „zbyt piękne" traktuj jako objaw błędu.** Profit factor powyżej 2 przy strategii
   intraday — protokół nakazuje najpierw szukać buga, dopiero potem się cieszyć.
   `engine/metrics.py` ma flagę `Metrics.suspicious`.

---

## 9. Mapa repozytorium

```
docs/PLAN.pdf            ŹRÓDŁO PRAWDY — 49 stron, czytaj przed zmianami w kodzie
hypotheses/REGISTRY.md   katalog hipotez, pamięć instytucjonalna, stan każdej karty
HANDOFF.md               ten dokument

engine/
  sessions.py      segmentacja doby w ET, DST, klasyfikacja luk (is_closed, uncovered_minutes)
  calendar_cme.py  kalendarz giełdy generowany z reguł — święta i dni skrócone
  costs.py         koszty i poślizg (baza 2.20 USD RT, skalowanie zmiennością)
  backtest.py      GŁÓWNA PĘTLA (run) + rozstrzyganie wewnątrzbarowe (5.4) + warstwa ryzyka
  clean.py         pipeline raw → clean, osiem kroków z rozdz. 4.2
  sanity.py        raport jakości danych (rozdz. 4.6)
  guards.py        HistoryView (blokada lookaheadu), zakaz volume==0, rozdzielenie serii
  roll.py          rolowanie wolumenowe, back-adjust różnicowy, px_raw/px_adj
  features.py      ATR, VWAP, percentyle, poziomy referencyjne (tylko na px_raw)
  metrics.py       PF, Sharpe + poprawka Lo, Sortino, MDD, MAR, SQN, koncentracja
  loader.py        GRANICA — wymaga danych w data/clean/

validation/
  engine_checks.py cztery testy silnika z rozdz. 5.6 — BRAMKA przed eksploracją
  dsr.py         Deflated Sharpe Ratio, SR₀ wg FST, N_eff przez ONC
  power.py       moc testu, liczność próby
  walkforward.py okna 12m/3m, purge + embargo, lockbox
  cpcv.py        Combinatorial Purged CV — 15 ścieżek zamiast jednej
  pbo.py         Probability of Backtest Overfitting (bramka < 0.20)
  spa.py         test SPA Hansena
  montecarlo.py  permutacja, bootstrap blokowy BCa, syntetyki
  trial_counter.json   globalny licznik prób

scripts/
  build_dataset.py      pobranie danych (sieć OK, czeka na klucz API)
  sanity_report.py      raport jakości → reports/data_quality.md
  engine_validation.py  bramka silnika (rozdz. 5.6)

tests/                  322 testy, w tym regresja na liczbach z PLAN.pdf
```

---

## 10. Jak zacząć następną sesję

```bash
git pull
cat HANDOFF.md                      # ten plik
cat hypotheses/REGISTRY.md          # co żyje, co umarło, jakie wnioski
cat validation/trial_counter.json   # budżet prób

pip install -e '.[dev]'
PYTHONPATH=. pytest -q              # czy wszystko nadal zielone

# sprawdź bloker sieciowy (sekcja 2) i jeśli 200 — ruszaj z sekcją 4
```

**Jeśli komenda z sekcji 2 zwraca `200`** — masz klucz i sieć, więc pierwsze zadanie tej sesji
jest jednoznaczne: Etap 1 (sekcja 4), potem bramka silnika (sekcja 5), potem pierwsze zadanie
badawcze (sekcja 7).

**Jeśli zwraca `401`** — sieć działa, brakuje klucza. Nie ma sensu szukać zadania w kodzie:
lista z sekcji 6 jest w całości zależna od danych albo od źródeł zewnętrznych. Poproś
właściciela o wpisanie `DATABENTO_API_KEY` w zmiennych środowiska i **załóż nową sesję** —
zmienne są kopiowane przy starcie, więc w trwającej sesji się nie pojawią.

Opis PR zawiera bieżący status projektu i jest aktualizowany po każdej sesji roboczej.
