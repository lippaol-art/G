# Dryf metadanych GLBX.MDP3 — zakup miesiąca WSTRZYMANY

**Wykryte: 08.08.2026. Status: OTWARTE. Zakup zablokowany warunkiem 8.**

> ## ⚠️ KOREKTA v2 — pierwsza wersja tego dokumentu stawiała błędną tezę
>
> Wersja z commita `e9a2b6c` twierdziła, że **Databento zrewidowało dane**.
> **Ich własne metadane temu przeczą** i dobrze, że mail nie został wysłany.
>
> `metadata.get_dataset_condition("GLBX.MDP3", "2026-07-01", "2026-07-31")`
> zwraca dla **każdej** sesji lipca `last_modified_date` równy D+1 — najpóźniejsza
> wartość w całym miesiącu to `2026-08-01`. **Nic nie było modyfikowane
> 6–8 sierpnia.** Nasze sesje: 07-01 → `2026-07-02`, …, 07-29 i 07-30 →
> `2026-07-31`.
>
> Wnioski liczbowe (tabela §1, proporcjonalność, stała cena za rekord) **stoją
> bez zmian**. Upadła wyłącznie ich interpretacja. Nowa teza i nowe pytanie: §2a.

**Poprawka dat wniesiona przez recenzję P1:** wcześniejsza wersja mówiła
o „05.08 vs 06.08". Faktyczne okno to **przebieg, który pobrał 2026-07-06
(serwer zwracał wtedy jeszcze stare liczby) → 2026-08-08T12:15Z**. Dokładny
lewy kraniec: pole `pobrano_utc` w lokalnym `manifest_d5b2.json`.

---

## 1. Objaw

Dwa uruchomienia wyceny tego samego, zamrożonego zapytania — ten sam zbiór,
ten sam instrument, ten sam schemat, **te same granice UTC** (potwierdzone
przez warunek 3: `manifest: zgodny (22 sesji)`) — dały **różne liczby
rekordów dla wszystkich 22 sesji**.

Kolumna „wycena nr 1" pochodzi z przebiegu, który pobrał sesje 07-01…07-06;
kolumna „nr 2" z przebiegu 08.08.2026 ok. 12:15 UTC.

| Sesja | Wycena nr 1 | Wycena nr 2 | Różnica | % |
|---|---:|---:|---:|---:|
| 2026-07-01 | 39 297 265 | 40 286 094 | +988 829 | +2,52% |
| 2026-07-02 | 61 279 315 | 62 968 438 | +1 689 123 | +2,76% |
| 2026-07-03 | 2 660 629 | 2 708 424 | +47 795 | +1,80% |
| 2026-07-06 | 32 369 900 | 32 910 056 | +540 156 | +1,67% |
| 2026-07-07 | 47 432 653 | 48 848 835 | +1 416 182 | +2,99% |
| 2026-07-08 | 44 684 887 | 46 050 560 | +1 365 673 | +3,06% |
| 2026-07-09 | 31 224 457 | 32 063 628 | +839 171 | +2,69% |
| 2026-07-10 | 31 691 336 | 32 533 406 | +842 070 | +2,66% |
| 2026-07-13 | 37 014 382 | 37 927 155 | +912 773 | +2,47% |
| 2026-07-14 | 36 187 628 | 37 012 042 | +824 414 | +2,28% |
| 2026-07-15 | 43 923 779 | 45 030 234 | +1 106 455 | +2,52% |
| 2026-07-16 | 40 315 486 | 41 290 788 | +975 302 | +2,42% |
| 2026-07-17 | 46 891 856 | 48 184 396 | +1 292 540 | +2,76% |
| 2026-07-20 | 37 279 369 | 38 272 577 | +993 208 | +2,66% |
| 2026-07-21 | 25 434 428 | 26 005 248 | +570 820 | +2,24% |
| 2026-07-22 | 25 180 783 | 25 734 547 | +553 764 | +2,20% |
| 2026-07-23 | 43 666 511 | 44 844 144 | +1 177 633 | +2,70% |
| 2026-07-24 | 41 935 351 | 43 003 047 | +1 067 696 | +2,55% |
| 2026-07-27 | 46 240 083 | 47 481 981 | +1 241 898 | +2,69% |
| 2026-07-28 | 35 721 633 | 36 695 855 | +974 222 | +2,73% |
| 2026-07-29 | 48 571 535 | 50 054 691 | +1 483 156 | +3,05% |
| **2026-07-30** | **38 306 877** | **39 437 696** | **+1 130 819** | **+2,95%** |

