# Kandydaci mechanizmów Gen2 — backlog, nie zobowiązanie

**Status: BACKLOG.** Zero kodu, zero pobrań, zero prób. Licznik prób pozostaje 0.
Żadna pozycja z tej listy nie jest kartą hipotezy i żadna nie została zamrożona.
Wejście na tę listę **nie jest** decyzją o badaniu — jest decyzją o tym, że temat
zasługuje na rozważenie, kiedy przyjdzie na to czas.

Powstało w oknie oczekiwania, zgodnie z zasadą, że czas czekania na dane jest
jedynym bezczynnym zasobem projektu.

**Wejście do tej listy jest tanie, wyjście z niej drogie.** Dopiero przejście
kandydata w kartę uruchamia `scripts/waliduj_karte.py`, test oryginalności
z PLAN rozdz. 8.4 i licznik prób.

---

## 0. Jak czytać ten dokument

### Rubryka

Ta sama skala 0–5 i te same dziewięć kryteriów co `GEN2_BRIEF.md` §E (max 45).
**Nie oceniam potencjalnego Sharpe'a ani zwrotu** — bez danych byłoby to
zgadywanie udające analizę.

Skróty w tabelach: `mech` siła mechanizmu · `znak` jednoznaczność znaku ·
`fals` falsyfikowalność · `dane` dostępność danych · `koszt` · `okazje` liczba
okazji · `wyk` realizm wykonania · `niez` niezależność od cmentarza Gen1 ·
`funded` zgodność z limitami konta.

### Próg częstotliwości — kryterium wstępne, nie jedno z wielu

Podłoga to **N ≥ 400** (`GEN2_BRIEF` §B). Przy „historia = development only"
liczy się, ile **lat** zajmie zebranie N w przód. Kolumna „lat do N" to
`400 / okazje_rocznie`. Kandydat, dla którego wychodzi ponad ~5 lat, jest
**niedopasowany do horyzontu decyzyjnego właściciela** — niezależnie od tego,
jak dobry jest jego mechanizm. Tak odpadły D2 i D4 z Gen1.

### Status weryfikacji źródeł — czytaj to przed cytowaniem czegokolwiek

| Znacznik | Znaczenie |
|---|---|
| **[Z]** | źródło **zweryfikowane wyszukiwaniem w tej sesji**, link niżej w §6 |
| **[W]** | twierdzenie z **mojej wiedzy treningowej, NIEZWERYFIKOWANE** — traktuj jak hipotezę o literaturze, nie jak fakt |

**[W] nie oznacza „prawdopodobnie prawda".** Oznacza „nie sprawdziłem".
Przed zbudowaniem karty na pozycji [W] trzeba znaleźć i przeczytać źródło —
albo stwierdzić, że go nie ma, co samo w sobie jest informacją o oryginalności.

---

## 1. Rodzina A — przepływ i mikrostruktura

Wspólny przymuszony uczestnik: **animator/HFT z obowiązkiem kwotowania**, który
nie może wycofać płynności bez konsekwencji, oraz **agresor z terminem** (musi
wykonać wolumen w oknie).

### A1 — Trwałość nierównowagi przepływu (OFI) poza oknem jej powstania

- **Mechanizm:** nierównowaga przepływu zleceń ma niemal liniowy wpływ na cenę
  w krótkim horyzoncie, ze współczynnikiem odwrotnie proporcjonalnym do
  głębokości rynku **[Z]** (Cont–Kukanov–Stoikov). Pytanie badawcze projektu jest
  **inne niż tezy pracy**: nie „czy OFI wpływa na cenę teraz", tylko **czy
  wpływ trwa dłużej, niż trwa sama nierównowaga**.
- **Przymuszony uczestnik:** animator odbudowujący zapasy po jednostronnym
  wypełnieniu — musi odwrócić pozycję, bo jego mandat to płynność, nie kierunek.
