# Synteza pierwszej generacji — wnioski W001–W013

**Dokument zamykający katalog H001–H016.** Powstał 02.08.2026, po odrzuceniu
ostatniej karty. Nie zawiera nowych pomiarów: konsoliduje to, co już zmierzono.

> **Stan projektu: 16 kart rozstrzygniętych, licznik prób 0, wydane $7.82,
> zero strategii.**

Ten dokument istnieje po to, żeby następna generacja kart nie powtórzyła
pierwszej. Jego najważniejszą częścią nie jest lista porażek, tylko **rejestr
ekspozycji na dane** (rozdz. 4) i **protokół drugiej generacji** (rozdz. 5).

---

## 1. Mapa wszystkich wyników

### 1.1 Legenda kategorii porażki

Sześć różnych rzeczy bywa nazywanych „karta nie działa" i mieszanie ich jest
kosztowne, bo każda implikuje co innego dla przyszłości.

| Kod | Znaczenie | Co implikuje |
|---|---|---|
| **BRAK** | zależności nie ma | mechanizm był fikcją; nie wracać |
| **AMPLITUDA** | zależność istnieje, ale mówi o wielkości ruchu, nie o kierunku | zmienna użyteczna gdzie indziej (sizing) |
| **KOSZTY** | zależność istnieje i przewiduje kierunek, ale nie przeżywa kosztów | wracać tylko przy niższych kosztach albo większym edge'u |
| **MECHANIZM** | efekt bywa, ale przewidywania mechanizmu są łamane (znak, monotoniczność, symetria) | karta mierzy coś innego niż deklaruje |
| **PRÓBA** | za mało obserwacji, żeby rozstrzygnąć | wraca dopiero z nowymi danymi |
| **NIEWYKONALNA** | zjawisko poza rozdzielczością danych | wraca z innym typem danych |

### 1.2 Karty odrzucone w pre-flight

| ID | Mechanizm | Przewidywanie rozstrzygające | Wynik | Kategoria | Efekt statystyczny? | Handlowalny? | Co zostaje | Ekspozycja danych |
|---|---|---|---|---|---|---|---|---|
| **H011** | sekwencja Azja→Europa przewiduje RTH | kontrast kierunkowy + efficiency ratio | t = −0.44 i **t = −1.34 ze znakiem przeciwnym** | BRAK | nie | nie | — | niska |
| **H005** | pierwszy vs kolejny test PDH/PDL | symetria, monotoniczność w k, stabilność | sygnał +5.07 pkt t = +2.98, ale PDL t = +0.89, skok w k, **rok 2026 = 52% wyniku** | MECHANIZM | tak, pozorny | nie | ostrzeżenie o koncentracji rocznej | średnia |
| **H010** | zmienność zrealizowana vs oczekiwana jako filtr reżimu | efficiency ratio różni się między reżimami | **zakres nocny → zakres RTH t = +10.2**, ale ER t ≈ 0 | AMPLITUDA | **tak, najsilniejszy w projekcie** | nie jako filtr kierunkowy | **zmienna do wielkości pozycji** | średnia |
| **H014** | NDX przereagowuje na szok stóp wobec SPX | rezyduum NQ−βES ma wracać | kontynuuje (corr +0.033); warunkowanie **pogarsza** (t −2.28 → −0.66) | MECHANIZM | tak, wariant odwrócony SR 0.85 | **nie po kosztach dwóch nóg** | hedge ES redukuje szum o 63%; próg opłacalności hedge'u | średnia |
| **H013** | rezydualny repricing indeksu po wynikach megacapów | rezyduum domyka się po otwarciu | corr +0.0808, t = −0.79; po korekcie obciążenia t = −0.11 | MECHANIZM | nie | nie | model nocny (OOS R² 0.9753), kalendarz EDGAR | **wysoka** |
| **H001** | kompresja nocna z równowagi vs z braku uczestników | wolumen przy zadanym zakresie rozdziela charakter sesji | **β₂ wolumenu t = −0.10** po kontroli zakresu | BRAK | nie | nie | — | średnia |
| **H002** | pochodzenie odchylenia od VWAP | świeże wraca, odziedziczone kontynuuje | powroty **t = +2.21**, ale zwrot t = +0.69 i **MFE/MAE symetryczne** | AMPLITUDA / bez PnL | **tak, przeszła 4 kontrole** | nie | **pochodzenie odchylenia jako zmienna reżimowa** | **wysoka** |
| **H003** | impuls wobec równowagi przedpublikacyjnej | iloraz lepszy niż sama wielkość impulsu | **iloraz −3.0 pkt, sama wielkość +5.1 pkt** | MECHANIZM | nie | nie | kalendarz makro BLS+Fed | **wysoka** |