**Razem: 837 310 143 → 859 343 842 rekordów (+2,63%).
Koszt: 78,6044 → 80,6729 USD (+2,0685).**

**22 z 22 sesji w górę. Ani jedna w dół.** Zakres +1,67% do +3,06%,
mediana +2,66%.

---

## 2. Co to NIE jest — hipotezy odrzucone rachunkiem

### Nie zmiana zapytania

Warunek 3 skryptu porównuje `dataset`, `symbols`, `stype_in`, `schema` oraz
`start_utc`/`end_utc` **każdej z 22 sesji** z manifestem poprzedniego
uruchomienia. Wypisał `manifest: zgodny (22 sesji)`. Zapytanie jest identyczne.

### Nie syntetyczne snapshoty księgi

Databento ostrzega, że zapytanie niezaczynające się o północy UTC zawiera
syntetyczny snapshot pełnego stanu księgi. Gdyby przyrost pochodził stąd,
byłby **stały na kawałek** — a wtedy sesja mała miałaby procentowo wielokrotnie
większy przyrost niż duża.

| Sesja | Rozmiar | Przyrost | % | Przyrost / kawałek |
|---|---:|---:|---:|---:|
| 2026-07-03 | 2 660 629 | +47 795 | +1,80% | 5 974 |
| 2026-07-21 | 25 434 428 | +570 820 | +2,24% | 43 909 |
| 2026-07-02 | 61 279 315 | +1 689 123 | +2,76% | 129 932 |

2026-07-02 jest **23× większa** od 2026-07-03. Przy stałym przyroście na
kawałek mniejsza sesja miałaby ~23× wyższy procent. Ma +1,80% wobec +2,76% —
ten sam rząd. Przyrost na kawałek różni się 28×, więc stały nie jest.

**Przyrost jest PROPORCJONALNY do rozmiaru sesji.** To wyklucza snapshoty
jako źródło.

**Zweryfikowane dodatkowo pomiarem, nie tylko rachunkiem** (08.08, darmowe):
okno 13:30–14:30 sesji 2026-07-03 zapytane jednym wywołaniem daje
**1 389 818** rekordów; podzielone na 13:30–14:00 i 14:00–14:30 daje
840 392 + 549 426 = **1 389 818**. **Różnica dokładnie 0.** Dzielenie na
kawałki jest ściśle addytywne i niczego nie dokłada.

### Nie błąd naszego sumowania

`metadane_dzielone` sumuje 13 kawałków po 30 min. Poprawność sumowania była
zweryfikowana empirycznie: 13 kawałków dało **38 306 877** rekordów
i **3,5961 USD**, zgodnie z wartością dla całego zakresu co do rekordu
i czwartego miejsca po przecinku. Potwierdzone ponownie 08.08 testem wyżej
(różnica 0). Kod sumujący nie zmienił się w sposób dotykający arytmetyki.

### Nie chwilowy odczyt — nowa wartość jest STABILNA

Trzy pomiary pod rząd, 08.08, sesja 2026-07-03, pełne okno RTH:
**2 708 424 / 2 708 424 / 2 708 424**. Nowa liczba nie „drga"; stara wartość
2 660 629 nie wraca.

### ✗ NIE rewizja danych u dostawcy — teza ODRZUCONA jego własnymi metadanymi

`metadata.get_dataset_condition("GLBX.MDP3", "2026-07-01", "2026-07-31")`,
08.08.2026, 31 pozycji:

| Sesja | `condition` | `last_modified_date` |
|---|---|---|
| 2026-07-01 | available | 2026-07-02 |
| 2026-07-02 | available | 2026-07-03 |
| 2026-07-03 | available | 2026-07-04 |
| … | … | D+1 |
| 2026-07-29 | available | 2026-07-31 |
| 2026-07-30 | available | 2026-07-31 |
| 2026-07-31 | available | 2026-08-01 |