- **Instrumenty:** MNQ (MES jako test transferu).
- **Dane:** MBO — **płatne**, ~3,60 USD/sesja. To jest dokładnie ścieżka D5-B2.
- **Częstotliwość:** setki tysięcy zdarzeń/sesja → N zbierane w dniach.
- **Trzy powody, dla których może być fałszywe:**
  1. wpływ może być w całości **równoczesny** — OFI i cena to ta sama informacja
     oglądana dwa razy, a nie przyczyna i skutek;
  2. praca dotyczy akcji na NYSE, nie futures na CME — struktura kolejki i klasa
     uczestników są inne;
  3. horyzont „dziesiątek sekund" **[Z]** może być krótszy niż detaliczne
     opóźnienie wykonania, co czyni efekt niedostępnym niezależnie od istnienia.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 4 | 4 | 1 | 2 | 5 | 3 | 5 | 3 | **32** |

### A2 — Asymetria odbudowy głębokości po jednostronnym zdjęciu

- **Mechanizm:** po zmieceniu jednej strony księgi tempo odbudowy jest różne po
  obu stronach; asymetria mierzy, po której stronie płynność jest *niechętna*.
- **Przymuszony uczestnik:** ten sam animator, ale mierzony przez to, czego **nie
  robi** — a nie przez to, co zrobił. To jest różnica mechanizmu wobec A1.
- **Dane:** MBO (te same pliki co A1 — koszt marginalny zerowy, jeśli A1 kupione).
- **Częstotliwość:** dziesiątki tysięcy zdarzeń/sesja.
- **Powody możliwej fałszywości:** (1) asymetria może odzwierciedlać wyłącznie
  trend, a nie niechęć; (2) `mbo` nie pokazuje intencji, tylko zdarzenia;
  (3) pomiar wymaga rekonstrukcji księgi, gdzie każdy błąd daje przekonująco
  wyglądający artefakt.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 1 | 4 | 5 | 3 | 5 | 3 | **31** |

### A3 — Rozmiar agresywnej akcji jako sygnał typu uczestnika

- **Mechanizm:** duża pojedyncza akcja agresywna vs seria drobnych o tym samym
  wolumenie to **różni uczestnicy** — pierwszy ma pilność, drugi algorytm.
- **Przymuszony uczestnik:** wykonujący zlecenie z terminem (VWAP/TWAP z deadline).
- **Dane:** MBO. Jednostka **już zdefiniowana** w `engine/mbo_events.py`.
- **Częstotliwość:** ~900 tys. akcji/sesja.
- **Powody możliwej fałszywości:** (1) rozmiar koreluje ze zmiennością, więc może
  mierzyć amplitudę — czyli dokładnie to, co Gen1 już umie i co nie daje kierunku;
  (2) algorytmy celowo maskują rozmiar; (3) próg „duża" byłby parametrem
  swobodnym, czyli furtką do strojenia.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 4 | 1 | 4 | 5 | 4 | 4 | 3 | **32** |

---

## 2. Rodzina B — kalendarz i rolowanie

Przymuszony uczestnik: **posiadacz pozycji, która wygasa**. Nie może nie zrolować.
To jest najczystszy przymus w całym zestawieniu — termin jest kontraktowy.

### B1 — Kierunkowy ślad presji rolowania w oknie rolki

- **Mechanizm:** spread kalendarzowy rozszerza się w oknie rolki **[Z]**;
  strumień rolek jest jednokierunkowy, bo większość pozycji jest po tej samej
  stronie. Pytanie: czy ten przepływ zostawia ślad w cenie **kontraktu
  frontowego**, a nie tylko w spreadzie.
- **Przymuszony uczestnik:** każdy posiadacz wygasającej pozycji — z twardym,
  z góry znanym terminem.
- **Instrumenty:** MNQ + MES + M2K + MYM (ta sama rolka, cztery niezależne testy).
- **Dane:** **bary w repo = 0 USD.** Daty rolek już policzone w `engine/roll.py`.
- **Częstotliwość:** 4 rolki/rok × ~5 dni okna × 4 instrumenty ≈ **80 obserwacji
  dziennych/rok** → **~5 lat do N=400.** To jest granica akceptowalności.