### 1.3 Karty zdegradowane do benchmarków

Zmierzone raz, z parametrami z literatury, bez optymalizacji. **Nie zużywają
licznika prób.**

| ID | Publiczny odpowiednik | Wynik | Wniosek |
|---|---|---|---|
| **B01** (←H006) | gap-fill | N=1551, netto **−5 786 USD**, SR −0.25, PF 0.95 | klasyka indeksowa jest ujemna po kosztach |
| **B02** (←H007) | NR7, Crabel ~1990 | N=279, netto **+1 611 USD**, SR +0.13, PF 1.06 | **jedyny dodatni benchmark**, ale SR daleko poniżej progu |
| **B03** (←H008) | weekend effect | N=355, netto **−16 098 USD**, SR −0.73, PF 0.74 | efekt martwy, jak zapowiadała literatura |
| **B04** (←H012) | momentum wewnątrzdzienne, Gao i in. 2018 | N=1799, netto **−10 658 USD**, SR −0.91, PF 0.84 | bez danych o imbalansach nie ma czego handlować |
| **B05** (←H004) | dryf nocny, Cooper i in. 2008 | SR **0.68** (2019–26) / **0.47** (2021–26) | poniżej progu 0.8 w obu okresach |

### 1.4 Karty nierozstrzygnięte z powodów strukturalnych

| ID | Powód | Kategoria | Kiedy może wrócić |
|---|---|---|---|
| **H015** | price discovery NQ→MNQ rozgrywa się w milisekundach; na barach M1 **każdy wynik byłby artefaktem agregacji** | NIEWYKONALNA | po pozyskaniu `trades`/MBP |
| **H016** | filtr reżimowy bez własnego P&L; jedyny kandydat na nosiciela (H013) upadł | — | gdy pojawi się karta-nosiciel z mierzalnym efektem bazowym |
| **H009** | zastąpiona przez H013 przed testem | — | nie wraca |

---

## 2. Cztery klasy odkrytych zmiennych

Najważniejszy rozdział dla przyszłych sesji. **Zmienna, która przewiduje
amplitudę, nie staje się sygnałem kierunkowym przez zmianę nazwy.**

### 2.1 Zmienne przewidujące AMPLITUDĘ

Mówią, jak duży może być ruch. **Nie mówią, dokąd.**

| Zmienna | Siła | Źródło | Dopuszczalne użycie |
|---|---|---|---|
| zakres nocny → zakres RTH | **t = +10.2** — najsilniejszy pojedynczy wynik projektu | W004 (H010) | wielkość pozycji, normalizacja progów |
| rezyduum NQ−βES redukuje szum NQ o **63%** (sd 0.964% → 0.353%) | duża | W006 (H014) | obniżenie wymaganego edge'u — **ale patrz koszt drugiej nogi** |
| ruch po zamknięciu w dni publikacji wyników: **3.56% wobec 0.11%** (32×) | bardzo duża | W008 | oczekiwana zmienność zdarzenia |

**Zakaz wynikający z W005:** żadnej z tych zmiennych nie wolno użyć jako sygnału
kierunkowego bez osobnego dowodu, że przewiduje znak. H010 dało t > 10 i zostało
odrzucone właśnie dlatego, że mierzyło amplitudę tam, gdzie karta potrzebowała
kierunku.

### 2.2 Zmienne przewidujące KIERUNEK

**Nie znaleziono ani jednej, która spełnia bramkę projektu.**

