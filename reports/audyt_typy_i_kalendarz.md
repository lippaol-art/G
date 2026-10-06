# Dwa defekty techniczne przed H017 — raport zamknięcia

Data: 2026-08-03. Zakres: naprawa flagi `short_day` oraz wąski audyt odejmowania
kolumn bez znaku. **Zero pomiarów przyszłych zwrotów, zero P&L, licznik prób: 0.**

---

## Część I — `short_day`

### Defekt był większy niż zgłoszony

Zgłoszenie dotyczyło jednego dnia (`2026-07-03`). Rzeczywisty zasięg:

```
short_day == True:  0 barów z 2 551 265
```

`build_continuous` wywoływał `SessionCalendar()` **bez argumentów**, więc zbiór
`short_days` był pusty. Kolumna istniała w schemacie, przechodziła walidację
`engine.loader.REQUIRED_COLUMNS` i **zawsze miała wartość False**. Nie było to
błędne oznaczenie jednej sesji, tylko martwa flaga w całym zbiorze.

Nikt tego nie zauważył, bo — jak pokazał przegląd — **żaden moduł badawczy,
walidacyjny ani raport jej nie czytał**. To jest właściwa lekcja: kolumna, której
nic nie konsumuje, nie ma jak się zdemaskować.

### Źródło prawdy: reguła, nie liczba barów

Nowy `engine/cme_calendar.py` zapisuje reguły opublikowanego harmonogramu CME
Equity Index. Dane rynkowe **weryfikują** te reguły, nigdy ich nie wyprowadzają.

To rozróżnienie ma konkretne uzasadnienie w tym zbiorze. Klasyfikator oparty na
liczbie barów uznałby za sesje skrócone:

| Dzień | Barów RTH | Co to naprawdę jest |
|---|---|---|
| 2020-02-28 | 89 | **defekt danych** (`degraded`) — szczyt krachu covidowego |
| 2020-06-30 | 41 | **defekt danych** (`degraded`) |

Oba są oznaczone w `degraded_days.json` i **żaden nie jest dniem skróconym**.
Brak transakcji nie jest skróconą sesją.

### Ustalenie, którego poprzedni kod nie mógł wyrazić: dwa różne zamknięcia

`close_time` zwracało stałe 13:00 dla każdego dnia skróconego. To jest błędne
dla jednej trzeciej z nich:

| Zamknięcie | Kiedy | Barów RTH |
|---|---|---|
| **13:00 ET** (12:00 CT) | sam dzień świąteczny: MLK, Dzień Prezydentów, Memorial Day, Juneteenth, 4 lipca, Labor Day, Święto Dziękczynienia | 210 |
| **13:15 ET** (12:15 CT) | dzień przylegający: 3 lipca, piątek po Święcie Dziękczynienia, 24 grudnia | 225 |

Różnica to 15 minut sesji, potwierdzona na **wszystkich 66 dniach skróconych**
w zbiorze 2019–2026.

### Dlaczego 2026-07-03 zachowuje się inaczej niż 2025-07-03

4 lipca 2026 wypada w **sobotę**, więc święto obserwowane przypada w piątek
3 lipca. To sesja świąteczna (13:00, 210 barów), a nie przeddzień święta
(13:15, 225 barów). Ta sama sytuacja wystąpiła w 2020 roku. Dane potwierdzają
oba przypadki.

### Testy zgodności z danymi złapały dwa błędy w moich własnych regułach

Nie w przeglądzie kodu — w konfrontacji z danymi:

1. **Nowy Rok w sobotę NIE przenosi się na poprzedzający piątek.** Przyjąłem
   regułę symetryczną i błędnie oznaczyłem `2021-12-31` jako święto. Dane:
   ten dzień miał pełną sesję RTH. Piątek przed 1 stycznia należy do
   poprzedniego roku i rynek go nie zamyka. Boże Narodzenie przenosi się
   normalnie w obie strony (`2021-12-24`, `2022-12-26` — potwierdzone).