- **Powody możliwej fałszywości:** (1) rolka jest **doskonale przewidywalna**, więc
  każdy może się do niej ustawić — klasyczny warunek zaniku efektu; (2) rolka
  wpływa na **spread**, a przełożenie na cenę outright wcale nie musi istnieć
  **[Z]**; (3) 80 obserwacji/rok przy czterech skorelowanych instrumentach to
  N_eff istotnie niższe niż N.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 5 | **5** | **5** | 1 | 4 | 4 | 4 | **35** |

### B2 — Dzień wygaśnięcia i rozliczenie SOQ

- **Mechanizm:** rozliczenie po SOQ tworzy uczestników, którzy muszą handlować
  dokładnie w oknie ustalania kursu rozliczeniowego.
- **Dane:** bary w repo = 0 USD.
- **Częstotliwość:** **4 zdarzenia/rok/instrument** → 16/rok przy czterech
  instrumentach → **25 lat do N=400. ODPADA na kryterium wstępnym.**
- **Werdykt:** do backlogu jako *obserwacja*, nie jako kandydat. Zapisany, żeby
  nikt nie zaproponował go ponownie bez policzenia N.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 4 | 5 | 5 | **0** | 2 | 4 | 2 | **29** |

### B3 — Migracja płynności między kontraktami jako predyktor zmienności

- **Mechanizm:** tempo migracji wolumenu ze starego kontraktu na nowy mierzy
  **zdecydowanie** uczestników; wolna migracja = niepewność co do kierunku.
- **Dane:** wolumen per kontrakt — **w repo, 0 USD**.
- **Częstotliwość:** 4 rolki/rok × 4 instrumenty ≈ 16 epizodów/rok.
  **ODPADA jako sygnał samodzielny**; sensowny wyłącznie jako **warstwa
  reżimowa** filtrująca inne karty (tak jak zaplanowano H016).
- **Powody możliwej fałszywości:** (1) tempo migracji jest zwyczajem
  instytucjonalnym, nie sygnałem; (2) mierzy amplitudę, nie kierunek —
  wprost cmentarz Gen1; (3) 16 epizodów nie wystarczy na żadną warstwę.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 2 | 3 | 5 | 5 | 0 | 3 | 3 | 3 | **27** |

---

## 3. Rodzina C — pozycjonowanie i dane sprawozdawcze

### C1 — COT jako sygnał — kandydat na BENCHMARK, nie na hipotezę

- **Ustalenie zweryfikowane [Z], i jest ono negatywne.** Testy przyczynowości
  Grangera dają „bardzo mało dowodów", że pozycje traderów prognozują zwroty;
  jest natomiast istotny dowód, że traderzy **reagują** na zmiany cen. Do tego
  raport ma **3 dni opóźnienia publikacji**.
- **Wniosek dla projektu:** COT wchodzi na listę **jako benchmark do testu
  przyrostowego**, a nie jako kandydat. Uruchamiany raz, z parametrami
  z literatury, **nie zużywa licznika prób**.
- **To jest cenne znalezisko negatywne:** oszczędza ~10 prób, które ktoś mógłby
  wydać na „darmowe dane o pozycjonowaniu".

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 5 | 5 | 5 | 2 | 3 | 2 | 3 | **27** |

### C2 — Zmiana otwartego zainteresowania (OI) a kierunek ruchu ceny

- **Mechanizm:** wzrost OI przy ruchu = nowe pozycje; spadek OI = zamykanie.
  Klasyczne rozróżnienie **[W]**, mierzalne z danych CME.
- **Dane:** dzienne OI/wolumen z CME — **darmowe** (do potwierdzenia stabilności
  publikacji przed budową karty).