To jest główny wynik pierwszej generacji i trzeba go napisać wprost. Szesnaście
kart, z których osiem miało jawnie kierunkową tezę, i żadna nie dostarczyła
stabilnego predyktora znaku przechodzącego SR ≥ 0.8 po kosztach.

Najbliżej były:

| Kandydat | Co miał | Dlaczego nie |
|---|---|---|
| wariant kontynuacyjny H014 | SR brutto **0.85**, 7 z 8 lat dodatnich | koszty dwóch nóg zjadają 73% przewagi → SR 0.23, pod stresem ×2 ujemny |
| B02 (NR7) | jedyny dodatni benchmark, netto +1 611 USD | SR +0.13, rząd wielkości poniżej progu |

### 2.3 Zmienne REŻIMOWE i warunkujące

Opisują, w jakim stanie jest rynek. **Nie generują wejść.**

| Zmienna | Zmierzone | Status |
|---|---|---|
| **pochodzenie odchylenia od VWAP** (świeże vs odziedziczone) | rozdziela odsetek powrotów **60.4% vs 51.5%, t = +2.21**; monotoniczne (60.0/54.8/50.0); przeżyło kontrolę \|d\|, ablację wolumenową (t = +0.29) i kontrolę mechaniki VWAP | **kandydat na sterowanie ryzykiem** — nie wolno teraz dobierać sposobu użycia na tej samej historii |
| reżim zmienności (H010) | zakres nocny przewiduje amplitudę, nie charakter | wejście do wielkości pozycji |
| dyspersja składników NDX (H016) | nieprzetestowana — brak nosiciela | czeka |

**Reguła:** zmienna reżimowa wolno **wyłączać** handel albo **skalować** pozycję.
Nie wolno jej zamienić w sygnał wejścia bez osobnej karty z własnym mechanizmem.

### 2.4 Zależności prawdziwe statystycznie, ale BEZ PnL

Osobna sekcja istnieje po to, żeby przyszła sesja nie przedstawiła ciekawej
zależności jako strategii.

| Zależność | Dowód | Dlaczego nie jest strategią |
|---|---|---|
| pochodzenie odchylenia → odsetek dotknięć VWAP | t = +2.21, cztery kontrole | **dotknięcie nie jest zwrotem**: zwrot t = +0.69, MFE +0.506% wobec MAE −0.506% — symetria jest sygnaturą błądzenia losowego |
| hedge ES redukuje szum NQ o 63% | sd 0.964% → 0.353% | redukcja szumu ≠ predykcja domknięcia; druga noga kosztuje więcej, niż warta jest przy tym edge'u |
| model nocny wyjaśnia **97.5%** wariancji ruchu NQ (OOS R²) | W011, MAE 8.18‱, kalibracja γ = 1.013 | **model opisujący nie jest modelem prognozującym rezyduum** — składniki wnoszą dużo do modelu (MAE 12.73 → 8.18) i nic do sygnału |
| publikacje wyników odróżniają się od zwykłych dni 32-krotnie | W008 | to warunek konieczny mechanizmu, nie przewaga |
| dryf w poranki po publikacjach wyników: −0.063% | W011, t = −1.39 | nieistotny **i znaleziony po obejrzeniu wyniku** — zapisany jako obserwacja, nie hipoteza |
| środkowy tercyl \|I\|/R w H003: **+13.8 pkt, t = +2.61** | W013 | **wynik wygenerowany przez dane, bez prawa do dalszego testowania na tej historii** — patrz rozdz. 3 i 4 |

---

## 3. Cmentarz rodzin hipotez

Nie pojedyncze karty, lecz **całe rodziny**, których nie wolno otwierać ponownie
bez nowego argumentu mechanizmowego.

### 3.1 Warunkowanie reakcji wielkością impulsu

