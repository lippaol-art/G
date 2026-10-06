# D5-B — wynik testu identyfikowalności

> ## ⚠ WERDYKT ZASTĄPIONY PO ODPOWIEDZI DATABENTO
>
> **Obliczenia dla empirycznej agregacji pozostają odtwarzalne, ale `sequence`
> nie identyfikuje pojedynczego matching event. Główny warunek pomiarowy A jest
> więc niespełniony.**
>
> **Aktualny status: `D5-B INCONCLUSIVE — niewłaściwa jednostka pomiaru`.**
>
> Odpowiedź Databento z 2026-08-04 (pełna treść: `docs/D5_PYTANIE_DATABENTO.md`
> §C) stwierdza, że `sequence` jest numerem sekwencyjnym wiadomości CME, a jedna
> wiadomość może zawierać wiele Trade Summaries, również po przeciwnych
> stronach. Reguła `(ts_event, sequence, side)` **nie jest** identyfikatorem
> jednego zdarzenia agresora.
>
> **Ten raport zostaje w repozytorium bez zmian poniżej tego bloku.** Nie
> usuwam go i nie przepisuję historii tak, jakby błąd nigdy nie wystąpił —
> wszystkie liczby są poprawne dla zadeklarowanego agregatu empirycznego,
> błędna była jego interpretacja jako liczby zdarzeń agresora.
>
> Co pozostaje w mocy: potwierdzenie `ts_recv` jako podstawy agregacji barów
> (§3 i pytanie Q6), zgodność rekonstrukcji 8 400 z 8 400 minut, poprawność
> pola `side`, oraz cała kontrola jakości danych.
>
> Czego nie wolno zrobić: **B i C nie mogą przejąć roli A.** Były kontrolami
> pomiaru, a zmiana głównej definicji po zobaczeniu wyników złamałaby regułę
> zamrożoną przed zakupem.
>
> **Licznik prób: 0.** Żaden przyszły zwrot ani P&L nie został obejrzany.

---

**Specyfikacja zamrożona przed zakupem:** `docs/D5_ETAP2_SPEC.md`
(commit `91d2649`, poprawka zakresu RTH `00fdcad`).
**Data wykonania:** 2026-08-03.
**Licznik prób: 0** — Etap 2 nie mierzy P&L, zwrotów przyszłych ani skuteczności
kierunku. H017 nie powstaje w tym dokumencie.

---

## 1. Werdykt

```
D5-B GO          <- ZASTĄPIONY 2026-08-04, patrz blok na początku dokumentu
D5-B INCONCLUSIVE — niewłaściwa jednostka pomiaru   <- STATUS AKTUALNY
```

Wszystkie sześć warunków z §8 specyfikacji zostało spełnionych **liczbowo**,
a kontrole B i C były zgodne z A. Warunki mierzyły jednak identyfikowalność
agregatu, który — jak potwierdził dostawca — nie odpowiada zadeklarowanej
jednostce mechanizmu. Tabela poniżej pozostaje poprawnym zapisem pomiaru.

| # | Warunek z §8 | Wymóg | Zmierzone | |
|---|---|---|---|---|
| 1 | pooled VIF | < 5 | **1,548** | OK |
| 2 | mediana dziennego VIF | < 5 | **1,787** | OK |
| 3 | udział sesji z VIF < 5 | ≥ 75% | **100%** (21/21) | OK |
| 4 | zależność od jednej pory dnia | ≤ 20% | **9,99%** | OK |
| 5 | obie strony agresji, najsłabsza sesja | ≥ 20% okien | **39,2%** | OK |
| 6 | udział jednej sesji w zmienności | ≤ 20% | **10,21%** | OK |

**Co ten werdykt znaczy:** nierównowaga zdarzeń agresora w oknie 60 s **nie jest
odtwarzalna** z równoczesnego momentum ceny, jego przekształceń, wolumenu ani
efektów pory dnia. Model pomocniczy tłumaczy 35,4% jej wariancji; 64,6%
pozostaje poza zasięgiem benchmarku.

**Czego NIE znaczy:** że ta reszta ma wartość prognostyczną. Etap 2 nie mierzył
niczego, co dotyczy przyszłości. Zmienna przeszła wyłącznie test, na którym
upadło D1 — nie jest przebraniem istniejącego benchmarku.