2. **`2025-01-09` to jednorazowe zamknięcie** (ogólnokrajowy dzień żałoby),
   którego żaden algorytm kalendarzowy nie odtworzy. Wpisane jawnie do tablicy
   `ZAMKNIECIA_JEDNORAZOWE`.

Trzeci fałszywy alarm był wadą **testu, nie kalendarza**: wykluczałem dni
zdegradowane ze zbioru sesji, a potem ich brak traktowałem jako dowód święta.
Dawało to dziewięć fałszywych trafień, w tym `2025-11-28`, który sesję ma
(225 barów), tylko oznaczoną jako `degraded`.

### Dokładny wpływ na dane — zmierzony, jeszcze NIEZASTOSOWANY

Przebudowa do katalogu tymczasowego, porównanie kolumna po kolumnie:

| | MNQ | NQ | ES |
|---|---|---|---|
| liczba wierszy | bez zmian | bez zmian | bez zmian |
| `open`, `high`, `low`, `close`, `volume` | **0 różnic** | **0** | **0** |
| `px_raw`, `px_adj`, `contract`, `trade_date`, `segment` | **0 różnic** | **0** | **0** |
| `short_day` | 72 206 | 72 494 | 72 383 |
| `gap_kind` | 192 | 113 | 178 |

**Obie zmiany idą wyłącznie w jednym kierunku:**

- `short_day`: **tylko `False → True`**, 64 dni. Nic nie zostało odznaczone.
- `gap_kind`: **tylko `anomaly → expected`**, zero w drugą stronę. To poranki
  po świętach — `2019-07-05`, `2019-11-29`, `2019-12-26`, `2020-01-02`,
  `2020-04-13`. Wcześniej były zgłaszane jako anomalie, bo kalendarz był pusty.

### Co z tego wynika dla wcześniejszych wyników

| Artefakt | Zależy od flagi? | Wpływ |
|---|---|---|
| Wnioski **W001–W013** | nie — nic nie czyta `short_day` | **żaden** |
| Karty hipotez, próby | nie | **żaden**, licznik prób nadal 0 |
| `reports/data_quality.md` | **tak** — czyta `gap_kind` | liczba anomalii spadnie o 192 / 113 / 178 |
| `golden/baseline.json` | tak, przez `hash_danych` | zmieni się po przebudowie |

**Zatrzymuję się przed przebudową `data/clean/` i przed aktualizacją
baseline'u.** Zgodnie z regułą: naprawa zmienia próbkę i jeden raport, więc
dokładny wpływ trafia do decyzji właściciela projektu, zanim cokolwiek zostanie
nadpisane. Kod jest naprawiony i otestowany; dane pozostają w poprzednim stanie.

**Stan pośredni jest świadomy:** `build_continuous` produkuje teraz inne wyjście
niż to, które leży w `data/clean/`. Testy przechodzą, bo weryfikują reguły
kalendarza wobec **czasów barów**, które się nie zmieniają.

---

## Część II — audyt odejmowania kolumn bez znaku

### Dlaczego dokumentacja nie wystarczyła

Ta klasa błędu wystąpiła dwa razy:

| Kiedy | Gdzie | Skutek |
|---|---|---|
| Etap 1 D5 | różnica wolumenów | złapane przed raportowaniem |
| Etap 2 D5 | `n_buy − n_sell`, `f_buy − f_sell`, `v_buy − v_sell` | **fałszywy werdykt `NO-GO`** |

Po Etapie 1 zapisałem regułę „rzutuj na `Int64`". Reguła była poprawna
i **nie zadziałała**, bo trzeba jeszcze pamiętać, żeby ją zastosować.
Stąd dwie warstwy niezależne od pamięci autora.

### Warstwa 1 — skaner statyczny (`scripts/audit_typy_bez_znaku.py`)

Skaner AST szukający odejmowań wyrażeń polars bez rzutowania. **Pierwsza wersja
zwróciła zero trafień na całym repozytorium** — i to był fałszywy komfort:
sprawdzona na znanym błędzie, przepuściła go.