| | |
|---|---|
| **Przetestowane** | H014 (wielkość rezyduum NQ−βES), H013 (wielkość rezyduum składników), H003 (iloraz impulsu do równowagi) |
| **Dlaczego zawiodło** | za każdym razem warunkowanie **nie poprawiało** wyniku: H014 t −2.28 → −0.66 przy zawężaniu, H013 t −0.79 → −1.42, H003 iloraz (−3.0 pkt) **gorszy** od samej wielkości (+5.1 pkt) |
| **Co musiałoby być nowe** | argument, dlaczego reakcja miałaby zależeć od czegoś innego niż rozmiar — np. od **tożsamości uczestnika** albo struktury księgi, a nie od statystyki ceny |
| **Jakie dane** | `trades` lub MBP; z OHLCV M1 ta rodzina jest wyczerpana |

### 3.2 Prosty dryf nocny

| | |
|---|---|
| **Przetestowane** | H004 → B05 |
| **Dlaczego zawiodło** | SR 0.68 (2019–26) i **0.47** (2021–26), oba poniżej progu 0.8. Co gorsza, W001 wykazało, że odróżnienie dryfu 3.7%/rok od zera wymagałoby **86 lat danych** |
| **Co musiałoby być nowe** | warunek zawężający z zadeklarowanym *f* i uzasadnieniem, skąd koncentracja — przy progu 1/√f |
| **Jakie dane** | te same; problemem jest moc, nie dane |

### 3.3 Sam zakres jako predyktor charakteru ruchu

| | |
|---|---|
| **Przetestowane** | H010 (zakres nocny), H001 (zakres + wolumen) |
| **Dlaczego zawiodło** | zakres przewiduje **amplitudę** bardzo mocno (t = +10.2) i **charakter** wcale (t ≈ 0). Dołożenie wolumenu nic nie zmienia: β₂ = −0.10 po kontroli zakresu |
| **Co musiałoby być nowe** | zmienna opisująca **kto** handlował, nie ile i jak szeroko |
| **Jakie dane** | `trades` z klasyfikacją agresora |

### 3.4 Dotknięcie poziomu jako proxy P&L

| | |
|---|---|
| **Przetestowane** | H002 (dotknięcie VWAP) |
| **Dlaczego zawiodło** | odsetek dotknięć różni się istotnie (t = +2.21) i **nie przekłada się na zwrot** (t = +0.69) przy symetrycznych MFE/MAE |
| **Co musiałoby być nowe** | metryka wyniku od początku w zwrocie, nigdy w zdarzeniu binarnym |
| **Jakie dane** | te same — to błąd metryki, nie danych |

### 3.5 Hedge redukujący szum, ale przegrywający z kosztami

| | |
|---|---|
| **Przetestowane** | H014 |
| **Dlaczego zawiodło** | hedge ES obniża sd o 63% i podnosi SR brutto do 0.85, ale druga noga podwaja koszt (2.20 → 4.40 USD) i zjada **73%** przewagi |
| **Co musiałoby być nowe** | edge brutto większy o **~2.2 pkt MNQ** na transakcję niż w wersji jednonożnej |
| **Jakie dane** | te same; to rachunek, nie brak informacji |

### 3.6 Lead–lag niewidoczny na M1

| | |
|---|---|
| **Przetestowane** | H015 — **zarejestrowana, świadomie niebadana** |
| **Dlaczego zawiodło** | zjawisko rozgrywa się w milisekundach; na barach minutowych każdy wynik byłby artefaktem agregacji, i to artefaktem wyglądającym przekonująco |
| **Co musiałoby być nowe** | nic — potrzebne są dane |
| **Jakie dane** | `trades` / MBP-10, koszt rzędu $24 za miesiąc MNQ |

---

## 4. Rejestr ekspozycji na dane

**To jest najważniejszy rozdział tego dokumentu.**

Licznik prób wynosi 0 i to jest prawda: żaden backtest nie został uruchomiony,
żadna siatka parametrów nie przeszukana. Ale **zero prób to nie zero
ekspozycji.** Projektowanie kart było informowane danymi, a DSR tego nie mierzy,
bo liczy warianty, a nie decyzje o tym, które hipotezy w ogóle napisać.

### 4.1 Skala ekspozycji per zbiór

