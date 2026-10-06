# D5-B2 — test identyfikowalności na kanonicznej jednostce

**Specyfikacja zamrożona PRZED zakupem** (reguła R4). Commit z tym plikiem
poprzedza jakiekolwiek pobranie miesięcznej próbki `mbo`.

**Data zamrożenia:** 2026-08-04.
**Poprzednicy:** `D5-B INCONCLUSIVE` (niewłaściwa jednostka), `D5-C GO`
(jednostka znaleziona i odtworzona bez wyjątków).
**Licznik prób: 0.** Ten etap nie mierzy przyszłych zwrotów ani P&L.

**Nie zastępuje `docs/D5_ETAP2_SPEC.md`.** Tamten dokument zostaje w repozytorium
jako zapis, dlaczego interpretacja `sequence` była niewłaściwa.

---

## 1. Kanoniczna jednostka: agresywna akcja

Definicja zamrożona **przed** zobaczeniem jakiegokolwiek wyniku. Wynika
bezpośrednio z pomiarów D5-C, nie z wygody obliczeniowej.

### 1.1 Reguła podstawowa

1. Rekord **`Trade`** rozpoczyna transakcję.
2. Następujące po nim rekordy **`Fill`** — aż do następnego `Trade` albo końca
   koperty `F_LAST` — należą **do tej transakcji**.
3. **Strona i agresor pochodzą z bieżącego rekordu `Trade`**, nie z koperty
   i nie z globalnego `order_id`.
4. `Fill` o `order_id` identycznym z bieżącym `Trade` jest **wypełnieniem
   agresora**, nie stroną pasywną. Pasywne są wyłącznie pozostałe.

### 1.2 Łączenie wielopoziomowego sweepu

Kolejne rekordy `Trade` o **tym samym `order_id` i tej samej stronie** łączy
się w jedną agresywną akcję **wyłącznie wtedy**, gdy tworzą **bezpośrednio po
sobie następujący ciąg w tej samej kopercie `F_LAST`**.

### 1.3 Ponowne pojawienie się `order_id`

Ponowne wystąpienie tego samego `order_id` **po innym agresorze** stanowi
**nową akcję**. Nie scalamy przez przerwę.

**Pasywne wystąpienie tego samego `order_id` nigdy nie jest scalane z jego
wcześniejszą rolą agresora.**

### 1.4 Dlaczego akurat tak — dowód z D5-C

Trzy pomiary wykluczają prostsze definicje:

| Kandydat na jednostkę | Dlaczego odrzucony |
|---|---|
| `(ts_event, sequence, side)` | **732 pary dwustronne**; dostawca oficjalnie odrzucił jako identyfikator zdarzenia |
| Koperta `F_LAST` jako jedna obserwacja | **19 852 zdarzeń (2,4%) zawiera ≥ 2 agresorów** — koperta nie ma jednoznacznego znaku |
| Globalny `order_id` w sesji | ten sam identyfikator **zmienia rolę** z agresywnej na pasywną, także wewnątrz jednej koperty |

### 1.5 Znacznik dostępności

Czasem dostępności akcji jest **`ts_recv` jej ostatniego rekordu**.

