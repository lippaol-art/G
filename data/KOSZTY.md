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
| 5 | D5 diagnostyka | `mbo` MNQU6, **30 min** 2026-07-03 13:30–14:00 | **0,0789 USD** | mikro-diff, limit 0,10 — dotrzymany |

**Suma zakupów unikalnych: 40,0250 USD** (przy górnej granicy pozycji 3:
41,5350 USD).

### Pozycja 5 — jedyny zakup diagnostyczny w projekcie

Zgoda właściciela wg reguły R1, udzielona 09.08 z pięcioma warunkami
(wyliczone i odhaczone w `docs/D5_DRYF_METADANYCH.md` §5a). Cel: rozstrzygnąć,
czy pliki kupione przed 08.08 są niekompletne — bo od tego zależało, czy trzeba
je **odkupić za ~13 USD**.

**Zwrot z tego wydatku:** wynik (§3b tamże) wykluczył odkup. 0,0789 USD kupiło
odpowiedź na pytanie warte dwa rzędy wielkości więcej. Zapisuję to nie jako
pochwałę, tylko jako wzorzec: **najmniejszy możliwy płatny pomiar zamiast
decyzji podjętej w niepewności**.

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
| MBO, **17 pozostałych** sesji RTH lipca 2026 | **63,94 USD** | ⛔ **ZAMROŻONE** — patrz §3a (konto) i `D5_DRYF` §5e (drugi mikro-diff) |
| Cała miesięczna próbka MBO (22 sesje, nowa normalizacja) | **80,68 USD** | limit zamrożony: **82,00 USD**, zapas 1,32 |

**Stan pobrań: 5 z 22 sesji**, wszystkie w **starej** normalizacji —
2026-07-01, 07-02, 07-03, **07-06** i 07-30. Sesja 07-06 była raz przerwana
(`Response ended prematurely`), ale drugie pobranie **zakończyło się
powodzeniem**: plik jest kompletny (32 369 900 rekordów, pokrycie
13:30–19:59:59), a podwójne naliczenie rozliczone w §3a. Wcześniejszy wpis
„pobrano 3 z 21, przerwane na 07-06" był nieaktualny od diagnostyki 08.08.

Zostaje więc **17 sesji do dokupienia**, nie 18 i nie 21: 07-30 mamy z D5-C,
a downloader **musi wykryć ją jako kompletną i pominąć** — inaczej naliczyłby
ją trzeci raz.

---

## 3a. Przerwane pobrania — rekonsyliacja PODWAŻONA 11.08

> ### ⚠️ CAŁA TA SEKCJA MOŻE OPISYWAĆ NIEWŁAŚCIWE KONTO
>
> Właściciel zgłosił 11.08, że **rozliczenie MBO szło z innego konta** niż to,
> którego panel odczytaliśmy 09.08. Jeżeli tak, to poniższa rekonsyliacja
> (20,65 wobec 20,30 USD, residuum 0,3490) **nie dotyczy zapytań, o których
> mówi** — i wtedy nie jest ani potwierdzeniem, ani zaprzeczeniem tego, czy
> przerwane pobrania zostały naliczone.
>
> **Zostawiam liczby nietknięte i oznaczone, zamiast je kasować.** Skasowanie
> zatarłoby to, że przez dwa dni traktowaliśmy je jako pomiar — w tym w mailu
> do Databento, gdzie podaliśmy je jako podstawę pytania o rozliczenie.
> Databento przekazało sprawę do zespołu billingowego **na podstawie tych
> liczb**; jeśli dotyczą innego konta, trzeba to sprostować, zanim odpowiedzą.
>
> **Do ustalenia, po kolei:** (1) z którego konta faktycznie szły zapytania MBO,
> (2) odczyt panelu **tego** konta, (3) czy 125 USD kredytu startowego było na
> jednym koncie, czy na obu, (4) czy pozostałe **104,35 USD** kredytu, na które
> liczymy przy zakupie 18 sesji, w ogóle jest tam, gdzie myślimy.
>
> **Punkt 4 jest jedynym, który blokuje decyzję zakupową** — reszta to
> księgowość. Dopóki nie wiadomo, gdzie leży kredyt, „starczy z zapasem"
> jest twierdzeniem bez pokrycia.

**Odczyt panelu Databento (09.08) — konto NIEPOTWIERDZONE:**

| | |
|---|---|
| Historical streaming, MBO | **11,47 GB × 1,80 USD/GB = 20,65 USD** |
| Pokryte kredytami | −20,65 USD |
| **Obciążenie karty** | **0,00 USD** |
| Kredyt pozostały | **104,35 / 125 USD** |

### Rekonsyliacja

| | |
|---|---:|
| obciążenia wg panelu | **20,6500** |
| potwierdzone naszymi wycenami (§1 poz. 5 + trzy sesje + 07-06) | 12,8093 |
| **różnica** | **7,8407** |
| przerwane 07-06 + 07-07 liczone w **pełnym** zakresie | 3,0388 + 4,4529 = **7,4917** |
| **residuum** | **+0,3490** |

**Wniosek pomiarowy: przerwane pobrania zostały naliczone w całości.**
Precedens z D5-B potwierdzony — Databento rozlicza **zrealizowane zapytanie,
nie odebrane bajty**. Pozycje przestają być „niepotwierdzone".

