# Dryf metadanych GLBX.MDP3 — zakup miesiąca WSTRZYMANY

**Wykryte 08.08.2026. Skutek dla danych rozstrzygnięty pomiarem 09.08.
Mechanizm NAZWANY PRZEZ DOSTAWCĘ 10.08. Zakup nadal zablokowany warunkiem 8.**

> ## 📣 ODPOWIEDŹ DATABENTO — 10.08, mechanizm znany (§5b)
>
> > *„We released a change for GLBX.MDP3 over the weekend, which leads to
> > additional MBO records being published for some events."* — Renan, Databento
>
> **To celowa zmiana normalizacji, nie awaria i nie utrata danych.** Zgadza się
> z każdym naszym pomiarem: okno czasowe (weekend 08–09.08 mieści się
> w przedziale 06.08 22:05:38Z → 08.08 12:15Z), proporcjonalność do rozmiaru
> sesji („for **some** events"), oraz to, że nadwyżka jest **dodana**
> („**additional** records"), a nie podmieniona.
>
> **Cena tej odpowiedzi: obalona moja trzecia teza.** Wycofałem wcześniej
> ryzyko **A4-11 z audytu 4** („zmiana normalizacji GLBX.MDP3, VII 2026"),
> powołując się na `last_modified_date`. Audyt miał rację, ja nie —
> `last_modified_date` **nie obejmuje zmian normalizacji**. Rozliczenie błędu
> w §4.2.
>
> **Pięć pytań nadal bez odpowiedzi**, bo mail dotarł **ucięty** („Your message
> looks like it was cut off"). Krótkie dopytanie: §5c. Ogłoszenie dostawcy jest
> **nieprzeczytane** — `databento.com` blokuje polityka egress tego środowiska.

> ## ✅ ROZSTRZYGNIĘCIE 09.08 — wariant **B′**, pomiar na treści
>
> Mikro-diff (§3b, §5a, koszt 0,0789 USD) porównał **treść** 30 minut sesji
> 2026-07-03 rekord po rekordzie. Wynik jest jednoznaczny i domyka się
> arytmetycznie:
>
> | | |
> |---|---|
> | wspólnych rekordów | **822 240** |
> | tylko u dostawcy | **18 152** — wszystkie `action=N` |
> | **tylko u nas** | **0** |
> | pięć realnych typów akcji (A, C, F, M, T) | różnica **+0 w każdym** |
>
> **Nasze pliki zawierają 100% realnych zdarzeń rynkowych.** Cała nadwyżka to
> rekordy-wypełniacze bez treści ekonomicznej (`order_id=0`, `side=N`, `size=0`,
> `price=INT64_MAX` = UNDEF_PRICE).
>
> **Skutki:** ❌ nie ma podstawy do odkupu z tytułu kompletności ·
> ⛔ **zakaz mieszania plików z obu okresów pozostaje w mocy** — liczebności
> nadal się nie zgadzają, a mechanizm nie ma nazwy. Propozycja zawężenia
> zakazu (nie decyzja Wykonawcy) leży w §4 pkt 4.
>
> **Test 4 (§3c) dołożył kawałek mechanizmu, którego dostawca jeszcze nie
> nazwał:** wszystkie 18 152 rekordy `N` niosą `F_LAST`, ale **liczba kopert
> jest identyczna** (698 358 po obu stronach), a nadwyżka `F_LAST` na
> rekordach realnych sumuje się co do rekordu do liczby `N`. Bit został
> **przeniesiony** na osobny wypełniacz, nie dodany.
>
> **Test 5 (§3d) domknął diagnostykę:** rekonstrukcja jednostki obserwacji
> daje po obu stronach **29 734 akcje identyczne we wszystkich polach**.
> **Audyt D5-C STOI** — wynik `842 757 zdarzeń` opisuje rynek, nie wersję
> serwowania. Testy 1–5 zamknięte; **nic więcej nie da się ustalić lokalnie.**

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

**Okno skoku — domknięte odczytem manifestu (09.08).** Wcześniejsze wersje
mówiły najpierw o „05.08 vs 06.08", potem o „wieczorze 06–07.08". Obie były
nieprecyzyjne. `pobrano_utc` z `manifest_d5b2.json` = **2026-08-06T22:05:38Z**
(lokalnie 00:05 w nocy 6/7.08) — to ostatni przebieg, o którym **wiadomo
z pobranych plików**, że serwer zwracał wtedy stare liczby. Skok jest więc
zamknięty w przedziale **2026-08-06 22:05:38Z → 2026-08-08 12:15Z**.

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
| **06.08 22:05:38** | przebieg zakupowy, lokalnie (`pobrano_utc`) | stare liczby; pobrane pliki zgodne co do rekordu |
| wieczór 07.08 | dalsze wyceny | **wciąż stare liczby** |
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
między nimi jest **skokowe** i nastąpiło między **06.08 22:05:38Z** a 08.08
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

| | rekordów u nas | rekordów u dostawcy | niedobór | stopa |
|---|---:|---:|---:|---:|
| okno 13:30–14:30 | 1 362 037 | 1 389 818 | 27 781 | **1,999%** |
| reszta sesji | 1 298 592 | 1 318 606 | 20 014 | **1,518%** |

**Mianownikiem stopy jest liczba u DOSTAWCY** — niedobór odnosimy do zbioru
większego, bo to on jest tu punktem odniesienia. Zarzut recenzji P1 przyjęty:
poprzednia wersja tabeli pokazywała tylko kolumnę „u nas" i sugerowała, że to
z niej liczona jest stopa. Przy naszym mianowniku wyszłoby **2,040%**
i **1,541%** — stosunek **1,32×** jest identyczny w obu ujęciach, więc wniosek
się nie zmienia, ale liczby w tabeli muszą dać się odtworzyć bez zgadywania.

Ta sama dwuznaczność siedzi w opisach wcześniejszych commitów. **Komunikatu
commita nie da się poprawić bez przepisania historii**, więc go nie ruszam —
w razie rozbieżności **rozstrzyga ten dokument**, nie opis commita.

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

## 3b. Test 3 — mikro-diff treści · **WYKONANY 09.08**, koszt 0,0789 USD

Procedura i warunki zgody: §5a. Zapytanie `GLBX.MDP3` / `mbo` / `MNQU6`,
**2026-07-03 13:30–14:00 UTC**, zapis do osobnego katalogu `diag_mikro/`
(14,7 MB). `d5b2_mbo/`, `d5c_mbo/` i manifesty nietknięte.

```
rekordow u dostawcy (dzis)  :    840,392
rekordow u nas              :    822,240
WSPOLNYCH (ten sam klucz)   :    822,240
TYLKO u dostawcy            :     18,152
TYLKO u nas                 :          0
```

| action | dostawca | my | różnica |
|---|---:|---:|---:|
| A (Add) | 321 593 | 321 593 | **+0** |
| C (Cancel) | 321 150 | 321 150 | **+0** |
| F (Fill) | 57 862 | 57 862 | **+0** |
| M (Modify) | 88 682 | 88 682 | **+0** |
| T (Trade) | 32 953 | 32 953 | **+0** |
| **N (None)** | **18 152** | **0** | **+18 152** |

Arytmetyka domyka się co do rekordu: 822 240 + 18 152 = 840 392.

Przykład rekordu obecnego wyłącznie u dostawcy:

```
ts=2026-07-03 13:30:00.014424+00:00 order_id=0 action=N side=N
px=9223372036854775807 sz=0
```

`price = 9223372036854775807` to `INT64_MAX`, czyli **UNDEF_PRICE** w DBN.
Komplet `order_id=0` + `side=N` + `size=0` + brak ceny oznacza, że rekord
**nie opisuje żadnego zdarzenia księgi**.

### Co to rozstrzyga

**Wariant B′ — potwierdzony pomiarem, nie wnioskowaniem.** Zero rekordów
obecnych tylko u nas i zerowa różnica w każdym z pięciu realnych typów akcji
znaczą, że nasz plik zawiera **komplet zdarzeń rynkowych** tego okna. Różnica
2,16% (18 152 / 840 392) to wyłącznie rekordy `N`.

Uwaga na kierunek dowodu: mikro-diff mierzy **30 minut jednej sesji**. Dla tego
okna wariant A jest wykluczony. Rozciągnięcie na pozostałe 21 sesji jest
uogólnieniem — mocnym, bo tempo niedoboru jest podobne we wszystkich sesjach
(§1), ale nadal uogólnieniem. Nie zamieniam go w twierdzenie o pomiarze.

### Dlaczego klucz porównania celowo nie zawiera `sequence`

Tożsamość rekordu to `ts_recv` + `order_id` + `action` + `side` + `price` +
`size`. `sequence` to numer **wiadomości CME**, nie identyfikator zdarzenia —
potwierdzone oficjalnie przez dostawcę. Gdyby wszedł do klucza, każda zmiana
pakowania komunikatów wyglądałaby jak inne zdarzenie i test **z góry** dawałby
wariant A. Test, który nie może dać drugiej odpowiedzi, nie jest testem.

---

## 3c. Test 4 — flagi rekordów `N` · **WYKONANY 09.08**, koszt 0

`python scripts/diff_mikro.py --flagi`, to samo okno, oba pliki z dysku.

| action | flags | dostawca | my |
|---|---|---:|---:|
| A | — | 7 580 | 74 |
| A | `F_LAST` | 314 013 | **321 519** |
| C | — | 41 311 | 32 974 |
| C | `F_LAST` | 279 839 | **288 176** |
| F | — | 57 862 | 57 862 |
| M | — | 2 328 | 19 |
| M | `F_LAST` | 86 354 | **88 663** |
| **N** | **`F_LAST`** | **18 152** | **0** |
| T | — | 32 953 | 32 953 |

```
kopert (F_LAST) razem u dostawcy  :    698,358
kopert (F_LAST) razem u nas       :    698,358
```

### Pytanie było źle postawione — i to jest mój błąd

Pytałem: *czy rekordy `N` niosą `F_LAST`*. Odpowiedź brzmi „wszystkie 18 152",
a mój skrypt wydrukował na tej podstawie werdykt **„audyt WYMAGA
POWTÓRZENIA"**. **Ten werdykt jest nieprawdziwy** — warunek sprawdzał
`n_z_last == 0` przed porównaniem sum i nigdy nie dotarł do liczby, która ma
znaczenie. Liczba kopert jest po obu stronach **identyczna**.

Bilans domyka się co do rekordu:

| nadwyżka `F_LAST` po naszej stronie | |
|---|---:|
| A | +7 506 |
| C | +8 337 |
| M | +2 309 |
| **razem** | **18 152** = liczba rekordów `N` |

**Bit nie został dodany, tylko przeniesiony.** W nowym serwowaniu kopertę
zamyka osobny rekord-wypełniacz `N`, a nie ostatni rekord realny. Liczba
kopert bez zmian, granice **w tym samym miejscu strumienia**.

### Czego histogram nie może rozstrzygnąć — i dlaczego to nie koniec

Histogram nie widzi **kolejności**. Dwa scenariusze dają w nim identyczne
liczby, a skutki mają przeciwne:

| scenariusz | skutek dla jednostki D5-B2 |
|---|---|
| granica **przeniesiona** na końcowy `N` | **żaden** — koperta zamyka się w tym samym miejscu |
| granica **wstawiona** w środek ciągu `Trade` | **poważny** — akcja rozpada się na dwie |

Na ręcznych fixture'ach oba są zmierzone i rozróżnione
(`tests/test_mbo_events.py::TestRekordyNone`). Na realnym pliku rozstrzyga
dopiero test 5.

## 3d. Test 5 — rekonstrukcja akcji · **WYKONANY 09.08**, koszt 0

`python scripts/diff_mikro.py --rekonstrukcja` — puszcza
`engine/mbo_events.rekonstruuj` na **obu** plikach w tym samym oknie
i porównuje **akcje agresywne** pole po polu, czyli dokładnie tę jednostkę
obserwacji, na której policzono audyt D5-C. Jedyny test w tej diagnostyce,
który patrzy na kolejność rekordów, a nie na ich rozkład.

| | świeży wycinek | nasz plik |
|---|---:|---:|
| akcji agresywnych | **29 734** | **29 734** |
| suma `n_trade` | **32 953** | **32 953** |
| suma rozmiaru | **63 394** | **63 394** |
| pozycja pierwszej różnicy | **n/d** | **n/d** |

```
-> IDENTYCZNE, akcja po akcji, we wszystkich polach.
```

### Werdykt: **audyt D5-C STOI**

Kryterium odczytu było zapisane **przed** uruchomieniem (commit `4ee8708`):
listy identyczne → audyt stoi; jakakolwiek różnica → do powtórzenia. Zapadło
pierwsze, i to bez ani jednej różnicy — więc pytanie o zachowanie na granicy
okna w ogóle nie powstaje.

**Cross-check, który się domyka:** suma `n_trade` = **32 953** zgadza się co
do rekordu z licznikiem `action=T` z testu 3 (32 953 po obu stronach). Dwie
niezależne ścieżki liczenia — surowy histogram akcji i pełna rekonstrukcja
jednostki — dają tę samą liczbę.

Numer koperty jest z porównania świadomie wyłączony: to indeks porządkowy,
a nie cecha zdarzenia.

**Co to znaczy praktycznie:** przeniesienie bitu `F_LAST` na wypełniacz `N`
jest dla naszej jednostki obserwacji **nieodróżnialne**. Wynik
`842 757 zdarzeń, 0 niewyjaśnionych` opisuje więc rynek, a nie wersję
serwowania danych.

**Czego nadal nie obejmuje:** zmierzono 30 minut jednej sesji. Dla tego okna
równoważność jest pomiarem; dla pozostałych 21 sesji pozostaje uogólnieniem.

---

## 3a. Bilans diagnostyki — co wiemy po pięciu testach

| Pytanie | Odpowiedź | Na jakiej podstawie |
|---|---|---|
| Czy pliki są ucięte na końcu? | **Nie** (poza 07-07) | test 1, pokrycie 13:30–19:59:59 |
| Czy pliki mają tyle rekordów, co dziś API? | **Nie, mniej o ~2%** | test 2, okno o pełnym pokryciu |
| Czy niedobór jest jednorodny? | **Nie**, stosunek 1,133 | test 2 |
| Czy brakuje realnych zdarzeń? | **NIE** — 0 rekordów tylko u dostawcy poza `action=N` | test 3 (30 min sesji 07-03) |
| Czy rekordy `N` niosą `F_LAST`? | **Tak, wszystkie 18 152** | test 4 |
| Czy zmieniła się liczba kopert? | **NIE** — 698 358 po obu stronach; bit **przeniesiony**, nie dodany | test 4, bilans domyka się co do rekordu |
| Czy jednostka obserwacji jest ta sama? | **TAK** — 29 734 akcje identyczne we wszystkich polach | test 5 |
| **Czy audyt D5-C stoi?** | **TAK** | test 5; cross-check: suma `n_trade` 32 953 = licznik `action=T` z testu 3 |
| Czy trzeba odkupić pobrane sesje? | **Nie z tytułu kompletności** | test 3 |
| Czy wolno mieszać stare i nowe pliki? | **Nie** | liczebności nadal rozjechane, mechanizm bez nazwy |

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

Konsekwencje — stan po trzech testach:

1. ✅ **Czy plik D5-C obejmuje całe okno RTH** — tak (test 1), pokrycie
   13:30–19:59:59 UTC.
2. ✅ **Czy brakuje realnych zdarzeń** — nie (test 3). Nadwyżka u dostawcy to
   w całości rekordy `action=N` bez treści ekonomicznej.
3. ✅ **Czy zmieniła się liczba kopert** — nie (test 4). 698 358 po obu
   stronach; wszystkie `N` niosą `F_LAST`, ale bit został przeniesiony
   z ostatniego rekordu realnego na dołożony wypełniacz.
3a. ✅ **Czy jednostka obserwacji jest ta sama** — **tak** (test 5). 29 734
   akcje identyczne we wszystkich polach. Wynik `842 757 zdarzeń,
   0 niewyjaśnionych` **stoi**.
4. ⛔ Czy miesiąc D5-B2 wolno policzyć na **mieszance** plików z obu okresów?
   **Zakaz obowiązuje nadal — ale jego uzasadnienie się zmieniło i wymaga
   decyzji właściciela, nie mojej.** Stan wiedzy:

   | | |
   |---|---|
   | co zmierzono | na oknie 30 min jednostka obserwacji jest **identyczna** po obu stronach |
   | co z tego wynika | analiza idąca przez `rekonstruuj` daje ten sam wynik niezależnie od okresu pobrania |
   | co nadal różne | **surowa liczba rekordów** — każdy licznik nieprzechodzący przez jednostkę kanoniczną policzy inaczej |
   | czego nie zmierzono | pozostałych 21 sesji; równoważność jest tam **uogólnieniem** |
   | czego nie wiemy | czy za tydzień nie pojawi się trzecia wersja — mechanizmu nadal nikt nie nazwał |

   **Propozycja do rozstrzygnięcia (Wykonawca nie wydaje tu werdyktu):**
   zawęzić zakaz z „nie mieszać plików" do „nie mieszać **liczników surowych
   rekordów**", dopuszczając mieszanie dla analiz przechodzących przez
   `engine/mbo_events.rekonstruuj`. Warunek minimalny: powtórzyć test 5 na
   drugiej sesji z innego dnia, żeby równoważność przestała stać na jednym
   oknie. **Decyzja należy do właściciela i najlepiej zapada po odpowiedzi
   dostawcy** — bo jeśli mechanizm okaże się niestabilny, zawężenie trzeba
   będzie cofnąć.
5. ✅ Czy trzeba odkupić już pobrane sesje — **nie z tytułu kompletności**.
   Pytanie o rozliczenie przerwanych pobrań (07-06, 07-07) pozostaje otwarte
   i jest pytaniem do dostawcy.

### ⚠️ Wycofanie A4-11 było BŁĘDEM — przywracam, dostawca potwierdził

Napisałem tu wcześniej: *„Powiązanie z ryzykiem A4-11 z audytu 4 (zmiana
normalizacji GLBX.MDP3, VII 2026) **wycofuję** — `last_modified_date` mu
przeczy. To nie jest ten scenariusz; to problem z warstwą metadanych, nie
z normalizacją danych."*

**To była dokładnie ta jedna rzecz, którą audyt 4 przewidział, a ja odrzuciłem.**
Odpowiedź Databento (10.08, §5b) mówi wprost: wdrożono zmianę w GLBX.MDP3,
która powoduje publikowanie **dodatkowych rekordów MBO dla niektórych zdarzeń**.
To jest zmiana normalizacji. **A4-11 wraca jako ryzyko zmaterializowane.**

**Gdzie dokładnie popełniłem błąd w rozumowaniu.** Wnioskowałem tak:
`last_modified_date` = D+1 dla każdej sesji lipca ⟹ dane nie były modyfikowane
⟹ to nie może być zmiana normalizacji. Przesłanka była prawdziwa, wniosek
fałszywy, bo milcząco założyłem, że **`last_modified_date` obejmuje zmiany
normalizacji**. Nie obejmuje — śledzi rewizje danych źródłowych, a nie zmiany
w tym, jak dostawca je serializuje. Pytanie 2 maila pytało dokładnie o to
i było postawione dobrze; szkoda, że sam odpowiedziałem sobie na nie wcześniej
i źle.

**Lekcja, która wychodzi poza ten incydent:** brak sygnału w polu metadanych
jest dowodem tylko wtedy, gdy wiadomo, **co to pole obejmuje**. Nie wiedziałem,
a mimo to użyłem go do odrzucenia hipotezy — i to hipotezy, którą niezależny
audyt postawił z góry.

---

## 5. Pytanie do Databento

**GOTOWY DO WYSŁANIA.** Wszystkie blokery zniesione: testy 1–5 wykonane,
`pobrano_utc` odczytane (**2026-08-06T22:05:38+00:00**), panel Databento
odczytany (§3a `data/KOSZTY.md`).

**Adresat: `support@databento.com`** (decyzja właściciela, 09.08). To skrzynka
ogólna, nie wątek Erika — dlatego mail jest **samodzielny**: nie zakłada, że
czytający pamięta poprzednią rozmowę o `sequence`, tylko powołuje się na nią
jednym zdaniem. Gdyby trafił jednak do tamtego wątku, to zdanie nie przeszkadza.

> **Subject: `metadata.get_record_count` for GLBX.MDP3 MBO jumped ~2.6% for all
> July 2026 sessions, while `get_dataset_condition` reports no modification**
>
> Hello,
>
> We have a reproducibility question about GLBX.MDP3 MBO that we could not
> resolve ourselves, and we have paused a purchase because of it. (We had an
> earlier exchange with Erik on this account about `sequence` semantics in the
> `trades` schema — this is a separate issue, so please feel free to route it
> wherever is appropriate.)
>
> **Setup.** Fixed research query: `GLBX.MDP3`, schema `mbo`, symbol `MNQU6`,
> `stype_in=raw_symbol`, 22 RTH sessions of July 2026, each `13:30–20:00 UTC`
> (09:30–16:00 America/New_York).
>
> **Dated history of our measurements** — the same query, repeatedly:
>
> | When (UTC) | Where | Result |
> |---|---|---|
> | 2026-08-04 13:31 | our cloud environment | 837,310,143 records / 78.6044 USD |
> | 2026-08-04 | `timeseries.get_range` for 2026-07-30 | file contains **38,306,877** records |
> | ~2026-08-05 | re-download of the same session, different machine | identical SHA-256, again 38,306,877 |
> | **2026-08-06 22:05:38** | purchase run (manifest `pobrano_utc`) | same counts; downloaded files match them record-for-record |
> | 2026-08-07 evening | further pricing | still the old counts |
> | **2026-08-08 12:15** | pricing run | **859,343,842 records / 80.6729 USD** |
>
> So the change happened somewhere between **2026-08-06 22:05:38 UTC** —
> the last download that provably returned the old counts — and
> **2026-08-08 12:15 UTC**.
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
>    changed on your side between 2026-08-06 22:05:38 UTC and 2026-08-08
>    12:15 UTC**?
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
>    We then compared the **content** of one 30-minute slice
>    (2026-07-03, 13:30–14:00 UTC), matching records on
>    `ts_recv + order_id + action + side + price + size`:
>
>    | | |
>    |---|---:|
>    | records in a freshly downloaded slice | 840,392 |
>    | records in our pre-change file | 822,240 |
>    | matching on both sides | **822,240** |
>    | present only in the fresh slice | **18,152** — **all `action=N`** |
>    | **present only in our file** | **0** |
>
>    Counts per action type are identical for A, C, F, M and T (difference
>    exactly 0 in each). Every extra record looks like
>    `order_id=0, action=N, side=N, size=0, price=9223372036854775807`
>    (`INT64_MAX` / `UNDEF_PRICE`).
>
>    So our older files appear to contain **all real book events**, and the
>    entire difference consists of placeholder `None` records.
>
>    We also compared the `flags` field. **Every one of the 18,152 `N` records
>    carries `F_LAST`** — and the total number of `F_LAST` records is
>    *identical* on both sides (**698,358**). The surplus of `F_LAST` on our
>    side falls on real records and sums exactly to the number of `N` records:
>
>    | action | `F_LAST` ours − yours |
>    |---|---:|
>    | A | +7,506 |
>    | C | +8,337 |
>    | M | +2,309 |
>    | **total** | **+18,152** |
>
>    Read together, this looks like the end-of-event marker moved: what used to
>    be `F_LAST` on the last real record of an event is now a separate trailing
>    `N` record carrying `F_LAST`. **Is that reading correct?** Specifically:
>
>    a) **What are these `action=N` records, and why do they now appear in
>       historical ranges that previously returned without them?**
>    b) **Is the event partition guaranteed unchanged** — i.e. does the
>       trailing `N` always immediately follow the record that previously
>       carried `F_LAST`, with no real record in between?
>
>       On this window it evidently is: we reconstructed our unit of
>       observation (aggressor action per `Trade`, keyed by `order_id`) from
>       both files and got **29,734 actions identical in every field**, with
>       matching `Trade` counts (32,953) and sizes (63,394). We would like to
>       know whether that is **guaranteed by the format** or merely true of
>       the slice we happened to check — we can only measure 30 minutes,
>       you can answer for the dataset.
> 5. Two sessions were interrupted mid-download — 2026-07-06 returned
>    `Response ended prematurely`, and 2026-07-07 left a truncated file
>    (1,867,793 records, ~7 minutes of a 6.5-hour window).
>
>    Our usage page shows **11.47 GB of MBO historical streaming at 1.80
>    USD/GB = 20.65 USD** for the period, which is more than the 12.81 USD our
>    own per-query estimates account for — consistent with both interrupted
>    requests having been billed **in full**, not by bytes delivered. That
>    leaves roughly **0.35 USD** we cannot attribute to any query we know we
>    made.
>
>    a) Could you provide a **per-request breakdown for 2026-08-06 to 08-09**?
>       The usage page aggregates, so we cannot reconcile it ourselves.
>    b) **Does a retry of a truncated response get billed again in full?**
>       That is our working hypothesis for the ~0.35 USD residue, but it is a
>       hypothesis, not something we measured.
>
> For context: this is a single-instrument research project on a small budget,
> and reproducibility is a hard requirement — a result we cannot recompute later
> is not a result we can use. We stopped after 4 of 22 sessions specifically
> because mixing data from two periods would be invisible in the data itself.
>
> Happy to share the exact queries, the diff script, or the record-level output
> if that helps you reproduce any of the above.
>
> Thanks,

