# D5-C — audyt jednodniowej próbki MBO

**Specyfikacja zamrożona przed zakupem:** `docs/D5_ETAP3_SPEC.md` (commit
poprzedza pobranie danych).
**Data wykonania:** 2026-08-04.
**Licznik prób: 0.** Nie mierzono przyszłego zwrotu, trwałości znaku, VIF,
Sharpe'a, P&L, progu, horyzontu ani skuteczności. To audyt pomiaru.

---

## 1. Werdykt

```
D5-C GO
```

**MBO pozwala kanonicznie odtworzyć zdarzenia dopasowania.** Wszystkie dziewięć
zamrożonych pytań zostało rozstrzygniętych; żadne nie okazało się
nierozstrzygalne z powodu braku snapshotu.

**Mianownik jest zamknięty:** wszystkie **842 757** zdarzeń z transakcją mają
przypisaną kategorię, kategorie sumują się co do sztuki, **niewyjaśnionych: 0**
(§3, Q6b).

Kluczowe ustalenie wykracza poza to, o co pytaliśmy: **`order_id` agresora jest
obecny na **100%** rekordów `Trade` i nigdy nie występuje po obu stronach.**
To jest jednostka, której szukaliśmy — i której `(ts_event, sequence, side)`
nie potrafiło dostarczyć.

---

## 2. Próbka i koszt

| | |
|---|---|
| Sesja | 2026-07-30, `MNQU6`, RTH 09:30–16:00 `America/New_York` |
| Okno UTC | `2026-07-30T13:30` … `2026-07-30T20:00` |
| Schemat | `mbo` |
| Rekordów | **38 306 877** (zgodne z `metadata.get_record_count`) |
| Plik na dysku | **0,678 GB** `.dbn.zst` (rozliczeniowo 2,145 GB) |
| SHA-256 | `3e6f023d3d6978a23af9a49256f68dd2862420b32eadab80c7b23abf0974ac42` |
| **Koszt** | **3,5961 USD** przy zamrożonym limicie 4,00 USD |
| Wolne miejsce po pobraniu | 27,6 GB |

Pierwsze podejście zakończyło się **HTTP 504 (timeout bramy)** przy transferze
2,1 GB. Plik nie powstał, manifest nie powstał. Druga próba po 20 s powiodła
się. Traktuję to jako błąd sieciowy, nie odmowę polityki — zgodnie z regułą
ponowiłem z odstępem, bez skracania okna i bez zmiany dnia.

**Przetwarzanie w całości strumieniowe.** Nie powstała pełna zdekompresowana
kopia; nie było momentu, w którym 38 mln rekordów znajdowało się naraz w ramce.
Iteracja po `DBNStore` z licznikami i tablicami `array('q')`; przepustowość
~845 tys. rekordów/s, pełny przebieg ~45 s.

---

## 3. Odpowiedzi na dziewięć zamrożonych pytań

### Q1 — Czy `F_LAST` jest rzeczywiście dostępne

**TAK.** Flaga `F_LAST` (wartość 128) jest ustawiona na większości rekordów;
`flags` przyjmuje wyłącznie wartości `0` i `128`. Potwierdza to odpowiedź
Databento: w `trades` flag nie ma, w `mbo` są i niosą treść.

Rozkład akcji w próbce: `A` (add), `C` (cancel), `M` (modify), `T` (trade),
`F` (fill).

### Q2 — Jak `F_LAST` wyznacza granice zdarzenia

`F_LAST` domyka zdarzenie: rekordy od poprzedniego domknięcia do rekordu
z flagą włącznie. Instrument jest jeden (`MNQU6`), więc granica per instrument
pokrywa się z granicą globalną.

Większość zdarzeń jest jednorekordowa — to zwykłe pojedyncze aktualizacje
księgi. Zdarzenia wielorekordowe to dopasowania.

### Q3 — Jak łączą się rekordy `Trade` i `Fill`

| | |
|---|---|
| Zdarzeń zawierających `Trade` | **842 757** |
| w tym dokładnie jeden `Trade` | **767 588 (91,08%)** |
| **Zdarzeń z `Trade`, ale bez `Fill`** | **0** |

**Zero zdarzeń z transakcją bez wypełnień** — struktura opisana przez Databento
(Trade, po nim rekordy Fill) sprawdza się bez wyjątku.

### Q4 — Czy `Trade` zawiera `order_id` agresora

| | |
|---|---|
| Rekordów `Trade` | 984 113 |
| z niezerowym `order_id` | **984 113 — 100,00%** |
| z `order_id == 0` | **0** |