Powód jest pouczający. Wymagałem, żeby `.sum()`/`.len()` wystąpiło w **tym
samym wyrażeniu**. Tymczasem w błędzie Etapu 2:

```python
(pl.col("n_buy") - pl.col("n_sell")) / (pl.col("n_buy") + pl.col("n_sell"))
```

brak znaku przyszedł z agregacji wykonanej **piętro wyżej**, przy tworzeniu
kolumn. Żadna analiza pojedynczego wyrażenia tego nie zobaczy.

Drugi ślepy punkt: detekcja po `pl.col(` przepuszczała formę `z["volume"] −
z["v"]`, czyli dokładnie zapis błędu Etapu 1.

Po obu poprawkach skaner łapie wszystkie trzy znane przypadki i pomija
poprawnie zabezpieczony. Zgłasza **46 kandydatów** — świadomie z fałszywymi
alarmami, bo są tańsze niż drugi taki werdykt.

### Wynik ręcznej oceny 46 kandydatów

| Kategoria | Ile | Ocena |
|---|---|---|
| różnice cen (`px_adj − close`, `high − low`, logarytmy, VWAP) | 38 | `Float64` — **bezpieczne** |
| różnice ETF (`aum`, `nav`, `sh` w `audit_d1.py`) | 3 | `Float64` — **bezpieczne** |
| `n_buy/f_buy/v_buy` w `audit_d5_etap2.py` | 3 | **naprawione** — rzutowanie przy agregacji |
| `z["volume"] − z["r_volume"]` w `verify_d5b_bars.py` | 1 | **zabezpieczone** — oba `Int64` |
| `z["volume"] − z["v"]` w `audit_d5_etap1.py` | 1 | **zabezpieczone** po Etapie 1 |

**Nie znaleziono ani jednego niezabezpieczonego wystąpienia.** Jedyna kolumna
bez znaku w schemacie `data/clean/` to **`volume` (UInt64)**, i każde miejsce,
w którym wchodzi w odejmowanie, ma jawne rzutowanie.

**Żaden opublikowany raport Gen1 nie jest dotknięty tym błędem.**

### Warstwa 2 — asercje zakresu (`engine/guards.py`)

Kontrola **niezależna od tego, czy autor pamiętał o rzutowaniu**. Zmienna
o znanych z konstrukcji granicach musi w nich leżeć; wartość poza nimi jest
dowodem błędu obliczenia, nie własnością rynku.

| Funkcja | Zakres |
|---|---|
| `assert_imbalance` | [−1, +1] |
| `assert_udzial` | [0, 1] |
| `assert_prawdopodobienstwo` | [0, 1] |
| `assert_liczebnosc` | ≥ 0 |
| `assert_vif` | ≥ 1 |

Podłączone w `scripts/audit_d5_etap2.py` w **siedmiu** punktach obliczenia.
Werdykt `D5-B GO` powtórzony z asercjami — bez zmiany.

Testy (`tests/test_zakresy.py`, 17 przypadków) **odtwarzają prawdziwe
przepełnienie** na typach `UInt64` zamiast symulować je stałą — dzięki temu
przestaną chronić, gdyby polars zmienił zachowanie, zamiast po cichu przechodzić.
Asercja `NaN` jest osobnym przypadkiem: metryka zwracająca `NaN` nie może cicho
przejść (wniosek W003).

Jeden błąd złapany przy podłączaniu: `_skrajne` nie przyjmowało skalara, więc
asercja wywracała się dokładnie tam, gdzie miała chronić. Naprawione i pokryte
testem.

---

## Stan po naprawach

```
481 testów zielonych, 1 pominięty (wymaga danych)
ruff w zakresie CI: czysto
golden baseline: ZGODNY (dane nieprzebudowane)
licznik prób: 0
```

## Czego to nie zamyka

Droga do H017 wymaga jeszcze **odpowiedzi Databento** (`docs/D5_PYTANIE_DATABENTO.md`,
wiadomość gotowa, **niewysłana** — w tej sesji nie ma włączonego kanału poczty)
oraz **decyzji o przebudowie `data/clean/`** wraz z aktualizacją baseline'u.
