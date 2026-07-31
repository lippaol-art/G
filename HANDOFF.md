# HANDOFF — wznowienie pracy nad Projektem G

**Ten dokument jest napisany dla sesji, która nie widziała poprzedniej rozmowy.**
Kontener jest efemeryczny, więc wszystko potrzebne do kontynuacji jest tutaj i w repo.

Data: 31.07.2026 · Branch: `claude/financial-market-strategy-8mb1y1` · PR #4

---

## 1. Stan projektu w dziesięciu liniach

Budujemy laboratorium badawcze do znalezienia oryginalnej strategii na MNQ (Micro E-mini
Nasdaq-100). Dokument założycielski `docs/PLAN.pdf` (49 stron, wersja 1.1 po czterech
niezależnych audytach zewnętrznych) jest **jedynym źródłem prawdy** — kod ma go realizować,
a nie odwrotnie.

Gotowe: fundament repo, rdzeń silnika backtestowego, komplet aparatu walidacyjnego,
strażnicy niezmienników, CI. **233 testy zielone, pokrycie 90%, ruff czysty.**

Niegotowe i zablokowane: **pobranie danych rynkowych (Etap 1)**. Bez nich nie da się
uruchomić ani jednego badania.

| Commit | Zawartość |
|--------|-----------|
| `78b864d` | Dokument v1.1 po audytach (49 stron) |
| `8626064` | Etap 0 + rdzeń silnika (sessions, costs, backtest) + DSR, power |
| `2a743a2` | Strażnicy niezmienników + CI |
| *(ten)* | Framework walidacji + roll, features, metrics, loader + ten dokument |

---

## 2. BLOKER: dostęp sieciowy do Databento

### Objaw

```
$ curl -u "$DATABENTO_API_KEY:" https://hist.databento.com/v0/metadata.list_datasets
curl: (56) CONNECT tunnel failed, response 403
```

### Co już sprawdzono

- `$HTTPS_PROXY/__agentproxy/status` pokazuje wpisy `connect_rejected` dla
  `hist.databento.com:443` z komentarzem *„gateway answered 403 to CONNECT
  (policy denial or upstream failure)"*.
- PyPI działa normalnie (HTTP 200) — blokada dotyczy **konkretnie hosta Databento**,
  nie sieci w ogóle.
- Właściciel projektu dodał domenę do allow-listy środowiska **w trakcie poprzedniej sesji**,
  ale 403 utrzymał się. Polityka egress jest wiązana przy starcie sesji, więc zmiana
  **wymaga nowej sesji**, żeby zadziałać.

### Weryfikacja jedną komendą

```bash
curl -sS --max-time 20 -o /dev/null -w "%{http_code}\n" \
  -u "$DATABENTO_API_KEY:" https://hist.databento.com/v0/metadata.list_datasets
```

`200` = odblokowane, można ruszać z Etapem 1. `000` z błędem 56 = nadal zablokowane.

### Czego NIE robić

- **Nie ponawiać** odmów polityki w pętli. Dokumentacja proxy (`/root/.ccr/README.md`) mówi
  wprost: odmowy 403/407 należy zgłaszać, nie obchodzić. Dwie próby wystarczą do
  stwierdzenia stanu.
- **Nie szukać obejść** (inny host, tunel, wyłączenie weryfikacji TLS). To naruszenie
  polityki organizacji, a nie problem techniczny do rozwiązania.

### Jeśli nadal zablokowane

Alternatywa całkowicie omijająca problem: właściciel pobiera dane lokalnie u siebie
(ten sam skrypt `scripts/build_dataset.py`) i wgrywa gotowe pliki parquet do `data/clean/`.
Reszta pipeline'u działa bez zmian.

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

# 5. Czyszczenie i budowa kontraktu ciągłego  (DO NAPISANIA — patrz sekcja 6)
# 6. Sanity-report                            (DO NAPISANIA — patrz sekcja 6)