**Najpóźniejsza modyfikacja w całym lipcu to 2026-08-01.** Żadna z naszych
22 sesji nie była dotykana 6–8 sierpnia. Jeżeli `last_modified_date` znaczy to,
co sugeruje nazwa, **dane się nie zmieniły — zmieniło się to, co o nich mówi
`get_record_count`.**

---

## 2a. Rama faktograficzna — świadomie BEZ mechanizmu

**Korekta v3, po recenzji P1.** Wersja v2 stawiała tezę „wcześniejsze wyceny
zaniżone, bo powstały w czasie awarii 503/504". **Oś czasu ją obala** i teza
zostaje wycofana. Podaję fakty; nazwanie mechanizmu należy do dostawcy.

### Stara wartość NIE powstała w czasie awarii

| Kiedy | Gdzie | Dowód w repo |
|---|---|---|
| **2026-08-04 13:31Z** | środowisko zdalne, **2 dni przed** obserwowaną awarią | commit `299ca34`, `data/wycena_d5b2_mbo.json`, pole `koszt_usd`: **78,6044 USD / 837 310 143 rek.** (78,6045 to suma 22 zaokrąglonych pozycji); per sesja 07-01 3,6891 / 39 297 265, 07-03 0,2498 / 2 660 629, 07-30 3,5961 / 38 306 877 |
| 2026-08-04 | pobranie D5-C — `get_range`, **nie** metadane | plik fizycznie ma **38 306 877** rekordów, SHA `3e6f023d…74ac42` |
| ~2026-08-05 | ponowne pobranie D5-C, maszyna lokalna | **ten sam SHA**, znowu 38 306 877 |
| wieczór 06–07.08 | przebiegi zakupowe, lokalnie | stare liczby; pobrane pliki zgodne co do rekordu |
| **2026-08-08 ~12:15Z** | przebieg wyceny | **skok we wszystkich 22 sesjach** |

**Stara wartość była stabilna przez ≥4 dni, na dwóch maszynach, i obejmowała
nie tylko metadane, ale też ZAWARTOŚĆ dostarczonych plików.** Awaria 503/504
z 06.08 jest wobec tego **datowaną koincydencją**, nie przyczyną — hipoteza
wtórna, którą zostawiam do rozstrzygnięcia dostawcy.

### Co wiemy na pewno

1. zapytanie identyczne (warunek 3, 22/22 sesji),
2. dzielenie na kawałki ściśle addytywne — 13:30–14:30 jednym wywołaniem
   1 389 818, dwoma po 30 min 840 392 + 549 426 = **1 389 818, różnica 0**,
3. nowa wartość stabilna: trzy pomiary 07-03 → 2 708 424,
4. cena za rekord identyczna przed i po (~9,388·10⁻⁸ USD/rek) — zmieniły się
   liczby rekordów, nie cennik,
5. `get_dataset_condition` nie raportuje **żadnej** modyfikacji w sierpniu
   (`last_modified_date` = D+1, najpóźniej `2026-08-01`),
6. stara wartość poprzedza awarię o dwa dni i występuje też w plikach.

Z (1)–(6): **jedna z dwóch wartości `get_record_count` jest błędna**, przejście
między nimi jest **skokowe** i nastąpiło między wieczorem 06–07.08 a 08.08
12:15Z. **Nie mam mechanizmu i nie będę go zgadywał** — pytanie do dostawcy
jest sformułowane neutralnie.

### Trzy światy, nie dwa

| | Co znaczy | Co robimy |
|---|---|---|
| **A. pliki niepełne** | pobrania z okresu starej wartości są krótsze, niż powinny | pobrać ponownie, zapłacić drugi raz |
| **B. pliki pełne, metadane błędne dziś** | nic nie kupujemy, czekamy na sprostowanie | nie kupujemy nic |
| **B′. pliki pełne wg STAREJ wersji serwowania** | nowe pobranie tego samego zakresu da **inną treść** | nie kupujemy — ale **„PEŁNY" ≠ „mieszalny z nowymi zakupami"** |