---

## 2. Próbka

| | |
|---|---|
| Instrument | `MNQU6`, `GLBX.MDP3`, schemat `trades` |
| Zakres | 22 sesje RTH lipca 2026 (2026-07-01 … 2026-07-30) |
| RTH | `09:30–16:00 America/New_York`, UTC **wyprowadzane ze strefy** |
| Wypełnień | **22 080 246** (21 sesji z D5-B + 2026-07-30 z Etapu 1) |
| `side == NONE` | **4** rekordy na 22 080 246 |
| `candidate_aggressor_event` | 19 837 327 |
| Grup niejednoznacznych (wykluczonych) | **732** — 0,0037% grup, 0,0035% wolumenu |
| Okien 60 s | **8 400** |
| Sesji kompletnych | 21 (2026-07-03 skrócona — 210 okien zamiast 390) |

Sesja `2026-07-30` pochodzi z Etapu 1 i została przycięta do RTH.
Sesja `2026-07-31` nie została kupiona — brak odniesienia OHLCV do kontroli.

### Koszt

| | |
|---|---|
| Limit zamrożony w specyfikacji | **30,00 USD** |
| Wycena 21 sesji przed zakupem | **26,406 USD** |
| Możliwe obciążenie ponad wycenę | ≤ 1,510 USD |
| Górna granica rzeczywistego kosztu | **≤ 27,916 USD** |

Rozbieżność ma jedną przyczynę i podaję ją jawnie: pierwsze podejście urwało
transfer sesji `2026-07-07`, a ponowne pobranie tej sesji mogło zostać
naliczone drugi raz. Databento nie udostępnia w API endpointu rozliczeniowego
(`metadata` ma tylko `get_cost` i `get_billable_size`), więc **nie potrafię
odczytać rzeczywistej kwoty z konta** — podaję granicę górną zamiast liczby,
której nie zmierzyłem. Nawet ta granica mieści się w limicie 30,00 USD.

---

## 3. Bramka §10 — rekonstrukcja OHLCV przed VIF

Specyfikacja wymaga, żeby **każda niezgodność została wyjaśniona przed
liczeniem VIF**. Skrypt `scripts/verify_d5b_bars.py`, wynik:

| | |
|---|---|
| Minut porównanych | **8 400** |
| Niezgodnych `open` / `high` / `low` / `close` | **0 / 0 / 0 / 0** |
| Niezgodnych `volume` | **0** |
| Minut tylko u dostawcy | **0** |
| Minut tylko w rekonstrukcji | **0** |
| Przecięcia zakresów między plikami sesji | **0** |

Zgodność doskonała na całym miesiącu — nie ma niezgodności do wyjaśnienia.
Potwierdza to ustalenie z Etapu 1 na drugiej, dwudziestodwukrotnie większej
próbce: bary Databento powstają na **`ts_recv`**, i tylko agregacja po tym
znaczniku daje zgodność co do jednego bara.

Kontrola braku duplikatów na granicy z `2026-07-30` przeszła: zakresy czasowe
wszystkich 22 plików są rozłączne.

---

## 4. Wyniki pełne

Model pomocniczy — **nie zawiera przyszłego zwrotu**:

```
I ~ m + |m| + m² + sign(m) + log(1 + volume) + efekty pory dnia
```

gdzie `m = log(P_last / P_first)` w **tym samym** oknie 60 s.

| | A `I_count` (główna) | B po wypełnieniach | C `I_volume` |
|---|---|---|---|
| pooled VIF (z porami dnia) | **1,548** | 1,971 | 2,291 |
| pooled R² | 0,3542 | 0,4925 | 0,5635 |
| pooled VIF (bez pór dnia) | 1,532 | 1,957 | 2,283 |
| mediana dziennego VIF | 1,787 | 2,374 | 2,773 |
| p10 / p90 dziennego VIF | 1,631 / 2,063 | 2,133 / 2,624 | 2,290 / 3,318 |
| sesji z VIF < 5 | 21/21 | 21/21 | 21/21 |
| max udział jednej sesji | 10,21% | 8,37% | 7,03% |

