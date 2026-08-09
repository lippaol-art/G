# Rejestr kosztów danych Databento

Jawna księgowość wszystkich zakupów danych w projekcie. Powstał, gdy przenosiny
na maszynę lokalną wymusiły **ponowne pobranie sesji już raz kupionej** —
i decyzja właściciela projektu brzmiała: *„Nie ukrywamy tej duplikacji
w księgowości."*

**Ograniczenie, które trzeba znać:** Databento **nie udostępnia w API endpointu
rozliczeniowego** (`metadata` ma tylko `get_cost`, `get_record_count`,
`get_billable_size`). Wszystkie kwoty poniżej to **wyceny `metadata.get_cost`
dla dokładnie tych zapytań, które wykonano**, a nie odczyt z konta. Stan
kredytu należy weryfikować w panelu Databento.

---

## 1. Zakupy wykonane

| # | Etap | Zakres | Koszt | Uwagi |
|---|---|---|---|---|
| 1 | Gen1 | MNQ, NQ, ES `ohlcv-1m` 2019–2026 + warstwa K6 | **7,8200 USD** | udokumentowane w `data/manifest.md` |
| 2 | D5 Etap 1 | `trades` MNQU6, **pełna doba** 2026-07-30 | **2,1240 USD** | limit 2,15 — dotrzymany |
| 3 | D5-B | `trades` MNQU6, 21 sesji RTH lipca 2026 | **26,4060 USD** | wycena; górna granica **27,9160** |
| 4 | D5-C | `mbo` MNQU6, RTH 2026-07-30 | **3,5961 USD** | limit 4,00 — dotrzymany |

**Suma zakupów unikalnych: 39,9461 USD** (przy górnej granicy pozycji 3:
41,4561 USD).

### Dlaczego pozycja 3 ma dwie liczby

Pierwsze podejście urwało transfer sesji `2026-07-07` (koszt tej sesji
1,5098 USD) i ponowne pobranie mogło zostać naliczone drugi raz. Bez endpointu
rozliczeniowego **nie potrafię odczytać rzeczywistej kwoty**, więc podaję
granicę górną zamiast liczby, której nie zmierzyłem.

---

## 2. Duplikacja — ponowne pobranie 2026-07-30

| | |
|---|---|
| Plik | `mbo` MNQU6, RTH 2026-07-30 |
| Pierwszy zakup | **3,5961 USD** — środowisko zdalne, 2026-08-04 |
| Ponowne pobranie | **3,5961 USD** — maszyna lokalna |
| **Nadmiarowy wydatek** | **3,5961 USD** |

**Przyczyna:** dane surowe są w `.gitignore` i nigdy nie przechodzą przez
repozytorium, a dysk środowiska zdalnego znika razem z kontenerem. Plik ma
646 MiB przy limicie transferu 30 MiB — przeniesienie było niewykonalne.

**Czego duplikacja uniknęła:** plik `trades` (31,1 MB) zmieścił się w limicie
i został przeniesiony, oszczędzając **2,1240 USD**.

**Bilans przenosin: −3,5961 USD zapłacone drugi raz, +2,1240 USD uniknięte.**

Ta pozycja **nie zwiększa** kosztu unikalnej próbki miesięcznej — sesja
2026-07-30 i tak wchodzi w skład 22 sesji MBO. Jest natomiast realnym wydatkiem
z konta i dlatego stoi tu osobno.

---

## 3. Planowane, jeszcze niewykonane

| Pozycja | Koszt | Status |
|---|---|---|
| MBO, pozostałe **21 sesji** RTH lipca 2026 | **75,0083 USD** | 🔄 **W TRAKCIE.** Wycena 06.08.2026: 78,6044 USD za 22 sesje (limit 82,00); 2026-07-30 pominięta (SHA zgodny). Pobrano **3 z 21**: 2026-07-01, 07-02, 07-03 — **9,6916 USD**. Przerwane na 2026-07-06 (`Response ended prematurely`, plik częściowy 215,2 MB). |
| Cała miesięczna próbka MBO (22 sesje) | 78,6044 USD | limit zamrożony: **82,00 USD** |

Miesięczny downloader **musi wykryć 2026-07-30 jako kompletną i ją pominąć** —
inaczej naliczyłby ją trzeci raz.

---

## 3a. Pozycje do wyjaśnienia — przerwane pobrania

| Pozycja | Kwota | Status |
|---|---|---|
| MBO 2026-07-06, pobranie przerwane w locie | **3,0388 USD** | ⚠️ **NIEPOTWIERDZONA** |
| MBO 2026-07-07, pobranie przerwane w locie | **≤ 4,4529 USD** | ⚠️ **NIEPOTWIERDZONA** |

Potwierdzone diagnostyką 08.08: plik 07-07 ma **1 867 793 rekordy** i kończy
się o **13:37:57 UTC** — 7 minut z 6,5-godzinnego okna, czyli **3,94%
rekordów** (1 867 793 / 47 432 653) i ~2% czasu.