**Wariant B′ dodany przez recenzję P1** i jest najważniejszy operacyjnie:
oznacza, że nawet komplet plików „pełnych" **nie wolno mieszać** z sesjami
pobranymi po skoku. Zakaz mieszania obowiązuje **niezależnie** od wyniku
diagnostyki.

## 3. Wynik diagnostyki lokalnej (08.08, `scripts/diag_dryf.py`)

### Test 1 — zakres czasowy

```
sesja             rekordow   pierwszy UTC   ostatni UTC   ocena
2026-07-01      39,297,265       13:30:00      19:59:59   PELNY
2026-07-02      61,279,315       13:30:00      19:59:59   PELNY
2026-07-03       2,660,629       13:30:00      17:00:00   PELNY   (zamkniecie 13:00 ET)
2026-07-06      32,369,900       13:30:00      19:59:59   PELNY
2026-07-07       1,867,793       13:30:00      13:37:57   OBCIETY o 382 min
2026-07-30      38,306,877       13:30:00      19:59:59   PELNY
```

**Pięć plików bez uciętego ogona; 07-07 to znany wrak** (przerwany transfer,
7 minut z 6,5 godziny czasu — **3,94% rekordów**, ~2% czasu). Wzorzec dokładnie taki, jaki przewidziała
recenzja.

**Czego ten wynik NIE dowodzi.** Plik, któremu brakuje 2,6% rekordów
rozsianych równomiernie, też zaczyna się o 13:30 i kończy o 19:59:59.
**„PEŁNY" wyklucza obcięcie, nie przerzedzenie** — i dlatego doszedł test 2.

### Test 2 — gęstość w oknie 13:30–14:30 · **WYKONANY 08.08**

```
serwer 08.08, to samo okno   :  1,389,818
nasz plik 2026-07-03         :  1,362,037
NIEDOBOR w oknie             :     27,781   (1,9989%)
NIEDOBOR w calej sesji       :     47,795   (1,7647%)
stosunek stop okno/sesja     :      1,133
```

**To jest wynik rozstrzygający dla jednego pytania i otwierający drugie.**

#### Co zostało rozstrzygnięte

**Ocena `PELNY` z testu 1 jest obalona empirycznie.** W oknie 13:30–14:30
pokrycie czasowe naszego pliku jest **pełne z obu stron** — a mimo to brakuje
w nim **27 781 rekordów** wobec tego, co API zwraca dziś dla identycznego
zakresu. Niedobór **nie jest uciętym ogonem**; siedzi w środku sesji.

Konsekwencja praktyczna: **żaden z pięciu plików ocenionych jako `PELNY` nie
jest dowodem kompletności.** Test zakresu wyklucza obcięcie i tylko tyle.

#### Co się otworzyło

Niedobór **nie jest jednorodny**. Gdyby był, tempo w oknie i w całej sesji
byłoby równe; stosunek wynosi **1,133**, czyli w pierwszej godzinie brakuje
o ~13% *względnie* więcej niż średnio.

**Kontrast wyostrzony rachunkiem recenzji P1** — porównanie okna z **resztą
sesji**, nie ze średnią:

| | rekordów u nas | niedobór | stopa |
|---|---:|---:|---:|
| okno 13:30–14:30 | 1 362 037 | 27 781 | **1,999%** |
| reszta sesji | 1 298 592 | 20 014 | **1,518%** |

Okno ma stopę **1,32×** wyższą niż reszta. Pierwsza godzina niesie **58,1%**
całego niedoboru, mając **51,3%** rekordów. Nadwyżka serwera jest więc
**skoncentrowana na otwarciu**. Udział pierwszej godziny w sesji:
**51,192%** u nas wobec **51,315%** u dostawcy.

To wyklucza najprostsze wyjaśnienie „stała frakcja rekordów zgubiona
równomiernie" i wskazuje na coś **strukturalnego** — ale czego, tego z samych
liczebności nie da się orzec.

#### Czego test 2 nadal NIE rozstrzyga

Czy brakujące 27 781 rekordów to:

| | |
|---|---|
| **wariant A** | realne zdarzenia rynkowe, których w naszym pliku nie ma |
| **wariant B′** | te same zdarzenia w innej reprezentacji (np. inaczej rozbite komunikaty) |