---

## 5b. ODPOWIEDŹ DOSTAWCY — 10.08.2026, mechanizm NAZWANY

Odpowiedź od **Renana (Databento support)**, cytat w całości:

> *We released a change for GLBX.MDP3 over the weekend, which leads to
> additional MBO records being published for some events.*
>
> *Please refer to the following announcement for more details:*
> `https://databento.com/blog/cme-normalization-changes-2026-07`

**To zamyka ramę faktograficzną z §2a.** Przez trzy dni świadomie nie nazywałem
mechanizmu, bo dwie moje próby nazwania go upadły. Nazwał go dostawca i brzmi
on: **celowa zmiana normalizacji, wdrożona w weekend 08–09.08**, publikująca
dodatkowe rekordy MBO dla niektórych zdarzeń.

### Zgodność z naszymi pomiarami — co do szczegółu

| Nasz pomiar | Wypowiedź dostawcy |
|---|---|
| skok zamknięty w 06.08 22:05:38Z → 08.08 12:15Z | „over the weekend" — 08.08 to sobota, przedział się zgadza |
| przyrost **proporcjonalny** do rozmiaru sesji, nie stały | „for **some** events" — dodatkowe rekordy per zdarzenie, więc skalują się z liczbą zdarzeń |
| nadwyżka to wyłącznie `action=N` bez treści ekonomicznej | „**additional** MBO records" — dodane, nie zmienione |
| `tylko u nas: 0`, pięć realnych typów akcji +0 | zdarzenia rynkowe nietknięte — spójne z „additional" |
| liczba kopert identyczna, `F_LAST` przeniesiony | spójne, ale **przez dostawcę niepotwierdzone** |