- **Częstotliwość:** dzienne, ~252/rok/instrument → **N=400 w ~1,6 roku** przy
  jednym instrumencie, szybciej przy czterech.
- **Powody możliwej fałszywości:** (1) OI dzienne, sygnał intraday — niedopasowanie
  częstotliwości; (2) rozróżnienie jest w każdym podręczniku, więc **cmentarz
  jest gęsty**; (3) OI publikowane z opóźnieniem — trzeba sprawdzić, czy da się
  je wykorzystać bez lookaheadu.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 4 | 4 | **5** | 4 | 4 | 2 | 4 | **33** |

### C3 — Rozbieżność wolumen–OI jako detektor pozycjonowania jednostronnego

- Wariant C2 mierzący **rozjazd** zamiast poziomów. Różnica mechanizmu wobec C2
  wymaga jeszcze nazwania — **dopóki jej nie ma, kandydat schodzi do C2**
  (reguła samoczyszcząca z PLAN 8.4).
- Dane i częstotliwość jak C2.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 2 | 3 | 4 | 5 | 4 | 4 | 2 | 4 | **30** |

---

## 4. Rodzina D — zmienność, opcje i reżim

### D1 — Nachylenie struktury terminowej VIX jako warstwa reżimowa

- **Mechanizm [Z]:** przy **backwardation** kolejny zwrot S&P500 bywa dodatni,
  natomiast przy contango współczynnik **nie jest istotny statystycznie**.
  To jest ważne: efekt jest **jednostronny**.
- **Konsekwencja dla projektu:** D1 nie jest samodzielnym sygnałem — jest
  **filtrem reżimowym** włączającym inne karty. Dokładnie ta rola, którą miała
  pełnić H016 po utracie nosiciela.
- **Dane:** struktura terminowa VIX z CBOE — **darmowa**.
- **Częstotliwość:** dzienna, ale backwardation to **rzadki stan** — realna liczba
  dni-w-reżimie to kilkadziesiąt rocznie. Jako filtr wystarcza; jako sygnał nie.
- **Powody możliwej fałszywości:** (1) jednostronność efektu może być artefaktem
  małej próby stanów backwardation; (2) backwardation zbiega się z krachami —
  efekt może być premią za ryzyko, nie nieefektywnością; (3) jest to jeden
  z najbardziej skomercjalizowanych wskaźników na rynku.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 4 | **5** | **5** | 2 | 4 | 3 | 3 | **32** |

### D2 — Ekspozycja gamma dealerów i przypinanie do strajków

- **Status: PODTRZYMUJĘ NISKĄ OCENĘ z `GEN2_BRIEF` D3 (24/45).**
  Wyszukiwanie **[Z]** potwierdziło, że materiał jest **niemal wyłącznie
  praktyczny** (SpotGamma, Bookmap, blogi), a nie akademicki. Jedyna liczba
  z poważnego źródła (CBOE) dotyczy **wpływu na zmienność 30-minutową**, nie
  na kierunek.
- **To wzmacnia zarzut, a nie kandydata:** przewiduje charakter, nie kierunek —
  czyli cmentarz Gen1 — i jest najgęściej skomercjalizowanym pomysłem na liście.
- **Dane:** OI opcji na NDX/QQQ — **płatne albo trudno dostępne historycznie**.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 2 | 3 | 2 | 2 | 3 | 4 | **1** | 3 | **23** |

### D3 — 0DTE jako zmiana reżimu mikrostruktury, nie jako sygnał

- **Mechanizm:** eksplozja 0DTE zmieniła strukturę przepływu wewnątrzdziennego
  **[Z, CBOE]**. Kandydat nie brzmi „handluj 0DTE", tylko: **czy dane sprzed
  ~2022 są w ogóle wymienne z dzisiejszymi** dla kart intraday.
- **To nie jest hipoteza handlowa — to test ważności próby.** Jeśli odpowiedź
  brzmi „nie", **skraca to historię użyteczną dla wszystkich kart intraday**
  i zmienia rachunek N dla całego projektu.