Databento zastrzegało *„when CME provides one"*. **W tej sesji CME podaje go
zawsze.** To najważniejszy pojedynczy wynik audytu.

### Q5 — Czy zdarzenie dopasowania da się jednoznacznie odtworzyć

**TAK, i to na dwa niezależne sposoby.**

Po pierwsze, przez granice `F_LAST`: 91,08% zdarzeń zawierających transakcję ma
dokładnie jeden rekord `Trade`.

Po drugie — i to jest właściwa odpowiedź — przez **`order_id` agresora**:

| | |
|---|---|
| Unikalnych `order_id` agresora | **903 107** |
| Średnio rekordów `Trade` na agresora | 1,090 |
| Agresorów z jednym `Trade` | 838 685 (92,87%) |
| Agresorów z 2 rekordami | 54 704 (6,06%) |
| Maksimum | 32 rekordy |
| **`order_id` agresora po OBU stronach** | **0 (0,0000%)** |

Rozkład jest dokładnie taki, jakiego oczekuje się od zleceń zdejmujących kilka
poziomów księgi. Zero dwustronnych agresorów — wobec **732 dwustronnych par**
`(ts_event, sequence)`, na których poległo D5-B.

### Q6 — Czy suma pasywnych `Fill` zgadza się z `Trade`

**TAK, w 100,000% — zero niezgodności na 767 588 zdarzeniach.**

Wymagało to **poprawienia niezmiennika po diagnostyce**, i to jest wynik warty
zapisania. Naiwna suma *wszystkich* rekordów `Fill` dawała 6 541 niezgodności
(0,85%). Zrzut zdarzeń niezgodnych pokazał przyczynę:

```
T side=A px=27872.50 sz=1 oid=6880436543628   <- transakcja
F side=A px=27872.50 sz=1 oid=6880436543628   <- Fill AGRESORA (ten sam oid!)
F side=B px=27872.50 sz=1 oid=6880436543923   <- Fill pasywny
```

**`Fill` dostaje także zlecenie agresora, nie tylko pasywne.** Rozpoznaje się
je po tym, że `order_id` jest identyczny z `order_id` rekordu `Trade`.
Właściwy niezmiennik brzmi: **suma `Fill` PASYWNYCH == rozmiar `Trade`** —
i ten trzyma się bez jednego wyjątku.

To nie była wada danych, tylko wada mojej pierwszej reguły zliczania.

### Q6b — Pełny podział zdarzeń: mianownik zamknięty

Niezmiennik Q6 dotyczył **767 588** zdarzeń, podczas gdy zdarzeń z transakcją
jest **842 757**. Różnica 75 169 była w pierwszej wersji raportu niewyjaśniona —
a metryka z niezapisanym mianownikiem jest dokładnie tą pułapką, przed którą
ostrzega wniosek W003. Poniżej podział **rozłączny i wyczerpujący**.

| Kategoria | Zdarzeń |
|---|---|
| `1T_pasywne_zgodne` | **767 588** |
| `1T_pasywne_niezgodne` | 0 |
| `1T_bez_pasywnych` | 0 |
| `wieleT_zgodne` | **75 169** |
| `wieleT_niezgodne` | 0 |
| `wieleT_bez_pasywnych` | 0 |
| `inne` | 0 |
| **Suma kategorii** | **842 757** |
| **Niewyjaśnione** | **0** |

Adnotacje **ortogonalne** (mogą wystąpić w każdej kategorii, więc liczone
osobno i nie sumują się do całości):

| Adnotacja | Zdarzeń | Udział |
|---|---|---|
| zawiera `Fill` agresora | 7 362 | 0,87% |
| dotknięte brakiem snapshotu | **986** | **0,12%** |

Różnica 75 169 to **zdarzenia z więcej niż jednym rekordem `Trade`** — mój
pierwotny niezmiennik ich po prostu nie badał. Po zbadaniu **wszystkie
spełniają niezmiennik**.

#### Poprawka, której wymagało zamknięcie mianownika

Pierwsze przeliczenie dało **8** niezgodności w kategorii `wieleT_niezgodne`.
Obejrzałem wszystkie osiem. Przyczyna jest jedna i **nie jest defektem danych**:

> **Zlecenie będące agresorem w jednej transakcji potrafi być stroną pasywną
> w drugiej — w obrębie tego samego zdarzenia `F_LAST`.**

```
seq=526824624
  T side=B sz=1 oid=…096070   <- agresor kupuje
  F side=A sz=1 oid=…096064      pasywne
  T side=A sz=1 oid=…063131   <- DRUGI agresor sprzedaje
  F side=B sz=1 oid=…096070   <- zlecenie …070, agresor z pierwszej
                                 transakcji, jest tu strona PASYWNA
```