**Nie odwracam kierunku wnioskowania.** Zgodność liczę jako potwierdzenie
naszych pomiarów przez niezależne źródło, a nie jako dowód, że wszystkie nasze
interpretacje były trafne — jedna z nich (A4-11) właśnie okazała się błędna.

### ⛔ Czego ta odpowiedź NIE rozstrzyga

| Pytanie | Stan |
|---|---|
| Q1 — która liczba jest autorytatywna | **bez odpowiedzi** (implikacja: nowa, ale to mój wniosek, nie ich słowa) |
| Q2 — które pole obserwować dla odtwarzalności | **bez odpowiedzi**; wiemy tylko negatywnie, że `last_modified_date` NIE wystarcza |
| Q3 — czy da się przypiąć wersję zbioru | **bez odpowiedzi** — a to jest dla nas najważniejsze pytanie długoterminowe |
| Q4b — czy podział na zdarzenia jest **gwarantowany** niezmieniony | **bez odpowiedzi**; mamy własny pomiar na 30 minutach (§3d), nie gwarancję formatu |
| Q5 — rozliczenie przerwanych pobrań i residuum 0,3490 USD | **bez odpowiedzi** |

**Powód jest prozaiczny: mail dotarł ucięty** („Your message looks like it was
cut off"). Renan odpowiedział na to, co zobaczył. Pytania trzeba zadać ponownie,
krótko — treść w §5c.

### Ogłoszenie — NIEPRZECZYTANE, i to trzeba wiedzieć

`https://databento.com/blog/cme-normalization-changes-2026-07` jest
**zablokowany przez politykę egress** tego środowiska (`databento.com` odrzucone,
choć `hist.databento.com` przechodzi). Zgodnie z `/root/.ccr/README.md` to
odmowa polityki, której nie obchodzę.

**Dopóki ktoś go nie przeczyta, nie wiemy rzeczy, które mogą być tam wprost:**
czy zmiana obejmuje historię wstecz (nasze pomiary mówią, że tak), czy jest
odwracalna, czy istnieje sposób na wersjonowanie, i czym formalnie są rekordy
`action=N`. **To jest najtańsze źródło odpowiedzi, jakie mamy — tańsze niż
kolejny mail.**

---

## 5c. Dopytanie — krótkie, bo pierwszy mail dotarł ucięty

**Diagnoza problemu z pierwszym mailem: był za długi.** Tabele, cytaty i pięć
rozbudowanych pytań — coś po drodze go przycięło. Ta wersja mieści się na
jednym ekranie i zadaje **cztery pytania, każde jednym zdaniem**. Szczegóły
techniczne oferujemy na życzenie, zamiast wysyłać je z góry.

> **Subject: Re: GLBX.MDP3 MBO record counts — four follow-up questions**
>
> Hi Renan,
>
> Thank you — that explains what we were seeing, and it matches our
> measurements. Apologies for the truncated message; here is the short version.
>
> We hold four July 2026 MBO sessions downloaded **before** the change and
> paused the rest of the purchase. We compared one 30-minute slice
> (2026-07-03, 13:30–14:00 UTC) before/after, record by record: the
> **18,152 extra records are all `action=N`** with `order_id=0`, `size=0` and
> `price=INT64_MAX`, every real action type (A/C/F/M/T) matches exactly, and
> **nothing is present only in our older file**. Reconstructing aggressor
> actions from both files gives **29,734 actions identical in every field**.
>
> Four questions:
>
> 1. **Are the older, pre-change files still valid** for analysis, or should
>    they be re-downloaded to match what the API now returns?
> 2. **Is the event partition guaranteed unchanged** by this release — i.e.
>    does the trailing `action=N` record always follow the record that
>    previously carried `F_LAST`, with no real record in between?
> 3. **Is there any way to pin a dataset version**, so a result computed today
>    can be reproduced later? Reproducibility is a hard requirement for us.
> 4. Two downloads were interrupted (2026-07-06 `Response ended prematurely`,
>    2026-07-07 truncated at 1,867,793 records). **Were they billed in full,
>    and does retrying a truncated response bill again?** Our usage page shows
>    20.65 USD against 20.30 USD of queries we can account for.
>
> Happy to send the exact queries, the diff script, or record-level output.
>
> Thanks,

---

## 5a. Mikro-diff — jedyna droga do rozstrzygnięcia A vs B′

**Zgoda właściciela (R1) udzielona 09.08 z pięcioma warunkami. WYKONANY —
wynik w §3b.** Wszystkie pięć warunków egzekwuje kod `scripts/diff_mikro.py`,
nie dyscyplina:

| # | Warunek zgody | Jak egzekwowany |
|---|---|---|
| 1 | `get_cost` przed pobraniem, STOP > 0,10 USD | `sys.exit` przed `get_range`; zmierzono **0,0789 USD** |
| 2 | zakres wyłącznie 07-03 13:30–14:00 UTC | stałe `START_UTC`/`END_UTC`, brak argumentu CLI |
| 3 | osobny katalog, manifesty nietknięte | `raw_dir("diag_mikro")`; skrypt nie zapisuje manifestów |
| 4 | wpis do `data/KOSZTY.md` niezależnie od wyniku | wykonany — `data/KOSZTY.md` §1 poz. 5 |
| 5 | meldunek z liczbami, zanim cokolwiek dalej | §3b powyżej, przed jakąkolwiek decyzją zakupową |

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

**Odczyt wyniku** (kryterium zapisane **przed** pobraniem):

- realne zdarzenia obecne u dostawcy, nieobecne u nas → **wariant A**
  (pliki niepełne, trzeba odkupić),
- te same zdarzenia, inny podział/typy rekordów → **wariant B′**
  (pliki pełne, ale niemieszalne).

**Zapadł wariant B′** — 0 realnych zdarzeń brakujących, 18 152 rekordów `N`.
Kryterium nie było dostrajane po zobaczeniu liczb (reguła R2): jest w docstringu
skryptu w commicie `85d9e73`, sprzed pobrania.

---

## 6. Co robimy do czasu odpowiedzi

| | |
|---|---|
| **Zakup miesiąca** | **WSTRZYMANY.** Warunek 8 blokuje automatycznie. |
| **Diagnostyka lokalna** | **ZAMKNIĘTA — testy 1–5 wykonane.** Dryf scharakteryzowany w całości |
| **Mechanizm** | **ZNANY od 10.08** — celowa zmiana normalizacji GLBX.MDP3 (§5b) |
| **Ogłoszenie dostawcy** | **DO PRZECZYTANIA** — `databento.com` zablokowany przez egress; najtańsze źródło odpowiedzi |
| **Dopytanie** | §5c — cztery pytania, krótko, bo pierwszy mail dotarł ucięty |
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
4. **Różnica liczebności nie jest różnicą danych.** Trzy testy na
   liczebnościach (§1, test 1, test 2) doprowadziły do pytania, ale żaden nie
   umiał na nie odpowiedzieć. Odpowiedział dopiero pomiar **treści** — za
   0,0789 USD i po tym, jak liczebności wyczerpały swoje możliwości. Kolejność
   „najpierw wyciśnij darmowe, potem kup najmniejszy możliwy pomiar" jest
   wzorcem do powtórzenia, nie jednorazową sztuczką.
5. **Filtr `action` należy do kontraktu wczytywania, nie do detali.**
   Rekordy `action=N` przechodzą przez każdy naiwny licznik rekordów i psują
   porównania między pobraniami. Każdy nowy kod czytający MBO musi je jawnie
   odrzucać albo jawnie uzasadnić, czemu nie.

   **Korekta w tym samym dokumencie:** napisałem najpierw, że
   `engine/mbo_events.py` „jest na nie odporny", bo liczy po `Trade`/`order_id`.
   To było za mocne i sprzeczne z §4.2 tego samego pliku. Moduł czyta `flags`
   z **każdego** rekordu, więc `F_LAST` na wypełniaczu zamyka kopertę tak samo
   jak na rekordzie realnym — regułą 2 rządzi koperta, nie typ akcji.
   Odporność jest **warunkowa** i granica jest teraz zmierzona testami
   (`TestRekordyNone`): granica przeniesiona na końcowy `N` nie zmienia nic,
   granica wstawiona w środek ciągu rozbija akcję na dwie.

6. **Werdykt wypisany przez skrypt to nadal tylko wynik gałęzi `if`.**
   Tryb `--flagi` wydrukował „audyt WYMAGA POWTÓRZENIA", bo sprawdzał
   `n_z_last == 0` przed porównaniem sum kopert — a suma była identyczna.
   Pytanie („czy `N` niosą `F_LAST`") było źle postawione, więc poprawna
   odpowiedź na nie prowadziła do fałszywego wniosku. **Skrypt nie ma
   uprawnienia do wydawania werdyktu o audycie; ma dostarczać liczby.**
   Poprawka nie polegała na złagodzeniu progu, tylko na dołożeniu testu
   **ostrzejszego** (§3d) — porównania samej jednostki obserwacji.