- **Dane:** bary w repo = 0 USD.
- **Priorytet: WYSOKI mimo braku P&L** — bo wynik warunkuje inne karty.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 4 | — | 4 | **5** | **5** | 5 | — | 4 | — | **n/d** |

### D4 — Zmienność zrealizowana nocna vs dzienna jako warstwa reżimowa

- Wariant H010, która upadła **w swojej roli sygnału**, ale nie została zbadana
  jako **warstwa**. Wymaga jawnej deklaracji, którą kartę ma filtrować — inaczej
  jest to ta sama karta pod nową nazwą.
- **Dane:** w repo = 0 USD. **Częstotliwość:** dzienna.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 2 | 4 | 5 | 5 | 5 | 4 | **1** | 4 | **32** |

---

## 5. Rodzina E — transmisja międzyrynkowa (K6)

### E1 — Rozbieżność MNQ–MES wokół szoków stopowych

- Bliskie H014 (odrzucone w pre-flight). **Wejdzie tylko z nazwaną różnicą
  mechanizmu**; bez niej reguła samoczyszcząca degraduje je do H014.
- **Dane:** ES w repo = 0 USD.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 4 | 5 | 5 | 3 | 4 | **1** | 4 | **32** |

### E2 — Dyspersja składników NDX jako filtr trend/chop

- H016 bez nosiciela. Wraca **tylko** wtedy, gdy inna karta będzie potrzebowała
  filtru — nie jako byt samodzielny.
- **Dane:** warstwa K6 w repo = 0 USD.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 2 | 3 | 4 | 5 | 4 | 4 | 3 | 3 | **31** |

### E3 — Wspólny mechanizm na czterech mikrokontraktach naraz

- **Mechanizm:** nie nowy mechanizm, tylko **dyscyplina testowa**: każdy kandydat
  z tej listy sprawdzany równolegle na MNQ/MES/M2K/MYM.
- **Dlaczego to jest wartość:** mechanizm strukturalny **powinien** działać na
  wszystkich czterech; działanie tylko na jednym jest sygnałem dopasowania.
  Silnik, kalendarz i model kosztów obsłużą je prawie bez zmian.
- **Koszt:** MES/M2K/MYM bary ≈ koszt MNQ (~14 USD każdy) — **wymaga zgody R1**.
- **Zastrzeżenie:** cztery instrumenty indeksowe US są silnie skorelowane, więc
  **N_eff rośnie znacznie wolniej niż N**. To jest test uniwersalności, nie
  sposób na czterokrotne zwiększenie próby — i nie wolno go tak liczyć w DSR.

| mech | znak | fals | dane | koszt | okazje | wyk | niez | funded | **suma** |
|---|---|---|---|---|---|---|---|---|---|
| — | — | 5 | 3 | 3 | — | 4 | 5 | — | **n/d** |

---

## 6. Rodzina F — pozycje zamknięte na kartce

Zapisane, żeby nie wracały. Odrzucenie na kartce jest najtańszą formą odrzucenia.

**Cztery odrzucone (F1–F4) i jedna przypomniana (F5).** F5 NIE jest odrzucona i nie
liczy się do odrzuconych — stoi tu wyłącznie po to, żeby lista nie sugerowała, że
o niej zapomniano.

| # | Kandydat | Powód odrzucenia |
|---|---|---|
| F1 | Lead-lag NQ→MNQ | Zjawisko milisekundowe; na M1 **każdy wynik byłby artefaktem agregacji** wyglądającym przekonująco. To jest H015 i pozostaje warunkowa. |
| F2 | Sezonowość kalendarzowa (efekt miesiąca, dnia tygodnia) | Cmentarz maksymalnie gęsty, mechanizm nienazywalny, N śmiesznie małe. B03 już to zmierzył: SR −0,73. |
| F3 | Wskaźniki techniczne w nowej kombinacji | Łamie test oryginalności wprost: inne parametry to nie inny mechanizm (audyt 3). |
| F4 | Sentyment z mediów społecznościowych | Płatne API, brak przymuszonego uczestnika, nieodtwarzalne historycznie. |
| F5 | Rebalans funduszy lewarowanych (D1 z GEN2_BRIEF) | **NIE odrzucony** — to nadal najwyżej oceniony kierunek (40/45). Wymieniony tutaj, żeby ta lista nie sugerowała, że go zapomniano. Czeka na werdykt D5-B2. |