**Na to odpowiada wyłącznie porównanie TREŚCI**, nie liczebności. Procedura
i koszt: §5a. Do czasu rozstrzygnięcia obowiązuje zakaz mieszania plików
z obu okresów — **niezależnie od tego, który wariant okaże się prawdziwy**.

---

## 3a. Bilans diagnostyki — co wiemy po obu testach

| Pytanie | Odpowiedź | Na jakiej podstawie |
|---|---|---|
| Czy pliki są ucięte na końcu? | **Nie** (poza 07-07) | test 1, pokrycie 13:30–19:59:59 |
| Czy pliki mają tyle rekordów, co dziś API? | **Nie, mniej o ~2%** | test 2, okno o pełnym pokryciu |
| Czy niedobór jest jednorodny? | **Nie**, stosunek 1,133 | test 2 |
| Czy brakuje realnych zdarzeń? | **NIEROZSTRZYGNIĘTE** | wymaga porównania treści (§5a) |
| Czy wolno mieszać stare i nowe pliki? | **Nie** | niezależnie od powyższego |

---

## 4. Dlaczego to jest poważne, a nie kosmetyczne

### 4.1 Ryzyko finansowe — realne i zmierzone

`kompletny()` porównuje plik na dysku z liczbą rekordów z **bieżącej** wyceny.
Po rewizji **każdy już opłacony plik wygląda na niekompletny**:

```
UWAGA 2026-07-01: plik istnieje, ale rekordow 39,297,265 != oczekiwanych 40,286,094
UWAGA 2026-07-02: plik istnieje, ale rekordow 61,279,315 != oczekiwanych 62,968,438
UWAGA 2026-07-03: plik istnieje, ale rekordow  2,660,629 != oczekiwanych  2,708,424
...
kompletnych juz na dysku : 0
do pobrania              : 22
koszt do zaplaty teraz   : 80.6729 USD
```

Skrypt zaproponował **zakup całego miesiąca po raz drugi**, mimo że cztery
sesje były już opłacone. Zatrzymał go warunek 4 — i to wyłącznie dlatego, że
2026-07-30 ma osobną, twardą ochronę. Pozostałe 21 sesji przeszłoby.

**To była wada projektowa, nie wada danych.** Naprawiona: warunek 8 porównuje
bieżące metadane z manifestem i przerywa przy rozjeździe.

### 4.2 Ryzyko naukowe — poważniejsze niż finansowe

**Audyt D5-C policzono na pliku, którego liczba rekordów nie zgadza się już
z tym, co podaje API.**

Wynik `842 757 zdarzeń, 0 niewyjaśnionych` powstał na pliku o SHA-256
`3e6f023d...74ac42` i **38 306 877** rekordach. Dziś to samo zapytanie wycenia
**39 437 696**. Dopóki nie wiemy, która liczba jest prawdziwa, nie wiemy też,
czy audyt policzono na komplecie danych.

Konsekwencje do rozstrzygnięcia — **kolejność ma znaczenie**:

1. **Najpierw**: czy plik D5-C obejmuje całe okno RTH (`scripts/diag_dryf.py`).
   Jeśli tak, audyt liczono na sesji ciągłej od 13:30 do 20:00 UTC i brak
   ~1,1 mln rekordów musiałby oznaczać braki rozsiane, nie ucięty ogon.
2. Czy miesiąc D5-B2 wolno policzyć na **mieszance** plików z obu okresów?
   **Nie** — dopóki nie wiadomo, czy różnią się zawartością, a nie tylko
   metadanymi. W danych nie widać, który plik z którego okresu pochodzi.
3. Czy trzeba pobrać ponownie i kto pokrywa koszt — **pytanie do dostawcy**,
   nie do nas, jeśli przyczyną była awaria po ich stronie.