**2026-07-07 zgłoszona przez recenzję P1** — na dysku leży plik obcięty
(1 867 793 z 47 432 653 rekordów, `BentoWarning: DBN file is truncated`),
pozostałość po przerwanym przebiegu. Kwota podana jako **granica górna**
(wycena z przebiegu #1); po korekcie metadanych może wynieść ~4,45 USD.
Bez tej pozycji największe niepotwierdzone naliczenie byłoby poza księgą.

**2026-07-06:** transfer przerwał się po 215,2 MB z ~0,7 GB (`BentoError:
Response ended prematurely`). Obie sesje wymagają ponownego pobrania, co
naliczy je **drugi raz**.

**Nie wiem, czy przerwane pobrania zostały naliczone.** Precedens
z D5-B (2026-07-07) sugeruje, że tak — Databento rozlicza zrealizowane
zapytanie, nie odebrane bajty — ale tego nie zmierzyłem i nie wolno mi tego
podawać jako faktu. **Do sprawdzenia na stronie zużycia konta Databento — spisz WSZYSTKIE
pozycje z 6–8.08, nie tylko te dwie.**

Zgodnie z zasadą 3 tego rejestru duplikacja dostaje własną pozycję i nie
zostaje schowana w sumie zbiorczej. Po weryfikacji: albo wpisy znikają, albo
zamieniają się w potwierdzone pozycje duplikacji.

**Stan pieniędzy, uczciwie:** potwierdzone wycenami **12,7304 USD**
(9,6916 za trzy sesje + 3,0388 za 07-06). Niepotwierdzone: **do ~7,49 USD**.
Liczba „12,7 USD wydane" z wcześniejszego meldunku była **dolną granicą
podaną jak stan** — poprawka z recenzji P1 przyjęta.

---

## 3b. ⛔ ZAKUP WSTRZYMANY 08.08.2026 — rozjazd metadanych

Wycena tych samych, zamrożonych zapytań wzrosła z **78,6044** na **80,6729 USD**
(+2,63%), bo liczba rekordów wzrosła we **wszystkich 22 sesjach**. Analiza:
`docs/D5_DRYF_METADANYCH.md`.

**Dwie diagnozy już upadły — obie moje, obie obalone pomiarem.**
(1) „Dostawca zrewidował dane" — odrzucone przez `get_dataset_condition`.
(2) „Wyceny zaniżone przez awarię 503/504" — odrzucone przez oś czasu:
commit `299ca34` z **04.08 13:31Z**, dwa dni przed awarią, ma identyczne
liczby, a pobrania z 04–05.08 fizycznie je zawierają.

Obowiązuje **rama faktograficzna bez mechanizmu**: wartość stabilna ≥4 dni
na dwóch maszynach, skok między wieczorem 06–07.08 a 08.08 12:15Z, brak
modyfikacji wg dostawcy. Mechanizm ma nazwać dostawca.

Diagnostyka lokalna (08.08), **oba testy wykonane**: pięć plików bez uciętego
ogona, 07-07 obcięty. Test gęstości: w oknie 13:30–14:30 sesji 07-03 nasz plik
ma **1 362 037** rekordów wobec **1 389 818** u dostawcy — brakuje **27 781
(−2,00%)** w oknie o **pełnym pokryciu czasowym**.

**„PEŁNY" jest więc obalone empirycznie: pliki są krótsze o ~2%, a brak siedzi
w środku sesji.** Czy to realne zdarzenia (wariant A — trzeba odkupić), czy
inna reprezentacja tych samych (B′ — nie kupujemy), rozstrzyga wyłącznie
porównanie treści: `docs/D5_DRYF_METADANYCH.md` §5a, koszt ~**0,079 USD**,
**wymaga jawnej zgody (R1), nieuruchomione**.

Skutek dla tego rejestru: **nie da się dziś podać kosztu dokończenia zakupu**,
bo nie wiadomo, którą wersję danych kupujemy ani czy za tydzień nie będzie
trzeciej. Zgodnie z zasadą 4 podaję więc granicę, nie liczbę: pozostałe
18 sesji to **≤ 68 USD** przy wycenie z 08.08.

**Zapas do limitu topnieje.** Zamrożony limit to 82,00 USD, dzisiejsza wycena
22 sesji 80,6729 — zostaje **1,3271 USD**. Kolejny wzrost o ~1,65% i warunek 2
zablokuje miesiąc. To argument, żeby po odpowiedzi Databento nie zwlekać
z decyzją — a nie żeby podnosić limit.

Pobrane i opłacone do tej pory: **4 z 22 sesji**. Plików **nie kasujemy** —
zgadzają się z liczbami, za które zapłacono.

---

## 4. Zasady, które ten rejestr utrwala

1. **Każdy zakup ma zamrożony limit w commicie sprzed zakupu** (reguła R4).
   Limit zatrzymał zakup dwukrotnie i za każdym razem miał rację.
2. **Wycena bezpośrednio przed pobraniem**, nie sprzed kilku dni. Moje
   ekstrapolacje kosztu myliły się o 21% i o 40%.
3. **Nie ukrywamy ponownych naliczeń.** Duplikacja ma własną pozycję.
4. **Kwota, której nie zmierzyłem, jest podawana jako granica**, nie jako
   liczba.