Uzasadnienie: `ts_recv` wyznacza moment, w którym informacja była dostępna
odbiorcy — potwierdzone oficjalnie przez Databento (odpowiedź Q6:
*„GLBX.MDP3 OHLCV bars are aggregated using `ts_recv`"*). Ostatni rekord, bo
akcja nie jest zaobserwowana, dopóki się nie zakończy.

---

## 2. Okno obserwacji

**60 sekund**, wyrównane do pełnych minut **według `ts_recv`**, rozłączne,
w RTH `09:30–16:00 America/New_York` (UTC **wyprowadzane ze strefy**).

### 2.1 Akcje przecinające granicę minuty

Akcja należy do minuty, w której wypada **`ts_recv` jej ostatniego rekordu**,
w całości i bez podziału. Akcja nigdy nie jest dzielona między okna.

Zapisane jawnie, bo jest to decyzja, a nie oczywistość: alternatywą byłoby
przypisanie po pierwszym rekordzie albo proporcjonalny podział. **Nie testujemy
tych wariantów** — byłyby to warianty wybrane przed kartą.

### 2.2 Okno bez transakcji

Obserwacja **brakująca**, nie zerowy zwrot. Łączenie przez `inner`, bez
uzupełniania zerami.

### 2.3 Sesja skrócona — 2026-07-03 (uzupełnienie *ex ante*, 06.08.2026)

**Zapisane PRZED pobraniem miesiąca i przed jakąkolwiek analizą.** Powód
zapisania teraz jest ten sam, dla którego istnieje cała ta specyfikacja: reguła
ustalona po zobaczeniu wyniku nie jest regułą, tylko wyborem.

**Fakt.** 4 lipca 2026 wypada w sobotę, więc 3 lipca jest dniem handlowym
z zamknięciem **13:00 ET**. Potwierdzone dwustronnie: `cme_calendar(2026, 2026)`
zwraca dla tej daty `short_day` i `close_time = 13:00`, a darmowa wycena
Databento daje **2 660 629 rekordów** wobec ~35 mln typowych dla pełnej sesji.

**Konsekwencja mechaniczna.** Okno RTH specyfikacji to 09:30–16:00, czyli
390 okien 60-sekundowych. Dla 2026-07-03 około **180 z nich nie będzie miało
ani jednej transakcji**, bo rynek jest zamknięty.

**Rozstrzygnięcia, wszystkie bez zmiany progów z §5:**

1. **Zapytanie pozostaje 09:30–16:00**, jak dla każdej innej sesji. Skracanie
   okna dla wybranych dni wprowadziłoby drugą definicję RTH w jednym miesiącu.
   Puste godziny nie kosztują — Databento liczy za rekordy.
2. **Okna po 13:00 są obserwacjami BRAKUJĄCYMI** — dokładnie wg §2.2, bez
   wyjątku dla tej sesji. Zero transakcji to nie `I_count = 0`; to brak danych.
   Wpisanie tam zera przesunęłoby rozkład `I_count` w stronę zera dla ~180
   punktów, czyli **zaniżyłoby** zmierzoną nierównowagę.
3. **Sesja ZOSTAJE w próbie.** Jest legalnym dniem handlowym RTH, a wykluczanie
   sesji dlatego, że wyglądają nietypowo, jest selekcją — i to selekcją
   dokonaną po obejrzeniu danych.
4. **Raport musi podać liczbę okien per sesja.** Bez tej kolumny sesja wnosząca
   210 okien zamiast 390 zniknęłaby w sumie zbiorczej. Ma być widoczna.

**Czego to uzupełnienie NIE zmienia:** żadnego z sześciu progów §5, definicji
jednostki §1, zmiennej głównej §3 ani modelu §4. Rozstrzyga wyłącznie przypadek,
którego specyfikacja nie nazwała po imieniu.

---

## 3. Zmienna główna

```
I_count = (N_buy − N_sell) / (N_buy + N_sell)
```

gdzie `N_buy`, `N_sell` to liczby **kanonicznych agresywnych akcji** (§1)
w oknie, po stronie odpowiednio kupna i sprzedaży.

**Jedna akcja liczy się raz**, niezależnie od: liczby poziomów ceny, liczby
rekordów `Trade`, liczby `Fill` i całkowitego rozmiaru.

Asercja zakresu `[−1, +1]` w miejscu obliczenia — reguła R5.
Rzutowanie na typ ze znakiem przy agregacji — reguła R6.

---

## 4. Benchmark i model identyfikowalności — BEZ ZMIAN

```
m_t = log(P_last / P_first)
```

`P_first`, `P_last` — cena pierwszego i ostatniego wypełnienia w oknie,
w kolejności `(ts_recv, sequence)`.

Model pomocniczy — **nie zawiera przyszłego zwrotu**:

```
I_count ~ m + |m| + m² + sign(m) + log(1 + volume) + efekty pory dnia
```

Identyczny z §7 specyfikacji Etapu 2. **Nie wolno go zmieniać.**

---

## 5. Progi GO/NO-GO — WSZYSTKIE BEZ ZMIAN względem §8 Etapu 2

`D5-B2 GO` **tylko** gdy `I_count` spełnia **wszystkie sześć**:

1. pooled VIF < 5,
2. mediana dziennego VIF < 5,
3. ≥ 75% kompletnych sesji ma VIF < 5,
4. żadna pora dnia nie odpowiada za > 20% zmienności,
5. obie strony agresji obecne — najsłabsza sesja ≥ 20% okien po słabszej stronie,
6. żadna sesja nie odpowiada za > 20% całkowitej zmienności.

**`INCONCLUSIVE`**, jeśli pooled VIF < 5, ale identyfikacja pochodzi głównie
z różnic **między** sesjami albo z pór dnia.

**Zakaz dobierania progów.** Progi pochodzą z dokumentu zamrożonego przed
zakupem próbki `trades` i **nie były dobierane pod żaden wynik**. Nie wolno ich
zmienić po zobaczeniu jednodniowej próbki MBO ani po zobaczeniu wyniku
miesięcznego.

### Kontrole B i C

`B` (nierównowaga po wypełnieniach) i `C` (`I_volume`) pozostają **kontrolami
pomiaru**. **Nie mogą zastąpić A po zobaczeniu wyniku** — to reguła, na której
D5-B zostało zdegradowane i która obowiązuje tu tak samo.

---

## 6. Kompletność sesji

Sesja wchodzi do próby, gdy:

1. plik **parsuje się** bez błędu,
2. liczba rekordów **zgadza się** z `metadata.get_record_count`,
3. SHA-256 zapisany w manifeście,
4. koszt i dokładny zakres UTC zapisane,
5. rekonstrukcja `ohlcv-1m` z MBO zgadza się z posiadanymi barami dostawcy.

**Istnienie pliku nie jest dowodem kompletności.** Ta reguła powstała po tym,
jak przerwany transfer zostawił obciętą sesję, która parsowała się bez błędu.

**Sesja `2026-07-03` jest skrócona** (zamknięcie 13:00 ET — święto obserwowane,
patrz `engine/cme_calendar.py`) i ma odpowiednio mniej okien. Nie jest to
defekt; sesja pozostaje w próbie, oznaczona, i **nie liczy się do wymogu
kompletności** w warunku 3 z §5, tak jak w Etapie 2.

---

## 7. Koszt — zmierzony sesja po sesji

`metadata.get_cost` dla dokładnie tych 22 zapytań, 2026-08-04:

| | |
|---|---|
| Sesji RTH | 22 (2026-07-01 … 2026-07-30) |
| **Koszt łączny** | **78,6044 USD** |
| Rekordów | 837 310 143 |
| Rozmiar rozliczeniowy | 46,89 GB |
| Szacowany rozmiar na dysku | **~14,8 GB** (stosunek 0,316 zmierzony na D5-C) |
| Pozostaje z kredytu 125 USD | 46,40 USD |

Rozrzut: od **0,2498 USD** (2026-07-03, sesja skrócona) do **5,7527 USD**
(2026-07-02).

### Zamrożony limit

```
LIMIT_USD = 82.00
```

Margines 4,3% ponad wycenę — na wahania liczby rekordów, **nie** na zmianę
zakresu. Powyżej limitu zakup **nie zostaje wykonany**, bez skracania okna
i bez rezygnacji z sesji.

---

## 8. Zasoby — zmierzone, nie szacowane

Pomiary z pełnego przebiegu D5-C na jednej sesji (38,3 mln rekordów):

| | Jedna sesja | 22 sesje (ekstrapolacja) |
|---|---|---|
| Czas przetwarzania | **281,9 s** | **~103 min** |
| Szczytowy RSS | **2,106 GB** | **~3,4 GB** (najcięższa sesja 61,3 mln rek.) |
| Zużycie dysku poza plikiem raw | **0 GB** | **0 GB** |
| Artefakt wynikowy | 1,8 kB | ~40 kB |

**Przetwarzanie jest sesja po sesji.** Nigdy nie wczytujemy miesiąca do pamięci.
Szczytowy RSS skaluje się z **największą pojedynczą sesją**, nie z sumą.

Pomiar wykonano po przeniesieniu danych **poza repozytorium** przez
`PROJECT_G_DATA_ROOT`; wyniki były **identyczne co do bajtu**.

---

## 9. Czego ten etap NIE mierzy

Przyszłych zwrotów, trwałości znaku, korelacji z przyszłym P&L, skuteczności
kierunku, Sharpe'a, profit factora, optymalnego progu nierównowagi, najlepszego
segmentu dnia, najlepszego horyzontu utrzymania, strategii long/short.

**Licznik prób pozostaje 0.**

---

## 10. Status statystyczny

**Cały lipiec 2026 jest development setem.** Nie jest OOS i nie stanie się OOS
po zamrożeniu H017. Sesja `2026-07-30` była dodatkowo oglądana w Etapach 1 i 3.

| Wynik | Co dalej |
|---|---|
| `D5-B2 GO` | dopiero wtedy powstaje **H017**; mechanizm, znak, okno i wykonanie zamrożone; następnie pre-flight trwałości znaku; dopiero potem pierwszy backtest i **próba nr 1** |
| `INCONCLUSIVE` | H017 nie powstaje; najpierw wyjaśniamy pomiar |
| `NO-GO` | D5 zamknięte **bez** zmiany zmiennej głównej na nierównowagę wypełnień ani wolumenu |

**H017 nie powstaje na tym etapie. P&L nie jest mierzony.**

---

## 11. Reprodukcja

Wymagane artefakty: manifest z SHA-256 każdej sesji, parametry zapytań,
rzeczywista liczba rekordów, rozmiar, koszt, dokładne granice UTC, wersja
biblioteki, kontrola braku duplikatów na granicach sesji.

**Pliki `.dbn.zst` nie trafiają do repozytorium.** Commitujemy manifest,
parametry, SHA-256, raport i kod rekonstrukcji.

---

## 12. Uzupełnienie *ex ante* — operacjonalizacja bramki (06.10.2026)

**Zapisane PO pobraniu miesiąca i PRZED jakąkolwiek analizą.** Do chwili tego
zapisu nikt — ani Wykonawca, ani właściciel — nie widział żadnej wielkości,
z której liczy się bramka: ani `I_count`, ani VIF, ani rozkładu stron. Jedyne
liczby znane z pobrania to liczby rekordów i koszty sesji.

Powód zapisu jest ten sam co w §2.3: spec nazywa sześć progów, ale kilka
decyzji wykonawczych zostawia otwartych. Rozstrzygnięte po zobaczeniu wyniku
byłyby wyborem, nie regułą. **Żaden próg z §5 się nie zmienia.** Implementacja:
`engine/d5b2.py` (logika), `scripts/d5b2_bramka.py` (I/O); każda reguła poniżej
ma test w `tests/test_d5b2.py` lub `tests/test_d5b2_bramka.py`.

Od 03.10 projekt nie ma recenzenta (decyzja właściciela), więc tę rolę pełni
ten zapis i testy: mapowanie werdyktu jest tabelą testową, progi są
porównywane z tekstem §5 przez test, a kluczowe reguły (kolejność cen,
przypisanie okna, brakujące okna, strona N, reguła INCONCLUSIVE) zostały
sprawdzone celowym zepsuciem kodu — każde zepsucie dało czerwony test.

### 12.1 Źródła wielkości w oknie

| Wielkość | Z czego | Uzasadnienie |
|---|---|---|
| `N_buy`, `N_sell` (A) | kanoniczne akcje §1, okno wg `ts_recv` ostatniego rekordu | §1.5, §2.1 |
| `P_first`, `P_last`, `volume` | wszystkie rekordy `T` w oknie, **także strona N** | odpowiednik wierszy schematu `trades` z Etapu 2 |
| kolejność cen | jawnie `(ts_recv, sequence)`; remis rozstrzyga kolejność pliku | §4 — liczona, nie zakładana z pliku |
| kontrola B | liczba rekordów `T` po stronie B / A | Etap 2: „surowe wypełnienia" |
| kontrola C | wolumen rekordów `T` po stronie B / A | Etap 2: `I_volume` |
| strona N akcji | raportowana osobno, **wykluczona** ze znaku | Etap 2 §4 |

Obserwacją jest okno, które ma jednocześnie cenę, stronę dla B/C i stronę dla
A (`inner join` z implementacji Etapu 2). Każde inne okno jest **brakujące**
(§2.2), nie zerowe.

### 12.2 Mapowanie werdyktu

| Układ | Werdykt | Źródło |
|---|---|---|
| wszystkie sześć warunków + A/B/C zgodne co do pooled VIF | **GO** | §5 |
| wszystkie sześć, ale A/B/C niezgodne | **INCONCLUSIVE** | Etap 2 §4a: „A daje GO, B/C nie" |
| warunek 1 spełniony, a **wszystkie** niespełnione należą do {2, 3, 4, 6} | **INCONCLUSIVE** | §5: „identyfikacja pochodzi głównie z różnic między sesjami (2, 3, 6) albo z pór dnia (4)" |
| każdy inny układ, w tym niespełniony warunek 1 albo 5 | **NO-GO** | §5 |

Warunek 5 (obie strony agresji) nie jest pytaniem o **źródło** identyfikacji,
tylko o to, czy pomiar w ogóle widzi obie strony — dlatego jego niespełnienie
daje NO-GO, nie INCONCLUSIVE.

**INCONCLUSIVE nie uprawnia do żadnego zakupu danych.** Wyjaśnienie pomiaru
odbywa się wyłącznie na posiadanym miesiącu. Reguła właściciela z 03.10:
NO-GO albo porażka H017 kończy kupowanie danych w D5.

### 12.3 Kompletność sesji (§6) dla miesiąca niejednorodnego

| Punkt §6 | Implementacja |
|---|---|
| 1. parsuje się | wyjątek przy odczycie = STOP |
| 2. liczba rekordów | liczba **wszystkich** rekordów pliku = `rekordow` z wpisu `wyniki[]` z `kompletny: true` (dla 07-30 rezerwowo manifest D5-C) |
| 3. SHA-256 | gdy manifest go ma — musi się zgadzać; **cztery stare sesje (07-01, 07-02, 07-03, 07-06) go nie mają** (wpisy z syntezy, `D5_DRYF` §5f), więc SHA jest liczony przy analizie i zapisany w raporcie jako `zapisany_teraz` |
| 4. koszt i zakres UTC | wpis planu manifestu; zakres musi być równy RTH wyprowadzonemu ze strefy |
| 5. rekonstrukcja `ohlcv-1m` | bary z rekordów `T` po `ts_recv` = bary dostawcy z `data/clean` (MNQU6, ceny surowe), **zgodność dokładna** co do open/high/low/close/volume i zbioru minut |

Uzasadnienie punktu 3: SHA z dnia analizy nie poświadcza pliku z dnia
pobrania — i nie udajemy, że tak jest. Te pliki mają za to liczbę rekordów
równą co do rekordu liczbie opłaconej (sprawdzone przez bieg zakupowy, który
je rozpoznał i pominął) oraz kopię zapasową z 11.08.

**Niespełnienie któregokolwiek punktu = STOP bez werdyktu**, a nie wykluczenie
sesji. Wykluczanie sesji po zobaczeniu, że „coś z nią nie tak", byłoby
selekcją. STOP nic nie kosztuje: dane są na dysku, bramka nie zostaje zużyta.
STOP dają też: suma `n_trade` różna od liczby rekordów `T` (N1), akcja poza
RTH, rekord `T` bez ceny, więcej niż jeden instrument w pliku, niedeterministyczny
wynik powtórnego przeliczenia sesji 07-03.

Tylko raportowane: rozjazd pasywnych `Fill` z rozmiarem akcji (N4, osobno na
brzegach RTH), rekordy spoza RTH, cofnięcia `ts_recv` w pliku, akcje strony N.

### 12.4 Miesiąc z dwóch normalizacji

Pięć sesji jest w starej normalizacji, siedemnaście w nowej (`KOSZTY` §3).
Bramka liczy się na **całym miesiącu**, przez rekonstrukcję jednostki §1 —
jednostka jest po obu stronach identyczna na dwóch zmierzonych oknach
(`D5_DRYF` §3d, §5e). Surowe liczniki rekordów **nigdy** nie są mieszane.

Zgoda właściciela: 06.10, odpowiedź „zrobione wszystko" na pytanie o to
mieszanie — **zinterpretowana jako „tak"** i zapisana tu jako interpretacja,
nie jako cytat jednoznacznej zgody.

Raport podaje dodatkowo pooled VIF dla A osobno dla sesji starej i nowej
normalizacji. **Ta liczba jest opisowa i NIE wchodzi do werdyktu.**

### 12.5 Operacjonalizacje odziedziczone z Etapu 2

Przeniesione 1:1 z jedynej dotychczasowej implementacji
(`scripts/audit_d5_etap2.py`), bez zmiany:

- efekty pory dnia: kubełki 30-minutowe, 13 w sesji pełnej, jeden jako baza;
  liczone od otwarcia RTH (w lipcu identyczne z podziałem tamtej
  implementacji po zegarze UTC — cały miesiąc w EDT),
- dzienny VIF tylko dla sesji kompletnych z **≥ 50 oknami**; mianownik
  warunku 3 to liczba takich sesji,
- „udział w zmienności" = udział sesji / kubełka w sumie kwadratów odchyleń
  `I_count` od średniej **globalnej**,
- warunek 5 liczony na **najsłabszej** sesji (z sesją skróconą włącznie),
- VIF = 1/(1 − R²) regresji z wyrazem wolnym; VIF nieokreślony (stałe `I`)
  **nie** jest poniżej progu.

### 12.6 Kolejność uruchomienia

1. `python scripts/d5b2_bramka.py --sesja 2026-07-03` — próba generalna: jedna
   sesja, wszystkie kontrole i test determinizmu, **bez werdyktu**,
2. dopiero po zielonej próbie pełny bieg, jednorazowo.

**Licznik prób pozostaje 0** niezależnie od wyniku — bramka nie mierzy
przyszłych zwrotów ani P&L.