Rozkład stron agresji: okien z `I > 0` — 51,8%, `I < 0` — 47,8%, `I = 0` — 0,5%.

### Trzy odczyty, które warto zapisać

**Pooled VIF prawie nie zmienia się po usunięciu pór dnia** (1,548 → 1,532).
To jest bezpośrednia odpowiedź na klauzulę `INCONCLUSIVE` z §8: identyfikacja
**nie** pochodzi z efektów pory dnia. Dzienne VIF-y liczone są w obrębie
pojedynczych sesji i również są niskie — więc nie pochodzi też z różnic
**między** sesjami. Tym właśnie ten wynik różni się od D1, gdzie cała
identyfikacja siedziała w wolnym trendzie.

**Kolejność A < B < C jest spójna z mechanizmem, a nie z nim sprzeczna.**
Miara po wolumenie jest najbardziej odtwarzalna z ceny (R² = 0,56), bo duże
wypełnienia i ruch ceny to w dużej mierze to samo zdarzenie. Miara po
zdarzeniach agresora jest najmniej odtwarzalna (R² = 0,35). Zgodne z tym,
że zliczanie zdarzeń niesie informację o **liczbie decyzji**, a nie o ich
wielkości — i to właśnie dlatego A jest zmienną główną.

**B i C są kontrolami pomiaru i nie zastępują A.** Zgodnie z decyzją
właściciela projektu werdykt główny pochodzi wyłącznie z A; B i C sprawdzają
jedynie, czy wynik nie jest artefaktem konkretnej definicji nierównowagi.
Nie zostały użyte do zmiany werdyktu po zobaczeniu liczb.

---

## 5. Błąd wykryty i naprawiony w trakcie — przepełnienie bez znaku

**Pierwszy przebieg audytu dał `D5-B NO-GO`. Ten wynik był fałszywy i nie
został nigdzie zaraportowany jako rezultat.**

Kolumny `n_buy`, `n_sell`, `f_buy`, `f_sell`, `v_buy`, `v_sell` powstają
z agregacji polars jako typy **bez znaku**. Różnica `n_buy − n_sell` nie
wychodziła ujemna, tylko przepełniała się do ~1,8·10¹⁹ w każdym oknie, gdzie
przeważała strona sprzedająca — czyli w blisko połowie próbki.

Wykrycie nie było przypadkiem: koncentracja 58,50% zmienności na jednej sesji
była niewiarygodna przy 22 sesjach, a diagnostyka pokazała średnią `I_count`
równą 1 509 827 przy zmiennej **z konstrukcji ograniczonej do [−1, +1]**.
Wartość poza tym przedziałem jest dowodem błędu obliczenia, nie własnością
rynku.

| Miara | Przed naprawą (fałszywe) | Po naprawie |
|---|---|---|
| pooled VIF (A) | 1,482 | 1,548 |
| mediana dziennego VIF (A) | 1,558 | 1,787 |
| max udział jednej sesji (A) | **58,50%** | **10,21%** |
| werdykt | `NO-GO` | `GO` |

To ta sama klasa błędu, która wystąpiła w Etapie 1 na różnicy wolumenów
i została tam udokumentowana. Wystąpiła po raz drugi, w innym pliku —
dlatego naprawa nie polega tylko na rzutowaniu:

1. rzutowanie na `Int64` przeniesione **do miejsca agregacji**, żeby żadne
   późniejsze wyrażenie nie mogło błędu odtworzyć,
2. dodany **strażnik**: wszystkie trzy nierównowagi muszą leżeć w [−1, +1],
   inaczej skrypt przerywa z błędem zamiast policzyć VIF z liczb bez sensu.

Wniosek do reguł projektu: **każda zmienna o znanym z konstrukcji zakresie
dostaje jawną asercję tego zakresu.** Ten błąd nie rzuca wyjątku i nie psuje
wykresu — zmienia werdykt.

---

## 5a. Grupy niejednoznaczne — druga zaległość w implementacji