# 7. Commit oczyszczonych danych
git add data/clean/*.parquet data/manifest.md
git commit -m "data: MNQ+NQ OHLCV-1m 2019-2026, kontrakt ciągły"
```

**Do `data/manifest.md` wpisz obowiązkowo:** zakres dat, wersję schematu dostawcy, datę
pobrania i sumy kontrolne. Databento zmienił normalizację `GLBX.MDP3` w lipcu 2026 —
bez przypiętej wersji nie odtworzysz później, na czym liczone były wyniki.

---

## 5. Po pobraniu danych: udowodnij, że silnik działa

**Zanim uruchomisz jakiekolwiek badanie**, silnik musi przejść testy z `docs/PLAN.pdf`
rozdz. 5.6. Niesprawdzony silnik produkuje śmieci z dokładnością do sześciu miejsc
po przecinku.

| Test | Oczekiwany wynik | Co oznacza porażka |
|------|------------------|--------------------|
| **Zerowa przewaga** — losowe wejścia, losowy SL/TP | wynik ≈ −(koszty × liczba transakcji), rozkład symetryczny przed kosztami | przeciek informacji w silniku |
| **Znany efekt** — kup na close RTH / sprzedaj na open vs odwrotnie | odtworzenie znanej asymetrii overnight/intraday co do znaku i rzędu wielkości | silnik źle mierzy — to linijka, nie strategia |
| **Symetria** — odwrócenie long↔short na strategii losowej | wynik lustrzany przed kosztami | błąd w obsłudze jednej ze stron |
| **Determinizm** — dwa przebiegi z tym samym ziarnem | wyniki bitowo identyczne | nieziarnowana losowość gdzieś w ścieżce |

Testy `@pytest.mark.needs_data` w `tests/test_features_loader.py` odblokują się automatycznie,
gdy pojawi się `data/clean/mnq_1m_cont.parquet`.

---

## 6. Czego jeszcze nie ma w kodzie

| Element | Uwagi |
|---------|-------|
| Pipeline czyszczenia `raw → clean` | Krok 5 z sekcji 4. Specyfikacja: PLAN rozdz. 4.2 (osiem kroków). Moduł `engine/roll.py` ma już gotowe rolowanie i back-adjust — trzeba je spiąć z wczytywaniem plików dostawcy. |
| Sanity-report | PLAN rozdz. 4.6. Uwaga krytyczna: **brak bara nie jest luką w danych** — Databento nie drukuje bara, gdy nie było transakcji. Raport ma rozróżniać `expected_gap` od `anomaly_gap` przez kalendarz CME (`engine/sessions.py` ma gotową funkcję `is_expected_gap`). |
| Kalendarz zdarzeń makro | PLAN rozdz. 4.5. Scraping do `data/clean/events.csv`. |
| Warstwa danych K6 | PLAN rozdz. 4.7 — ES, wagi NDX, ceny after-hours megacapów. Potrzebna dopiero do partii 2. |
| Pętla główna backtestu | `engine/backtest.py` ma rozstrzyganie wewnątrzbarowe i warstwę ryzyka; brakuje spinającej pętli iterującej po barach. |

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
  sessions.py    segmentacja doby w ET, DST, kalendarz CME, klasyfikacja luk
  costs.py       koszty i poślizg (baza 2.20 USD RT, skalowanie zmiennością)
  backtest.py    rozstrzyganie wewnątrzbarowe (tabela 5.4), warstwa ryzyka
  guards.py      HistoryView (blokada lookaheadu), zakaz volume==0, rozdzielenie serii
  roll.py        rolowanie wolumenowe, back-adjust różnicowy, px_raw/px_adj
  features.py    ATR, VWAP, percentyle, poziomy referencyjne (tylko na px_raw)
  metrics.py     PF, Sharpe + poprawka Lo, Sortino, MDD, MAR, SQN, koncentracja
  loader.py      GRANICA — wymaga danych w data/clean/

validation/
  dsr.py         Deflated Sharpe Ratio, SR₀ wg FST, N_eff przez ONC
  power.py       moc testu, liczność próby
  walkforward.py okna 12m/3m, purge + embargo, lockbox
  cpcv.py        Combinatorial Purged CV — 15 ścieżek zamiast jednej
  pbo.py         Probability of Backtest Overfitting (bramka < 0.20)
  spa.py         test SPA Hansena
  montecarlo.py  permutacja, bootstrap blokowy BCa, syntetyki
  trial_counter.json   globalny licznik prób

scripts/build_dataset.py   pobranie danych (czeka na odblokowanie sieci)
tests/                     233 testy, w tym regresja na liczbach z PLAN.pdf
```

---

## 10. Jak zacząć następną sesję

```bash
git pull
cat HANDOFF.md                      # ten plik
cat hypotheses/REGISTRY.md          # co żyje, co umarło, jakie wnioski
cat validation/trial_counter.json   # budżet prób
PYTHONPATH=. pytest -q              # czy wszystko nadal zielone

# sprawdź bloker sieciowy (sekcja 2) i jeśli 200 — ruszaj z sekcją 4
```

Opis PR #4 zawiera bieżący status projektu i jest aktualizowany po każdej sesji roboczej.