| Zbiór | Co zostało obejrzane | Status dla drugiej generacji |
|---|---|---|
| MNQ 1m 2019–2026 | zakres nocny, wolumen nocny, efficiency ratio RTH, VWAP i odchylenia, wybicia, poziomy PDH/PDL, luki, MOC, dryf nocny, okna wokół publikacji | **development set** |
| NQ, ES 1m | β NQ~ES, rezyduum, zwroty nocne | **development set** |
| K6 (megacapy, QQQ, SOXX) | zwroty dzienne i nocne, wrażliwości, reakcje po zamknięciu | **development set** |
| Kalendarz EDGAR | 261 publikacji, klasyfikacja rodzajów | metadane — ekspozycja mała |
| Kalendarz makro | 312 zdarzeń | **niemal nieużywany poza W013** |

### 4.2 Idee wygenerowane przez dane — nie wolno ich testować na tej historii

| Idea | Źródło | Status | Co jest dopuszczalne | Co jest wymagane |
|---|---|---|---|---|
| **pochodzenie odchylenia VWAP jako filtr ryzyka** | W010 | hipoteza **wygenerowana przez dane** | implementacja, sanity check | forward albo nowe dane |
| **środkowy tercyl \|I\|/R w H003** | W013 | wynik wygenerowany przez dane; **wybór zwycięskiego kubełka** | nic | nie otwierać |
| dryf poranny po publikacjach wyników (−0.063%) | W011 | obserwacja po fakcie, nieistotna | nic | nowy mechanizm + forward |
| wariant kontynuacyjny H014 | W006 | odwrócenie znaku po zobaczeniu wyniku | nic | nowe ID, nowy mechanizm, forward |
| zakres nocny jako wejście do sizingu | W004 | **nie jest hipotezą kierunkową** | użycie w warstwie ryzyka | zwykła walidacja |

### 4.3 Karty, których projekt był informowany danymi

| Karta | Co ją zainspirowało | Konsekwencja |
|---|---|---|
| **H001** | wprost wnioski W004/W005 (H010 mierzyła amplitudę, nie charakter) | dane wybrały pytanie; wynik i tak negatywny, więc szkoda ograniczona |
| **H003** (obecna postać) | porażka H014 na warunkowaniu wielkością | jw. |
| **H016** | luka po H010 | nieprzetestowana |

**Wniosek:** dla kart, które **przeszły** taki proces i dały wynik pozytywny,
historia 2019–2026 nie byłaby uczciwym OOS. Żadna taka karta nie powstała, więc
dług jest na razie teoretyczny — ale przy drugiej generacji stanie się realny.

---

## 5. Protokół drugiej generacji

Zasady obowiązujące **przed** napisaniem pierwszej nowej karty.

### 5.1 Status danych

> **Dane 2019–2026 są zbiorem deweloperskim, nie zbiorem testowym.**

Wolno na nich: implementować, sprawdzać poprawność techniczną, liczyć rozkłady
opisowe, kalibrować infrastrukturę.

Nie wolno na nich: uznawać wyniku za potwierdzenie karty, której projekt był
informowany wcześniejszymi wynikami z tych samych danych.

### 5.2 Metryka każdej nowej karty

Każda karta drugiej generacji dostaje w nagłówku:

| Pole | Znaczenie |
|---|---|
| `źródło_mechanizmu` | literatura / struktura rynku / obserwacja z danych |
| `wygenerowana_przez_dane` | tak / nie — **jeśli tak, historia jest development only** |
| `data_zamrożenia` | commit, po którym specyfikacji nie wolno zmieniać |
| `pierwszy_dzień_forwardu` | dzień po zamrożeniu |
| `budżet_wariantów` | jak dotąd, ≤ 10 |

### 5.3 Reguły nienaruszalne

1. **Żadnych zmian po rozpoczęciu forwardu.** Zmiana mechanizmu tworzy **nową
   kartę i nowy okres forward**, nie poprawkę.
2. **Zmiana specyfikacji przed pomiarem jest dozwolona i wymaga commitu**
   poprzedzającego wynik — tak jak przy H003 (`ae0f9f8`, `d03337c`).
3. **Kryterium falsyfikacji deklarowane z góry.** H003 zginęła na własnym
   kryterium monotoniczności, które inaczej dałoby się obejść wyborem środkowego
   tercyla.