Specyfikacja §3 („Obsługa grup niejednoznacznych") nakazuje: gdy grupa zawiera
obie strony, **nie przypisywać jej do strony dominującej**, oznaczyć jako
niejednoznaczną, **wykluczyć z `I_count`** i podać jej udział. Pierwsza wersja
skryptu tego nie robiła.

Ponieważ `side` jest częścią klucza, pojedyncza grupa nigdy nie ma obu stron —
ale para `(ts_event, sequence)` **może** wystąpić po obu stronach, i wtedy klucz
nie izoluje jednego zlecenia agresora. To jest przypadek, o który chodzi.

| | |
|---|---|
| Par `(ts_event, sequence)` z obiema stronami | **732** |
| Udział w liczbie grup | **0,0037%** |
| Udział w wolumenie | **0,0035%** |
| Wpływ na wyniki po wykluczeniu | **żaden do czwartego miejsca po przecinku** |

Wykluczenie zostało wprowadzone i wyniki w §4 są policzone **po** nim. Skala
jest pomijalna, ale reguła obowiązuje niezależnie od tego, czy zmienia wynik —
gdyby obowiązywała tylko wtedy, kiedy zmienia, nie byłaby regułą.

Te 732 przypadki są jednocześnie **treścią pytania P2 do Databento**: jeśli
`sequence` identyfikuje jedno zdarzenie dopasowania, nie powinny istnieć.

---

## 6. Warunki 4 i 5 — brak implementacji zamrożonej specyfikacji

Pierwsza wersja skryptu sprawdzała **cztery** warunki z §8, podczas gdy
specyfikacja wymienia **sześć**. Brakowało warunku 4 (niezależność od jednego
segmentu dnia) i warunku 5 (zmienność obu stron agresji).

Dopisałem oba. Zaznaczam wprost, bo kolejność zdarzeń wygląda niekorzystnie —
warunki zostały dodane **po** zobaczeniu, że pozostałe cztery przechodzą:

- oba warunki pochodzą z dokumentu zamrożonego **przed zakupem danych**, więc
  ich dodanie jest uzupełnieniem braku implementacji, nie zmianą progu;
- oba mogą werdykt wyłącznie **zaostrzyć** — dodanie warunku nigdy nie zamienia
  `NO-GO` w `GO`;
- próg 20% dla pory dnia jest tym samym progiem, który specyfikacja ustaliła
  dla sesji, zastosowanym przez analogię — zapisuję to jako moją decyzję,
  nie jako cytat ze specyfikacji.

---

## 7. Reprodukcja

| | |
|---|---|
| Skrypt zakupu | `scripts/fetch_d5b.py` |
| Bramka §10 | `scripts/verify_d5b_bars.py` → `reports/D5_etap2_bary.json` |
| Audyt | `scripts/audit_d5_etap2.py` → `reports/D5_etap2_wyniki.json` |
| Manifest z SHA-256 każdego pliku | `data/manifest_d5b.json` |
| `databento` | 0.82.0 |

Pliki `.dbn.zst` nie są commitowane (`data/raw/` w `.gitignore`). Manifest
zawiera parametry zapytań, granice UTC, liczby rekordów, rozmiary i sumy
kontrolne wszystkich 21 plików.

---

## 8. Otwarte pytanie do Databento

Przygotowane w `docs/D5_PYTANIE_DATABENTO.md`. Dotyczy semantyki pola
`sequence`, znaczenia flagi `F_LAST` i tego, dlaczego `flags` jest w tej
próbce zawsze zerowe. **Reguła grupowania `(ts_event, sequence, side)`
pozostaje przyjęta warunkowo** — jako empiryczne przybliżenie zdarzenia
agresora, nie jako potwierdzony identyfikator pojedynczego zlecenia.
Odpowiedź musi być dołączona do dokumentacji przed powstaniem H017.

---

## 9. Status statystyczny i co dalej

**Cały lipiec 2026 jest development setem.** Nie jest OOS i nie stanie się OOS
po zamrożeniu H017.

Zgodnie z §11 specyfikacji `GO` uprawnia do:

1. powstania karty H017 z zamrożonym mechanizmem, **znakiem**, oknem
   i wykonaniem — wyłącznie dla RTH,
2. pre-flightu trwałości znaku na wykonalnym horyzoncie,
3. dopiero potem pierwszego backtestu i **próby nr 1**.

**H017 nie powstaje w tym dokumencie. P&L nie został zmierzony.
Licznik prób: 0.**