Zbiór agresorów budowany dla **całego zdarzenia** wykluczał ten `Fill` jako
„własny", zaniżając sumę pasywną o dokładnie tę jedną sztukę.

**Rola agresora jest właściwością pojedynczej transakcji, nie zlecenia
w oknie.** Po zmianie przypisania — `Fill` należy do **poprzedzającego go**
rekordu `Trade`, a agresorem jest `order_id` z tego właśnie rekordu —
niezmiennik trzyma się na **842 757 z 842 757, czyli 100,0000%, bez jednego
wyjątku**.

To **trzecia z rzędu** „niezgodność", która okazała się wadą mojej reguły
zliczania, a nie danych: najpierw 6 541 (własny `Fill` agresora), potem 8 (rola
per transakcja). Wzorzec jest na tyle wyraźny, że trafia do rejestru jako
wniosek **W015**.

#### Rozkład agresorów w zdarzeniu — istotny dla D5-B2

| Agresorów w zdarzeniu | Zdarzeń |
|---|---|
| 1 | 822 905 (97,6%) |
| 2 | 10 220 |
| 3 | 3 758 |
| 4 | 1 873 |
| 5 lub więcej | 4 001 |

**2,4% zdarzeń zawiera więcej niż jednego agresora.** Potwierdza to wprost, że
`order_id` nie wolno scalać ani przez sesję, ani nawet przez pojedyncze
zdarzenie `F_LAST`: ten sam identyfikator pełni różne role. Jednostką pozostaje
matching event z agresorem odczytanym z jego **własnego** rekordu `Trade`.

### Q7 — Czy z MBO da się odtworzyć posiadany schemat `trades`

**TAK, dokładnie.**

| | MBO (rekordy `Trade`) | plik `trades` |
|---|---|---|
| Liczba rekordów | **984 113** | **984 113** |
| Suma `size` | **1 790 715** | **1 790 715** |

Zgodność co do rekordu i co do sztuki. To niezależne potwierdzenie, że oba
schematy opisują ten sam strumień i że nasza dotychczasowa próbka `trades`
nie miała ubytków.

### Q8 — Relacja MBO do grupowania po `(ts_event, sequence)`

| | |
|---|---|
| Rekordów `Trade` | 984 113 |
| Unikalnych par `(ts_event, sequence)` | 876 202 |
| Zdarzeń `F_LAST` zawierających `Trade` | 842 757 |
| Par rozciągniętych na >1 zdarzenie | **13 (0,001%)** |

Liczby układają się w hierarchię: **984 113 transakcji → 903 107 agresorów →
876 202 par sekwencyjnych → 842 757 zdarzeń `F_LAST`**.

Para `(ts_event, sequence)` jest **grubsza** od pojedynczej transakcji i
**cieńsza** od zdarzenia `F_LAST` — czyli nie odpowiada żadnej naturalnej
jednostce. Dokładnie to powiedział dostawca; teraz jest to zmierzone.

### Q9 — Czy brak snapshotu cokolwiek uniemożliwia

**NIE — żadnego z pytań Q1–Q8.**

| | |
|---|---|
| Unikalnych zleceń `ADD` w oknie | 16 609 423 |
| Rekordów `Fill` | 1 649 924 |
| `Fill` do zleceń złożonych **w oknie** | **1 646 854 (99,81%)** |
| `Fill` do zleceń **sprzed okna** | **3 070 (0,19%)** |

Tylko 0,19% wypełnień odwołuje się do zleceń złożonych przed 09:30. Dotyczy to
wyłącznie **proweniencji zlecenia pasywnego**, a nie granicy zdarzenia, sumy
wypełnień ani identyfikacji agresora.

**Nie rozszerzam zakupu do północy UTC.** Nie ma ku temu podstawy.

---

## 4. Co to znaczy dla D5

Jednostka mechanizmu jest **obserwowalna**, ale **nie w schemacie `trades`**.
Kanoniczną definicją zdarzenia agresora jest `order_id` agresora z rekordu
`Trade` w MBO — pole, którego w `trades` po prostu nie ma.

To domyka pytanie postawione po degradacji D5-B: nie jest tak, że mechanizmu
nie da się zmierzyć; jest tak, że mierzyliśmy go niewłaściwym narzędziem.

**Czego ten etap NIE ustalił:** czy nierównowaga liczona na poprawnej jednostce
da się odróżnić od równoczesnego momentum. To jest pytanie D5-B2 i wymaga
większej próbki. **Progi z §8 specyfikacji Etapu 2 pozostają niezmienione**
i zostaną zastosowane bez modyfikacji.

