# Dryf metadanych GLBX.MDP3 — zakup miesiąca WSTRZYMANY

**Data wykrycia: 06.08.2026. Status: OTWARTE. Zakup zablokowany warunkiem 8.**

---

## 1. Objaw

Dwa uruchomienia wyceny tego samego, zamrożonego zapytania — ten sam zbiór,
ten sam instrument, ten sam schemat, **te same granice UTC** (potwierdzone
przez warunek 3: `manifest: zgodny (22 sesji)`) — dały **różne liczby
rekordów dla wszystkich 22 sesji**.

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
i wskazuje na rewizję samych danych.

### Nie błąd naszego sumowania

`metadane_dzielone` sumuje 13 kawałków po 30 min. Poprawność sumowania była
zweryfikowana empirycznie na tej samej sesji: 13 kawałków dało **38 306 877**
rekordów i **3,5961 USD**, zgodnie z wartością dla całego zakresu co do rekordu
i czwartego miejsca po przecinku. Kod sumujący nie zmienił się między
uruchomieniami w sposób dotykający arytmetyki.

---

## 3. Dlaczego to jest poważne, a nie kosmetyczne

### 3.1 Ryzyko finansowe — realne i zmierzone

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

### 3.2 Ryzyko naukowe — poważniejsze niż finansowe

**Audyt D5-C policzono na wersji 2026-07-30, której API już nie zwraca.**

Wynik `842 757 zdarzeń, 0 niewyjaśnionych` powstał na pliku o SHA-256
`3e6f023d...74ac42` i **38 306 877** rekordach. Dziś to samo zapytanie zwraca
**39 437 696** rekordów. Ponowne pobranie da inny plik i najprawdopodobniej
inny wynik audytu.

Konsekwencje do rozstrzygnięcia:

1. Czy wynik D5-C jest nadal ważny? Plik u nas jest, SHA się zgadza —
   ale nie jest to już „to, co dostawca uważa za dane tej sesji".
2. Czy miesiąc D5-B2 wolno policzyć na **mieszance** wersji (4 sesje sprzed
   rewizji, 18 po)? **Nie.** W danych nie widać, która sesja pochodzi z której
   wersji; wynik wyglądałby normalnie.
3. Czy trzeba pobrać ponownie wszystko, żeby mieć jedną wersję — i kto
   pokrywa koszt drugiego naliczenia?

To jest dokładnie ryzyko A4-11 z audytu 4 dokumentu założycielskiego:
*„Zmiana normalizacji GLBX.MDP3 (VII 2026). Pinować datę pobrania w manifeście;
regeneracja `clean/` przy zmianach vendora."* Przewidziane — teraz zmaterializowane.

---

## 4. Pytanie do Databento

> **Temat: record counts for historical GLBX.MDP3 MBO data changed between
> two identical queries (2026-08-05 vs 2026-08-06)**
>
> We are running a fixed, frozen research query against `GLBX.MDP3`,
> schema `mbo`, symbol `MNQU6`, `stype_in=raw_symbol`, for 22 RTH sessions
> of July 2026 (each 13:30–20:00 UTC, derived from 09:30–16:00 America/New_York).
>
> We called `metadata.get_record_count` for exactly the same 22 ranges on two
> consecutive days. **All 22 sessions returned higher counts on the second
> day**, by +1.67% to +3.06% (median +2.66%). Total went from 837,310,143 to
> 859,343,842 records; `metadata.get_cost` went from 78.6044 to 80.6729 USD.
>
> The increase is proportional to session size, so it does not look like the
> synthetic order-book snapshot that is added for ranges not starting at UTC
> midnight — a constant per-range addition would affect a small session far
> more in percentage terms, and we observe the opposite.
>
> Our questions:
>
> 1. Was the historical `GLBX.MDP3` MBO data for July 2026 revised, backfilled
>    or re-normalized between 2026-08-05 and 2026-08-06?
> 2. If so, what changed, and is there a changelog or revision notice we should
>    be subscribed to?
> 3. **Is there a way to pin a dataset version**, so that a research result
>    computed today can be reproduced byte-for-byte later? We already record
>    SHA-256 of every downloaded file, but we need to know whether re-downloading
>    the same range is expected to be deterministic over time.
> 4. We downloaded 4 of these sessions before the change and would now be
>    charged again to obtain the revised version. Is re-downloading a revised
>    session billed as a new query?
>
> Context: this is a single-instrument research project on a limited budget.
> We stopped the purchase after 4 of 22 sessions specifically because mixing
> two data versions inside one month would be undetectable in the data itself.

---

## 5. Co robimy do czasu odpowiedzi

| | |
|---|---|
| **Zakup miesiąca** | **WSTRZYMANY.** Warunek 8 blokuje automatycznie. |
| Pliki już pobrane | **NIE kasujemy.** Zgadzają się z liczbami, za które zapłacono. |
| `2026-07-30` z D5-C | **NIE ruszamy.** SHA zamrożony, kopia zapasowa priorytetowa. |
| Analiza miesiąca | zablokowana — nie ma kompletu jednej wersji |
| Licznik prób | 0, bez zmian |

**Nie kupujemy pozostałych 18 sesji, dopóki nie wiadomo, czy za tydzień nie
będą znowu inne.** Wydanie 65 USD na dane, których definicja dryfuje, byłoby
kupowaniem czegoś, czego nie da się odtworzyć — a odtwarzalność jest w tym
projekcie warunkiem, nie ozdobą.

---

## 6. Co ta sytuacja zmienia trwale

1. **Liczba rekordów z metadanych nie jest niezmiennikiem.** Wszędzie, gdzie
   traktowaliśmy ją jako stałą cechę sesji, trzeba porównywać z **manifestem**,
   nie z bieżącym API. Warunek 8 to egzekwuje.
2. **SHA-256 pliku jest jedynym twardym identyfikatorem**, jaki mamy.
   Kopia zapasowa surowych plików (URUCHOMIENIE_LOKALNE §8.1) przestaje być
   ostrożnością, a staje się jedynym sposobem zachowania wersji, na której
   policzono wynik.
3. **Każdy wynik na danych MBO musi podawać SHA plików wejściowych.**
   Bez tego „powtórzyliśmy i wyszło inaczej" jest nierozstrzygalne.