4. **Metryka wyniku zawsze w zwrocie**, nigdy w zdarzeniu binarnym (W010).
5. **Kontrola ciągła, nie tylko kubełkowa**, gdy karta twierdzi „X niesie
   informację przy kontrolowanym Y" (W010).
6. **Model użyty do werdyktu musi być zwalidowany OOS** tak samo starannie, jak
   gdyby miał kartę potwierdzić (W011).

### 5.4 Czego nie robić teraz

- Nie otwierać karty na środkowy tercyl H003.
- Nie szukać „prawie działających" podzbiorów w odrzuconych kartach.
- Nie zmieniać progów kart odrzuconych.
- Nie uruchamiać automatycznego przeszukiwania cech.
- Nie projektować dwudziestu nowych hipotez z tych samych raportów.
- **Nie traktować 0 prób jako 0 ekspozycji.**

---

## 6. Co pierwsza generacja faktycznie dała

Uczciwy bilans, bez pocieszania się.

**Nie dała strategii.** Szesnaście kart, zero kandydatów, zero prób wydanych na
backtesty, bo żadna karta nie doszła do etapu, na którym backtest miałby sens.

**Dała sprawny aparat i to jest realny majątek.** Silnik udowodniony na realnych
danych (bramka 5.6), 430 testów, pełna warstwa walidacyjna (DSR, CPCV, PBO, SPA,
bootstrap blokowy), trzy kalendarze zdarzeń z darmowych źródeł urzędowych.

**Dała listę pułapek, z których każda kosztowałaby fałszywy wynik:**

| Pułapka | Gdzie | Skutek, gdyby przeszła |
|---|---|---|
| przepełnienie Int8 w polars przy `hour * 60` | W009 | wszystkie filtry godzinowe na śmieciach, bez wyjątku |
| `acceptanceDateTime` z sufiksem `Z`, które nie jest UTC | W008 | 29 publikacji MSFT przesuniętych w środek sesji |
| `startswith` łapiące „Employment Situation **of Veterans**" | kalendarz makro | 7 fałszywych zdarzeń o złej godzinie |
| konferencje prasowe przy awaryjnych cięciach FOMC | kalendarz makro | 53 z 60 posiedzeń w złym kuble |
| cena wyjścia sprzed sygnału przy wybiciach po 10:30 | W010 | przekonujące, ale nieważne liczby |
| σ_VWAP liczona wokół VWAP z własnego momentu | W010 | zła kwalifikacja zdarzeń i zły udział odziedziczony |
| ziarno bootstrapu z `hash()` randomizowanego per proces | W001 | nieodtwarzalny raport |
| mypy sprawdzający zero plików przez przypięty `python_version` | CI | trzy commity czerwonego CI przy zielonych testach lokalnych |
| próg 300 barów RTH odrzucający dni skrócone | kalendarz makro | utrata handlowalnych publikacji NFP |

**Dała bazową stopę, którą trzeba znać przed drugą generacją:** szesnaście kart
zaprojektowanych w jednym podejściu, w dużej mierze z literatury, dało zero
kandydatów. Następna generacja startuje z tą wiedzą, a nie z optymizmem.

---

## 7. Kolejność dalszych prac

Ustalona po syntezie, przed jakąkolwiek nową kartą.

| # | Etap | Status |
|---|---|---|
| 1 | **Synteza badawcza W001–W013** | ten dokument ✅ |
| 2 | Mapa architektury i zależności | — |
| 3 | Golden outputs najważniejszych raportów + hashe | — |
| 4 | Klasyfikacja krytyczności modułów (czerwone / pomarańczowe / zielone) | — |
| 5 | Ostrożny refaktor | — |
| 6 | Pełna regresja wobec golden outputs | — |
| 7 | Dokumentacja właściciela | — |
| 8 | Tag stabilnej wersji `engine-v1.0` | — |
| 9 | **Dopiero wtedy: nowe karty** | — |

**Refaktor przed zapisaniem golden outputs jest zabroniony.** Przy systemie tej
wielkości porządki potrafią stworzyć błąd trudniejszy do zauważenia niż
duplikacja, którą usuwają.