---

## 7. Podsumowanie — co z tego wynika

**Bilans listy:** 16 pozycji rozpatrzonych z rubryką, 4 odrzucone na kartce (F1–F4),
1 przypomniana bez odrzucenia (F5) — razem 21 wpisów.

**Najwyższe sumy:** B1 rolka (35), C2 zmiana OI (33), A1/A3 mikrostruktura (32).
**Poza rankingiem, ale pilne:** D3 (test ważności próby) — bo jego wynik
warunkuje rachunek N dla wszystkich kart intraday.

**Trzy obserwacje, które zmieniają obraz bardziej niż sam ranking:**

1. **C1 (COT) został zweryfikowany negatywnie, zanim kosztował cokolwiek.**
   Literatura mówi, że traderzy reagują, a nie prognozują **[Z]**. Wchodzi jako
   benchmark. To jest wzorcowy przykład, po co ten dokument istnieje.
2. **D2 (gamma) potwierdził swoją niską ocenę z innego kierunku** — nie brakiem
   mechanizmu, tylko brakiem *akademickiego* potwierdzenia przy jednoczesnym
   nasyceniu komercyjnym. Materiał praktyczny jest obfity, akademicki niemal
   nieobecny **[Z]**.
3. **Rodzina B jest najczystsza mechanicznie i najsłabsza liczbowo.** Termin
   wygaśnięcia to najtwardszy przymus w całym zestawieniu — i daje 4 zdarzenia
   rocznie. To napięcie (im czystszy przymus, tym rzadszy) jest strukturalną
   własnością tego rynku, nie pechem doboru.

**Czego ten dokument NIE rozstrzyga:** czy którykolwiek kandydat ma przewagę.
Ranking mówi wyłącznie, gdzie warto wydać *następne* próby, jeśli D5-B2 skończy
się na NO-GO. Przy GO ta lista czeka.

---

## 8. Źródła zweryfikowane w tej sesji

- Cont, Kukanov, Stoikov — *The Price Impact of Order Book Events*:
  [SSRN 1712822](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1712822)
- *Returns and Order Flow Imbalances: Intraday Dynamics and Macroeconomic News
  Effects*: [arXiv 2508.06788](https://arxiv.org/pdf/2508.06788)
- *Cross-impact of order flow imbalance in equity markets*:
  [Quantitative Finance](https://www.tandfonline.com/doi/full/10.1080/14697688.2023.2236159)
- Slivka, Qin, Ye — *Rolling Over Equity Futures: A Study in Four Countries*:
  [SSRN 3514204](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3514204)
- *On the predictive role of large futures trades for S&P500 index returns
  (analiza COT)*:
  [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1042443113000723)
- *Smart Money: The Forecasting Ability of CFTC Large Traders* (test Grangera,
  wynik negatywny):
  [ResearchGate](https://www.researchgate.net/publication/227350070_Smart_Money_The_Forecasting_Ability_of_CFTC_Large_Traders_in_Agricultural_Futures_Markets)
- CBOE — *0DTE Index Options and Market Volatility*:
  [cboe.com](https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf)
- VIX term structure jako sygnał (backwardation istotna, contango nie):
  [Macrosynergy](https://macrosynergy.com/research/vix-term-structure-as-a-trading-signal/)

**Pozycje oznaczone [W] nie mają tu wpisu — bo nie zostały zweryfikowane.**
Brak wpisu jest informacją, nie przeoczeniem.