---

## 5. Skala dla pełnego miesiąca — do decyzji, nie do zakupu

Pomiary z tej sesji pozwalają oszacować miesiąc rzetelniej niż wcześniejsza
ekstrapolacja:

| | Jedna sesja | 22 sesje RTH (szacunek) |
|---|---|---|
| Koszt | 3,5961 USD | **~79 USD** |
| Rozmiar rozliczeniowy | 2,145 GB | **~47 GB** |
| Plik na dysku | 0,678 GB | **~15 GB** |
| Czas przebiegu | ~45 s | **~17 min** |

Plik na dysku jest **3,2× mniejszy** od rozmiaru rozliczeniowego, co jest
istotne dla planowania miejsca: 22 sesje to ~15 GB skompresowanych, nie 47.

**Zakupu miesiąca nie wykonuję.** Wymaga: konfiguracji `PROJECT_G_DATA_ROOT` na
dysku lokalnym, sprawdzenia rzeczywistego zużycia przez pliki tymczasowe,
ponownej wyceny dokładnie 22 sesji, zamrożenia limitu i osobnej decyzji.

---

## 5a. Smoke test magazynu poza repozytorium

Audyt powtórzony w całości z danymi przeniesionymi poza katalog repozytorium
przez `PROJECT_G_DATA_ROOT`. **Wszystkie liczby identyczne**, plik
`reports/D5_etap3_wyniki.json` zgodny **co do bajtu**.

| | |
|---|---|
| SHA-256 kopii vs manifest | **zgodny** |
| Zdarzeń / podział / niewyjaśnione | **identyczne** |
| Q7 (rekonstrukcja `trades`) | **TAK** |
| Czas przetwarzania | **281,9 s** |
| Szczytowy RSS | **2,106 GB** |
| Wolne miejsce przed / po | **26,9 GB / 26,9 GB** |
| Artefakt wynikowy | 1,8 kB |

Zużycie dysku poza plikiem surowym: **zero** — przetwarzanie strumieniowe nie
tworzy plików tymczasowych.

Przy okazji naprawiona niespójność: ścieżka do pliku `trades` była zapisana na
sztywno i omijała `raw_dir`, więc `PROJECT_G_DATA_ROOT` przenosiło tylko MBO,
a kontrola Q7 po cichu sięgała do repozytorium. **Przy przenosinach na dysk
lokalny dałoby to fałszywy sukces.**

**Czego ten test NIE zastępuje:** uruchomienia na fizycznej maszynie
właściciela projektu z dyskiem 300 GB. Potwierdza mechanizm i odtwarzalność,
nie zachowanie tamtego sprzętu.

---

## 5b. Wycena 22 sesji RTH w MBO — sesja po sesji

`metadata.get_cost` dla dokładnie tych zapytań, które zostałyby wykonane:

| | |
|---|---|
| **Koszt łączny** | **78,6044 USD** |
| Rekordów | 837 310 143 |
| Rozmiar rozliczeniowy | 46,89 GB |
| Szacowany rozmiar na dysku | ~14,8 GB |
| Pozostaje z kredytu 125 USD | 46,40 USD |
| Rozrzut | 0,2498 USD (07-03, sesja skrócona) … 5,7527 USD (07-02) |

Ekstrapolacja zasobów: **~103 min** przetwarzania, szczytowy RSS **~3,4 GB**
(skaluje się z największą pojedynczą sesją — 61,3 mln rekordów — a nie z sumą,
bo przetwarzamy sesja po sesji).

**Zakup niewykonany.** Limit zamrożony w `docs/D5_ETAP4_SPEC.md` na 82,00 USD.

---

## 6. Reprodukcja

| | |
|---|---|
| Zakup | `scripts/fetch_d5c.py` (ponowna wycena przed pobraniem, twardy stop, kontrola dysku) |
| Audyt | `scripts/audit_d5_etap3.py` → `reports/D5_etap3_wyniki.json` |
| Manifest | `data/manifest_d5c.json` — SHA-256, koszt, liczba rekordów, wolne miejsce przed/po |
| `databento` | 0.82.0 |

Plik `.dbn.zst` **nie jest commitowany** (`data/raw/` w `.gitignore`).

---

## 7. Status

**H017 nadal nie powstaje.** Blocker przesunął się z „brak kanonicznej
rekonstrukcji" na „brak próbki wystarczającej do testu identyfikowalności na
poprawnej jednostce".

**P&L nie mierzony. Przyszłe zwroty nietknięte. Licznik prób: 0.**