Powiązanie z ryzykiem A4-11 z audytu 4 (*„zmiana normalizacji GLBX.MDP3,
VII 2026"*) **wycofuję** — `last_modified_date` mu przeczy. To nie jest ten
scenariusz; to problem z warstwą metadanych, nie z normalizacją danych.

---

## 5. Pytanie do Databento

**Wysłać dopiero po teście 2** — jego wynik zmienia punkt 4. Wątek: kontynuacja
rozmowy z Erikiem.

> **Subject: `metadata.get_record_count` for GLBX.MDP3 MBO jumped ~2.6% for all
> July 2026 sessions, while `get_dataset_condition` reports no modification**
>
> Hi Erik,
>
> Following up on our earlier thread. We have a reproducibility question we
> could not resolve ourselves, and we have paused a purchase because of it.
>
> **Setup.** Fixed research query: `GLBX.MDP3`, schema `mbo`, symbol `MNQU6`,
> `stype_in=raw_symbol`, 22 RTH sessions of July 2026, each `13:30–20:00 UTC`
> (09:30–16:00 America/New_York).
>
> **Dated history of our measurements** — the same query, four times:
>
> | When (UTC) | Where | Result |
> |---|---|---|
> | 2026-08-04 13:31 | our cloud environment | 837,310,143 records / 78.6044 USD |
> | 2026-08-04 | `timeseries.get_range` for 2026-07-30 | file contains **38,306,877** records |
> | ~2026-08-05 | re-download of the same session, different machine | identical SHA-256, again 38,306,877 |
> | 2026-08-06–07 evening | purchase runs | same counts; downloaded files match them record-for-record |
> | **2026-08-08 12:15** | pricing run | **859,343,842 records / 80.6729 USD** |
>
> Every one of the 22 sessions increased, by +1.67% to +3.06% (median +2.66%).
> Implied price per record is unchanged (~9.388e-8 USD/record), so this is
> purely a change in reported record counts.
>
> **What we ruled out ourselves:**
>
> * *Different query.* Identical dataset, symbol, stype, schema and UTC bounds —
>   compared against a stored manifest, matched on all 22 sessions.
> * *Our 30-minute chunking.* Verified additive: `13:30–14:30` as one call
>   returns 1,389,818; as `13:30–14:00` + `14:00–14:30` it returns
>   840,392 + 549,426 = 1,389,818. **Difference exactly 0.**
> * *A transient read.* Three consecutive calls for 2026-07-03 all return
>   2,708,424.
> * *Synthetic book snapshots.* The increase is proportional to session size,
>   whereas a per-request snapshot would add a roughly constant number of
>   records and therefore affect a small session far more in percentage terms.
>   We observe the opposite.
>
> **What puzzles us most.** `metadata.get_dataset_condition("GLBX.MDP3",
> "2026-07-01", "2026-07-31")` reports, for every July date, `condition:
> available` and a `last_modified_date` of D+1 — the latest value anywhere in
> the month is `2026-08-01`. So by your own metadata nothing in July was
> modified in August, yet the reported counts changed. Note also that the older
> counts were not confined to metadata: files we downloaded on Aug 4 and Aug 5
> physically contain the older record counts.
>
> **Our questions:**
>
> 1. Which of the two counts is authoritative for these ranges, and **what
>    changed on your side between the evening of Aug 7 and Aug 8, 12:15 UTC**?
> 2. Does `last_modified_date` in `get_dataset_condition` cover changes that
>    would affect `get_record_count`? If not, which field should we watch for
>    reproducibility?
> 3. **Is there a way to pin a dataset version**, so that a result computed today
>    can be reproduced later? We record SHA-256 of every downloaded file, but we
>    need to know whether re-requesting an identical historical range is expected
>    to be deterministic over time.
> 4. We hold **five** of these sessions downloaded before the change
>    (2026-07-01, 07-02, 07-03, 07-06 and 07-30). Each covers its full requested
>    window — first record at 13:30:00 UTC, last at 19:59:59 UTC, except
>    2026-07-03 which ends at 17:00:00 UTC because of the early close — yet each
>    contains the older, lower record count. We checked one narrow window
>    directly: for **2026-07-03, 13:30–14:30 UTC**, your API reports
>    **1,389,818** records today, while our file — whose time coverage spans
>    that window completely — contains **1,362,037**, i.e. **27,781 fewer
>    (−2.00%)**. The shortfall is therefore inside the session, not a truncated
>    tail, and it is not uniform (the first hour is short by 2.00% against 1.76%
>    for the session as a whole).
>
>    **Are those files missing real market events, or is this a difference in
>    how the same events are represented?** We need to know before mixing files
>    downloaded before and after the change into one dataset.
> 5. Two sessions were interrupted mid-download — 2026-07-06 returned
>    `Response ended prematurely`, and 2026-07-07 left a truncated file
>    (1,867,793 records, ~7 minutes of a 6.5-hour window). **Were those
>    interrupted requests billed?**
>
> For context: this is a single-instrument research project on a small budget,
> and reproducibility is a hard requirement — a result we cannot recompute later
> is not a result we can use. We stopped after 4 of 22 sessions specifically
> because mixing data from two periods would be invisible in the data itself.
>
> Thanks,

---

## 5a. Mikro-diff — jedyna droga do rozstrzygnięcia A vs B′

**Wymaga jawnej zgody właściciela (reguła R1). Nie uruchomione.**

Test 2 pokazał, że brakuje 27 781 rekordów w oknie o pełnym pokryciu
czasowym. Liczebności powiedziały już wszystko, co mogły — **naturę nadwyżki
rozstrzyga wyłącznie porównanie treści.**

| | |
|---|---|
| Zakres | `2026-07-03`, **13:30–14:00 UTC** (pierwsze 30 min) |
| Koszt | ~840 392 rek. × 9,388·10⁻⁸ ≈ **0,079 USD** · `get_cost` **przed** pobraniem |
| Cel zapisu | **osobny katalog diagnostyczny**, nie `d5b2_mbo/`, bez dotykania manifestów |
| Dlaczego ten start | identyczny z początkiem naszego pliku, więc syntetyczny snapshot księgi wypada w tym samym miejscu i **skraca się w porównaniu** |
| Metoda | diff rekord po rekordzie z odpowiadającym wycinkiem naszego pliku |

**Odczyt wyniku:**

- realne zdarzenia obecne u dostawcy, nieobecne u nas → **wariant A**
  (pliki niepełne, trzeba odkupić),
- te same zdarzenia, inny podział/typy rekordów → **wariant B′**
  (pliki pełne, ale niemieszalne).

**Wpis do `data/KOSZTY.md` niezależnie od wyniku.** Alternatywa: poczekać na
odpowiedź Databento i nie wydawać nic — decyzja właściciela.

---

## 6. Co robimy do czasu odpowiedzi

| | |
|---|---|
| **Zakup miesiąca** | **WSTRZYMANY.** Warunek 8 blokuje automatycznie. |
| **Diagnostyka lokalna** | `python scripts/diag_dryf.py` — **uruchom przed mailem** |
| **Furtka na później** | `--akceptuj-rozjazd` archiwizuje stary manifest; **nie używać przed odpowiedzią** |
| Pliki już pobrane | **NIE kasujemy.** Zgadzają się z liczbami, za które zapłacono. |
| `2026-07-30` z D5-C | **NIE ruszamy.** SHA zamrożony, kopia zapasowa priorytetowa. |
| Analiza miesiąca | zablokowana — nie ma kompletu jednej wersji |
| Licznik prób | 0, bez zmian |

**Nie kupujemy pozostałych 18 sesji, dopóki nie wiadomo, czy za tydzień nie
będą znowu inne.** Wydanie 65 USD na dane, których definicja dryfuje, byłoby
kupowaniem czegoś, czego nie da się odtworzyć — a odtwarzalność jest w tym
projekcie warunkiem, nie ozdobą.

---

## 7. Co ta sytuacja zmienia trwale

1. **Liczba rekordów z metadanych nie jest niezmiennikiem.** Wszędzie, gdzie
   traktowaliśmy ją jako stałą cechę sesji, trzeba porównywać z **manifestem**,
   nie z bieżącym API. Warunek 8 to egzekwuje.
2. **SHA-256 pliku jest jedynym twardym identyfikatorem**, jaki mamy.
   Kopia zapasowa surowych plików (URUCHOMIENIE_LOKALNE §8.1) przestaje być
   ostrożnością, a staje się jedynym sposobem zachowania wersji, na której
   policzono wynik.
3. **Każdy wynik na danych MBO musi podawać SHA plików wejściowych.**
   Bez tego „powtórzyliśmy i wyszło inaczej" jest nierozstrzygalne.