**Residuum 0,3490 USD pozostaje niewyjaśnione.** Hipoteza recenzenta (**nie
pomiar**): dwa dodatkowe pobrania uciętego fragmentu 07-07 przy ponowieniach,
2 × 1 867 793 rek. ≈ 0,3507. Zgadza się co do trzeciego miejsca, ale panel
**agreguje i nie daje rozbicia per zapytanie**, więc tego nie zweryfikowałem.
Pytanie 5a w mailu do Databento prosi o to rozbicie.

**Stawka 1,80 USD/GB potwierdza model wyceny niezależnie:** 78,6044 USD =
43,669 GB × 1,80, przy GB = 1024³. Dwie różne drogi (cena za rekord
~9,388·10⁻⁸ i cena za gigabajt) prowadzą do tej samej kwoty.

Potwierdzone diagnostyką 08.08: plik 07-07 ma **1 867 793 rekordy** i kończy
się o **13:37:57 UTC** — 7 minut z 6,5-godzinnego okna, czyli **3,94%
rekordów** (1 867 793 / 47 432 653) i ~2% czasu.

**2026-07-07 zgłoszona przez recenzję P1** — na dysku leży plik obcięty
(1 867 793 z 47 432 653 rekordów, `BentoWarning: DBN file is truncated`),
pozostałość po przerwanym przebiegu. **2026-07-06:** transfer przerwał się po
215,2 MB z ~0,7 GB (`BentoError: Response ended prematurely`). Obie sesje
wymagają ponownego pobrania, co naliczy je **drugi raz**.

Zgodnie z zasadą 3 tego rejestru duplikacja dostaje własną pozycję i nie
zostaje schowana w sumie zbiorczej.

**Stan pieniędzy, uczciwie:**

| | |
|---|---:|
| faktycznie obciążone konto (panel) | **20,6500 USD** |
| z tego z karty | **0,00 USD** — pokryte kredytami |
| kredyt pozostały | **104,35 / 125 USD** |
| przypisane do konkretnych zapytań | 20,3010 |
| **nieprzypisane** | **0,3490** |

Wcześniejszy podział na „potwierdzone 12,8093 / niepotwierdzone do ~7,49"
**przestaje obowiązywać** — panel pokazał kwotę faktyczną i jest ona wyższa
niż górna granica moich wycen (20,65 wobec 20,30). Zasada 4 rejestru zadziałała
w obie strony: granica była podana uczciwie, ale pomiar i tak ją przekroczył
o 0,3490 USD, których nie umiem przypisać.

**Skutek dla budżetu — WSTRZYMANY do wyjaśnienia konta.** Na odczytanym
koncie nic nie poszło z karty, a 104,35 USD kredytu wystarczyłoby na 18 sesji
(≤ 68 USD) z zapasem. **Ale jeśli zapytania MBO szły z innego konta, to zdanie
opisuje nie ten portfel.** Nie powtarzam go jako podstawy decyzji, dopóki
konto nie jest potwierdzone.

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
na dwóch maszynach, skok między **06.08 22:05:38Z** a 08.08 12:15Z, brak
modyfikacji wg dostawcy. Mechanizm ma nazwać dostawca.

Diagnostyka lokalna (08.08), **oba testy wykonane**: pięć plików bez uciętego
ogona, 07-07 obcięty. Test gęstości: w oknie 13:30–14:30 sesji 07-03 nasz plik
ma **1 362 037** rekordów wobec **1 389 818** u dostawcy — brakuje **27 781
(−2,00%)** w oknie o **pełnym pokryciu czasowym**.

**„PEŁNY" jest więc obalone empirycznie: pliki są krótsze o ~2%, a brak siedzi
w środku sesji.**

**Rozstrzygnięte 09.08 mikro-diffem (pozycja 5, 0,0789 USD): wariant B′.**
W oknie 30 minut sesji 07-03 rekordów wspólnych **822 240**, tylko u dostawcy
**18 152** (wszystkie `action=N`, bez ceny i wolumenu), **tylko u nas 0**,
a pięć realnych typów akcji zgadza się co do rekordu. **Nasze pliki mają
komplet zdarzeń rynkowych — odkup z tytułu kompletności odpada.**

> **Stan aktualny: §3 — zostało 17 sesji za 63,94 USD.** Zapis „18 sesji
> ≤ 68 USD" poniżej pochodzi z 08.08 i policzony jest po ówczesnych liczbach
> rekordów; zostaje jako datowany ślad, nie jako bieżąca kwota.

Skutek dla tego rejestru: **nie da się dziś podać kosztu dokończenia zakupu**,
bo nie wiadomo, którą wersję danych kupujemy ani czy za tydzień nie będzie
trzeciej. To, że treść zdarzeń jest ta sama, **nie znosi** tego problemu —
znosi tylko groźbę zapłacenia drugi raz za to samo. Zgodnie z zasadą 4 podaję
więc granicę, nie liczbę: pozostałe 18 sesji to **≤ 68 USD** przy wycenie
z 08.08.

**Zapas do limitu topnieje.** Zamrożony limit to 82,00 USD, dzisiejsza wycena
22 sesji 80,6729 — zostaje **1,3271 USD**. Kolejny wzrost o ~1,65% i warunek 2
zablokuje miesiąc. To argument, żeby po odpowiedzi Databento nie zwlekać
z decyzją — a nie żeby podnosić limit.

Pobrane i opłacone do tej pory: **5 z 22 sesji** (4 kampanijne + 07-30 z D5-C). Plików **nie kasujemy** —
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