---

# Epilog techniczny — 03.08.2026

**Wnioski badawcze powyżej pozostają bez zmian.** Ta sekcja odnotowuje wyłącznie
domknięcie etapu technicznego, który miał je zabezpieczyć.

## Status kolejności prac z sekcji 7

| # | Etap | Status |
|---|---|---|
| 1 | Synteza badawcza W001–W013 | ✅ |
| 2 | Mapa architektury i zależności | ✅ `docs/ARCHITEKTURA.md` |
| 3 | Golden outputs + hashe | ✅ `golden/baseline.json`, odtworzony trzykrotnie bajt w bajt |
| 4 | Klasyfikacja krytyczności modułów | ✅ trójstopniowa, w mapie architektury |
| 5 | Ostrożny refaktor | ✅ **minimalny** — R1 i R2, reszta świadomie odrzucona |
| 6 | Pełna regresja wobec golden outputs | ✅ `--sprawdz` po każdej zmianie, `golden/ZMIANY.md` v1–v4 |
| 7 | Dokumentacja właściciela | ✅ `docs/PODRECZNIK.md`, `docs/OD_DANYCH_DO_PNL.md`, `docs/ZALOZENIA.md` |
| 8 | Tag stabilnej wersji | ⚠ **nie utworzony zdalnie** — patrz niżej |
| 9 | Nowe karty | ⏸ **nie rozpoczęte** |

## Refaktor okazał się mniejszy, niż zakładała sekcja 7

Audyt kodu znalazł **79 linii martwych i cztery ogniska duplikacji w 11 817
liniach — 0,7%**. Trzy z czterech symboli „martwych" były brakiem wykonania
specyfikacji, nie śmieciami. Duży refaktor byłby więc sztuką dla sztuki przy
niezerowym ryzyku w kodzie krytycznym finansowo, i został odrzucony.

Wykonano wyłącznie: **R1** (naprawa znaku w SPA), **R2** (podpięcie kontroli
ciągłości), przeetykietowanie `verify_continuity` na diagnostykę oraz
empiryczne domknięcie założenia A3.

## Najważniejsze ustalenie techniczne

Golden baseline wykrył błąd, którego nie znalazło 233 testów: ścieżka `arch`
w `validation/spa.py` dostawała zwroty tam, gdzie biblioteka oczekuje strat.
Testowana była hipoteza przeciwna do zamierzonej.

**Powód, dla którego przeżył:** wszystkie testy tego modułu wołały funkcję
z `force_fallback=True`. Ścieżka domyślna — jedyna działająca produkcyjnie —
nie była testowana w ogóle. To dopisuje do listy pułapek z sekcji o traps
kategorię, której tam nie było: **pokrycie testami może być pozorne, jeśli testy
systematycznie omijają ścieżkę produkcyjną.**

Wpływ na wnioski W001–W013: **żaden.** SPA nie było użyte, licznik prób 0.

## Punkty odniesienia

Zdalnego tagu nie udało się utworzyć — proxy git odmawia pushu tagów (403).
Kanonicznymi identyfikatorami są SHA commitów:

| Punkt | SHA | Zawartość |
|---|---|---|
| **Baseline Gen1** | `a1aba1c0c47fce2e958374e2614e5744b6882027` | ostatnia wersja przed jakimkolwiek refaktorem; `hash_wynikow = 6a082749…` |
| **Stabilna po R1/R2** | `b8572a5ac7c482ab1a243a34b019f11c9694a4eb` | minimalny refaktor zamknięty |

SHA commitu jest jednoznaczny niezależnie od tego, czy tag `gen1-baseline`
istnieje zdalnie.

## Co pozostaje ważne

Licznik prób **0**. Osiem werdyktów odrzucenia bez zmian. Cmentarz rodzin
z sekcji 3 obowiązuje. Protokół drugiej generacji z sekcji 5 obowiązuje.

Kolejny krok to **`docs/GEN2_BRIEF.md`** — dokument projektowy, nie pomiar.
Żadnych nowych kart przed wyborem mechanizmu.
