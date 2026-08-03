# Rejestr hipotez — Projekt G

Pamięć instytucjonalna projektu. **Każda sesja agenta zaczyna od przeczytania tego pliku.**

Rejestr pełni trzy funkcje: (1) zapewnia ciągłość między sesjami, (2) jest jawnym licznikiem prób
wchodzącym do DSR, (3) akumuluje wnioski przekrojowe zasilające projektowanie kolejnych partii.

Specyfikacja procesu: `docs/PLAN.pdf` rozdz. 8. Test oryginalności: rozdz. 8.4.

---

## Stany hipotezy

```
IDEA → TESTING → REJECTED(faza)
              ↘ CANDIDATE → [bramka Tier 1] → PROMISING → (forward paper) → CERTIFIED
                                            ↘ REJECTED(gate)
```

`REJECTED` jest trwały. Hipoteza może wrócić wyłącznie jako **nowa karta z nowym ID**
i jawnym odwołaniem do poprzedniczki (np. „H017, wariant H003 z wnioskiem W-12").

---

## Benchmarki — B01–B04

**Nie są kandydatami na oryginalną strategię.** Uruchamiane raz, z parametrami wprost z
literatury, bez optymalizacji. Służą jako grupa kontrolna w teście przyrostowym (8.4 krok 3).
**Nie zużywają globalnego licznika prób** — to bezpośredni zysk dla DSR wszystkich kandydatów.

| ID | Karta | Publiczny odpowiednik | Status | Wynik |
|----|-------|----------------------|--------|-------|
| B01 | Gap otwarcia i domknięcie | Gap-fill (klasyka indeksowa) | **ZMIERZONY** | N=1551, netto −5 786 USD, SR −0.25, PF 0.95 |
| B02 | Cykl kontrakcja–ekspansja | NR7 i pochodne, Crabel ~1990 | **ZMIERZONY** | N=279, netto **+1 611 USD**, SR +0.13, PF 1.06 |
| B03 | Asymetria piątek→poniedziałek | Weekend effect, Cross 1973 / French 1980 | **ZMIERZONY** | N=355, netto −16 098 USD, SR −0.73, PF 0.74 |
| B04 | Mechanika zamknięcia / proxy MOC | Momentum wewnątrzdzienne, Gao i in. JFE 2018 | **ZMIERZONY** | N=1799, netto −10 658 USD, SR −0.91, PF 0.84 |
| B05 | **Dryf nocny, bezwarunkowo** | Cooper–Cliff–Gulen 2008 | **ZMIERZONY** | SR 0.68 (2019–26) / **0.47** (2021–26) — poniżej progu 0.8. Zdegradowana z H004 po W001. |

---

## Karty przeformułowane — H001–H004

Mechanizmy warte ratowania, pod warunkiem przejścia kroków 1–2 testu oryginalności.
**Reguła samoczyszcząca:** jeśli przy pisaniu pełnej karty różnicy mechanizmu nie da się
obronić, karta schodzi do benchmarków — decyzja zapada na papierze, zanim spali próbę.

| ID | Karta | Benchmark | Wymagana różnica mechanizmu | Status | Warianty |
|----|-------|-----------|----------------------------|--------|----------|
| H001 | Kompresja nocna: przyczyna, nie fakt | B02 + ORB | Wolumen przy zadanym zakresie | **[REJECTED (pre-flight)](H001.md)** → B02 | **0/8** |
| H002 | Powrót do VWAP: gdzie odchylenie powstało | „lunch VWAP fade" | Moment powstania odchylenia, nie jego wielkość | **[REJECTED (pre-flight)](H002.md)** | **0/6** |
| H003 | Reakcja na publikację: impuls wobec równowagi | „fade the news" | Iloraz impulsu do zakresu przedpublikacyjnego | **[REJECTED (pre-flight)](H003.md)** | **0/6** |
| H004 | Dryf nocny — czy jeszcze istnieje | Cooper–Cliff–Gulen 2008 | **Blokada zdjęta przez W001.** Postać bezwarunkowa → B05. Postać warunkowa wymaga deklaracji *f* i progu **przed** testem | IDEA (warunkowa) | 0/4 |

### Partia 3 — odrzucona w pre-flight (W010, W013)

Raporty: [`W010`](../reports/W010_partia3_preflight.md) (H001, H002) i [`W013`](../reports/W013_H003_preflight.md) (H003).
**Zużyte próby: 0 z budżetu 20.**

| Karta | Powód odrzucenia |
|-------|------------------|
| **H001** | Przesłanka fałszywa. Po kontroli dokładnego zakresu wolumen nie wnosi nic o charakterze sesji (β₂, t = **−0.10**); różnica efficiency ratio między dwoma kompresjami t = +0.91. Rozstrzygnęła regresja ciągła, dodana po przeglądzie kodu — podział kubełkowy dałoby się tłumaczyć małą grupą. |
| **H002** | **Odrzucona własnym falsyfikatorem 2** („działa tylko jeden koniec skali"). Koniec odziedziczony nie kontynuuje (t = −0.16). Przy tym karta przeszła cztery kontrole, w tym ablację, której się bała: pochodzenie odchylenia rozdziela powroty (t = +2.21), a prosty wolumen nie (t = +0.29). Zabił ją brak przełożenia na zwrot: t = +0.69 przy **symetrycznych MFE/MAE** (+0.506% / −0.506%). |
| **H003** | Pięć z sześciu przewidywań zawiedzionych (W013, N = 232). **Rozstrzygająca ablacja: iloraz |I|/R daje −3.0 pkt, sama wielkość |I| +5.1 pkt — zmienna karty jest gorsza od tej, którą miała poprawić.** Niemonotonicznie (środkowy tercyl +13.8 pkt, t = +2.61 — pułapka, którą łapie kryterium zadeklarowane z góry). Żaden typ nie niesie efektu, znak odwraca się między 2023 a 2024, netto −5.0 pkt. **Tym razem mocy nie brakuje:** do wykrycia efektu 20 pkt potrzeba 40 obserwacji, mamy 111. |

**H002 była najbliżej ze wszystkich dotąd badanych kart** i to jest informacja
sama w sobie: przeszła więcej kontroli niż jakakolwiek wcześniejsza, a i tak nie
miała przewagi handlowej. Pochodzenie odchylenia zostaje jako kandydat na wejście
do **wielkości pozycji** lub warstwę reżimową — tak jak H010 po W004.

**W skrypcie W010 znaleziono sześć usterek przed pierwszym uruchomieniem**, w tym
błąd czasowy dający cenę wyjścia sprzed sygnału i błędnie liczoną σ_VWAP. Żadna
nie rzucałaby wyjątku. Lista w docstringu modułu; σ_VWAP objęta testem
regresyjnym wobec kanonicznej `engine.features.vwap_sigma`.

### H004 — test wstępny WYKONANY (W001, 01.08.2026)

Pełny raport: [`reports/W001_overnight_drift.md`](../reports/W001_overnight_drift.md).
Odtworzenie: `python3 research/W001_overnight_drift.py`. **Zero zużytych prób.**

**Wynik nie jest tym, którego oczekiwały obie strony sporu.** Teza NY Fed o wygaśnięciu
dryfu jest na naszych danych **nierozstrzygalna, a nie fałszywa lub prawdziwa**: przedział
ufności dla dryfu nocnego MNQ 2021–2026 wynosi **[−4.4%, +16.4%] rocznie**. Zarówno 0%,
jak i 3.7% leży wewnątrz. Odróżnienie tych dwóch wartości przy mocy 80% wymagałoby
**86 lat danych**.

Rozstrzygające okazało się pytanie postawione inaczej — nie „czy efekt istnieje", lecz
„czy przechodzi bramkę projektu":

| Okres | Dni | Sharpe nocny (przed kosztami) | Próg 0.8 |
|---|---|---|---|
| 2019–2026 | 1863 | 0.68 | nie przechodzi |
| 2021–2026 | 1438 | **0.47** | nie przechodzi |

Spójne na trzech instrumentach (MNQ, NQ, ES) — nie jest to artefakt jednego zbioru.

**Decyzja:** postać bezwarunkowa → **B05** (benchmark, nie zużywa prób). Postać warunkowa
pozostaje otwarta, ale przed pierwszą próbą karta **musi zadeklarować**: (1) jaki ułamek
nocy *f* wybiera jej warunek, (2) jaki zwrot na noc czynną zakłada, (3) dlaczego mechanizm
miałby dawać taką koncentrację. Progi w W002. Bez tego karta schodzi do benchmarków regułą
samoczyszczącą.

---

## Kandydaci — główny front badań

| ID | Karta | Klasa | Priorytet | Status | Warianty |
|----|-------|-------|-----------|--------|----------|
| H011 | Sekwencja Azja→Europa jako predyktor RTH | K1 | ~~najwyższy~~ | **REJECTED (pre-flight)** | **0/6** |
| H005 | Mikrostruktura kolejnych testów poziomu | K5 | ~~wysoki~~ | **REJECTED (pre-flight)** | **0/6** |
| H010 | Zmienność zrealizowana wobec oczekiwanej | K3 × K1 | ~~wysoki~~ | **REJECTED w tej roli (pre-flight)** | **0/6** |
| H013 | Rezydualny repricing po wynikach megacapów | K6 × K4 | ~~najwyższy~~ | **[REJECTED (pre-flight)](H013.md)** | **0/8** |
| H014 | Dywergencja NQ–ES wokół szoków stóp | K6 × K4 | — | **[REJECTED (pre-flight)](H014.md)** | **0/6** |
| H016 | Reżim dyspersji składników NDX | K6 × K3 | **straciła nosiciela** — czeka, zgodnie z sekcją 7 karty | [IDEA warunkowa](H016.md) | 0/6 |

### Partia 2 — odrzucona w pre-flight (W006, W009)

| Karta | Powód odrzucenia |
|-------|------------------|
| **H014** | Rezyduum NQ−βES kontynuuje zamiast wracać, a warunkowanie na wielkości szoku **pogarsza** wynik (t = −2.28 na wszystkich dniach wobec −0.66 w górnym decylu). Wariant kontynuacyjny miał Sharpe brutto 0.85, ale koszty dwóch nóg zjadały 73% przewagi. |
| **H013** | Pięć z sześciu przewidywań mechanizmu zawiedzionych (W009). Warunkowanie na wielkości rezyduum pogarsza wynik, znak efektu odwraca się między 2022 a 2023, a człon składników nie poprawia wyniku handlowego wobec samej luki nocnej. Potwierdzone audytem zamykającym (W011, W012) na próbie zgodnej z pierwotną definicją karty. |

**Zaplanowany katalog K6 wyczerpany.** Obie karty niosące własny P&L odpadły
w pre-flight, H016 nie ma czego filtrować, H015 pozostaje niebadalne bez danych
`trades`/MBP. **Łączny koszt: $7.82 i zero zużytych prób z budżetu 20.**

Sformułowanie jest celowo węższe niż „klasa K6 wyczerpana": wyczerpaliśmy karty,
które **zaplanowaliśmy**, a nie przestrzeń mechanizmów transmisji międzyrynkowej.
Warstwa danych K6 zostaje w repo i jest opłacona — nowa karta tej klasy nie
wymagałaby już zakupu.

### Audyt zamykający H013 (W011, W012)

Wykonany na żądanie właściciela projektu **przed** zamknięciem karty, zero prób.

- **W011** wykazał, że W007 walidował **inny model** niż ten, którym odrzucono
  kartę. Model nocny zwalidowany osobno wypada lepiej niż dzienny (OOS R² 0.9753
  wobec 0.9436, MAE 8.18‱ wobec 26.31‱, kalibracja γ = 1.013). Rezyduum użyte
  do werdyktu jest więc sensowne. Znaleziono przy tym **usterkę pre-flightu**:
  model jest obciążony w sesje zdarzeń (+3.05‱), przez co asymetria stron
  106/79 była artefaktem — po korekcie 93/92.
- **W012** powtórzył rachunek na próbie zgodnej z pierwotną definicją karty
  (kwartalne wyniki, AMC, N = 157), rozdzielonej z **treści komunikatów**, nie
  z reakcji ceny. Kierunek wniosków nie zmienił się w żadnym przekroju;
  najczystszy mechanizmowo (noce z jedną publikacją) wypadł najgorzej.

Werdykt osłabiony językowo i to jest poprawka merytoryczna, nie kosmetyczna:
**nie twierdzimy, że udowodniono brak edge'u** — przy tej próbie nie sposób.
Twierdzimy, że układ wyników jest niezgodny z zadeklarowanymi przewidywaniami,
i to wystarcza, by nie wydawać ośmiu prób.

### Partia 1 — odrzucona w pre-flight (W004, 01.08.2026)

Pełny raport: [`reports/W004_partia1_preflight.md`](../reports/W004_partia1_preflight.md).
**Zużyte próby: 0 z budżetu 18.** Trzy karty zginęły, zanim kosztowały choć jedną próbę.

| Karta | Powód odrzucenia |
|-------|------------------|
| **H011** | Oba przewidywania mechanizmu zawodzą (kontrast kierunkowy t = −0.44; efficiency ratio t = −1.34, ze znakiem **przeciwnym** do przewidywanego). Karta o najwyższym priorytecie w katalogu nie ma przesłanki. |
| **H010** | Efekt jest — i to najsilniejszy w całym projekcie (szeroka noc → szerszy zakres RTH, **t = +10.2**) — ale dotyczy **amplitudy, nie charakteru**. Efficiency ratio nie różni się między reżimami (t ≈ 0). Karta zakładała filtr trend/piłowanie; tego dane nie dają. Zostaje jako wejście do **wielkości pozycji**, nie jako filtr kierunkowy. |
| **H005** | Sygnał PDH przy k ≥ 4: +5.07 pkt, t = +2.98, przeszedł kontrolę pory dnia (nadwyżka t = +3.11), zmianę czterech parametrów i podział próbki na połowy. **Upadł na trzech kontrolach z mechanizmu:** brak symetrii (PDL t = +0.89), brak monotoniczności w k (skok przy 4, spadek przy 5), koncentracja czasowa (**rok 2026, niepełny, daje 52% wyniku**; 3 z 8 lat ujemne). |

**Skład partii 1 do przeprojektowania.** Trzy karty z sześciu kandydatów odpadły
bez kosztu. Karty klasy K6 rozstrzygnięte osobno — patrz niżej.

---

### H015 — zarejestrowana, niebadalna

| ID | Karta | Powód wstrzymania |
|----|-------|-------------------|
| H015 | Price discovery NQ→MNQ (lead-lag) | Zjawisko rozgrywa się w milisekundach. Na barach M1 **każdy wynik byłby artefaktem agregacji** — i to artefaktem wyglądającym przekonująco. Wraca, gdy pozyskamy dane `trades`/MBP. **Nie zużywa ani jednej próby.** |

Karta jest zapisana celowo: jawne odnotowanie „wiemy o tym mechanizmie i wiemy, dlaczego go nie
badamy" chroni przyszłe iteracje przed przypadkowym wejściem w tę pułapkę.

---

## Kolejność partii

| Partia | Skład | Uzasadnienie |
|--------|-------|--------------|
| **0** ✅ | ~~Test dryfu nocnego~~ W001 + ~~benchmarki B01–B04~~ | **WYKONANA 01.08.2026.** W001 rozstrzygnął H004; B01–B04 zmierzone (`reports/B00_benchmarks.md`, liczby maszynowe w `reports/benchmarks.json`). Zero zużytych prób. |
| **1** ✅ | ~~H011, H005, H010~~ | **ODRZUCONE W PRE-FLIGHT (W004).** Zero zużytych prób z budżetu 18. Żadna z trzech kart nie miała przesłanki mierzalnej w danych. |
| **2** ✅ | ~~H014~~ (W006) · ~~H013~~ (W009) · H016 bez nosiciela | **ODRZUCONA W PRE-FLIGHT.** Zero zużytych prób z budżetu 20. Koszt danych $7.82. Klasa K6 wyczerpana w obecnym zakresie danych. |
| **3** ✅ | ~~H001~~ ~~H002~~ (W010) · ~~H003~~ (W013) | **Wszystkie trzy odrzucone w pre-flight**, zero prób z budżetu 20. Kalendarz makro zbudowany z darmowych źródeł urzędowych i zostaje jako infrastruktura. |

---

## ORYGINALNY KATALOG ZAMKNIĘTY — 02.08.2026

**Wszystkie szesnaście kart rozstrzygnięte. Licznik prób: 0. Wydane: $7.82.**

| Los | Karty |
|---|---|
| Odrzucone w pre-flight | H001, H002, H003, H005, H010, H011, H013, H014 |
| Zdegradowane do benchmarków | H004 → B05, H006 → B01, H007 → B02, H008 → B03, H012 → B04 |
| Warunkowe, bez nosiciela lub bez danych | H009 → zastąpiona przez H013 · H015 (wymaga `trades`/MBP) · H016 (straciła nosiciela) |

**Żadna karta nie zużyła próby.** Cały katalog padł na pre-flightach kosztujących
czas i osiem dolarów, przy budżecie 20 prób na partię i limicie 10 wariantów
na kartę.

### Czego to NIE znaczy

Nie znaczy, że na MNQ nie ma przewagi. Znaczy, że **szesnaście konkretnych
mechanizmów, wymyślonych w jednym podejściu i w dużej mierze zainspirowanych
literaturą, nie miało mierzalnej przesłanki** na siedmiu latach danych minutowych.

### Czego to wymaga przed następną generacją kart

**Aparat działa — i to jest realny dorobek.** Zabił szesnaście kart bez wydania
próby, a przy okazji wyłapał: przepełnienie Int8 w polars, niejednolitą strefę
w `acceptanceDateTime` SEC, `startswith` łapiące „Employment Situation of
Veterans", konferencje prasowe przy awaryjnych cięciach FOMC, błąd czasowy
dający cenę wyjścia sprzed sygnału i błędnie liczoną σ_VWAP.

Ale **licznik prób równy 0 nie znaczy, że dane są nietknięte.** Projekt kart był
informowany danymi: H001 powstała wprost z wniosków W004/W005, H003 z porażki
H014. To jest selekcja, której DSR nie mierzy, bo DSR liczy warianty, a nie
decyzje o tym, które hipotezy w ogóle napisać.

**Konsekwencja dla następnej generacji: prawdziwy forward albo lockbox jest
konieczny, nie ostrożnościowy.** Dane historyczne posłużyły już do wyboru
kierunków badań i nie są dla nowych kart czystym testem OOS.

### Pełna synteza: [`docs/SYNTEZA_GEN1.md`](../docs/SYNTEZA_GEN1.md)

Dokument zamykający pierwszą generację. Zawiera mapę wszystkich szesnastu kart
z rozróżnieniem sześciu kategorii porażki, cztery klasy odkrytych zmiennych
(amplituda / kierunek / reżim / zależności bez PnL), **cmentarz sześciu rodzin
hipotez**, **rejestr ekspozycji na dane** i **protokół drugiej generacji**.

Dwie rzeczy z niego, które obowiązują od zaraz:

1. **Dane 2019–2026 są zbiorem deweloperskim, nie testowym.** Karta, której
   projekt był informowany wcześniejszymi wynikami z tych danych, wymaga
   forwardu do potwierdzenia.
2. **Nie znaleziono ani jednej zmiennej przewidującej KIERUNEK**, która
   spełnia bramkę. Znaleziono kilka przewidujących amplitudę i reżim — i nie
   wolno ich zamieniać w sygnał kierunkowy przez zmianę nazwy.

---

## Wnioski przekrojowe (W-xx)

Fakty o rynku i o procesie odkryte przy okazji badań. Zasilają projektowanie kolejnych partii.

| ID | Wniosek | Źródło |
|----|---------|--------|
| **W010** | **Podział kubełkowy nie zastępuje kontroli ciągłej.** H001 dzieliła dolny tercyl zakresu medianą wolumenu i pytała, czy grupy różnią się charakterem sesji. Wewnątrz tercyla nadal są różnice zakresu, więc taki podział nie odpowiada na pytanie karty. Regresja `ER ~ percentyl_zakresu + percentyl_wolumenu` liczona wewnątrz kompresji dała jednoznaczne **t = −0.10** dla wolumenu. **Reguła: gdy karta twierdzi „X niesie informację przy kontrolowanym Y", pre-flight musi zawierać test, który Y kontroluje ciągle, a nie tylko kubełkiem.** Drugi wniosek z tej samej partii: **odsetek zdarzeń nie jest zwrotem** — H002 miała separację odsetka powrotów przeżywającą cztery kontrole i zerowy zwrot przy symetrycznych MFE/MAE. | W010 |
| **W011** | **Model, którym odrzucamy kartę, musi być zwalidowany tak samo starannie jak model, którym byśmy ją przyjęli.** W007 walidował QQQ na zwrotach dziennych; W009 odrzucił H013 rezyduum z modelu NQ na zwrotach nocnych z ES i SOXX. To dwa różne estymatory, a jedyną podaną liczbą o jakości drugiego była statystyka **in-sample**. Osobna walidacja pokazała, że model nocny jest dobry (OOS R² 0.9753, γ = 1.013) — ale **wykryła obciążenie +3.05‱ w sesje zdarzeń**, przez które jedno z sześciu przewidywań zawiodło z powodu wewnętrznego dla modelu, nie własności rynku. Reguła: **przed zamknięciem karty waliduj dokładnie ten obiekt, który dał werdykt** — importowany, nie odtworzony. | W011 |
| **W012** | **Zbiór zdarzeń zbudowany z rejestru wymaga jeszcze rozdzielenia RODZAJÓW zdarzeń.** Kalendarz EDGAR dał 261 poprawnych publikacji 8-K item 2.02, ale karta H013 była zaprojektowana na kwartalne wyniki po zamknięciu — a w zbiorze były też 29 komunikatów Tesli o produkcji i dostawach. Rozdzielenie **z treści komunikatów** (nigdy z reakcji ceny) jest tanie i daje kontrolę wewnętrzną: każda spółka wyszła po 28–30 raportów, TSLA rozpadła się na dokładnie 29 i 29. **Przekroje próbki nie są wariantami strategii i nie zużywają prób** — nie zmieniają reguły wejścia, tylko odpowiedź na pytanie, które zdarzenia są zdarzeniami tej karty. | W012 |
| **W009** | **Odwrócenie znaku efektu w środku próbki jest mocniejszym dowodem braku mechanizmu niż koncentracja w jednym roku.** H005 zginęło na tym, że jeden rok dawał 52% wyniku. H013 zginęło na czymś gorszym: lata 2019–2022 dają średnio ujemny wynik, 2023–2026 dodatni — **efekt nie jest skoncentrowany, tylko zmienia kierunek**. Karta z koncentracją może mieć mechanizm działający w jednym reżimie; karta ze zmianą znaku nie ma mechanizmu wcale. Wniosek procesowy: **rozkład wyniku po latach raportujemy zawsze ze znakiem i udziałem, nie samą wartością bezwzględną** — inaczej te dwa różne tryby porażki są nieodróżnialne. Dodatkowo potwierdzone po raz drugi (po H014): **warunkowanie, które pogarsza wynik, obala przesłankę niezależnie od znaku efektu**. | W009 |
| **W008** | **Etykiety zdarzeń biorą się z rejestru, nigdy z reakcji rynku — i sam pomiar reakcji też trzeba zweryfikować.** Kalendarz z SEC EDGAR (8-K item 2.02, 261 publikacji) definiuje próbę; detektor służy wyłącznie kontroli. Kontrola potwierdziła przesłankę H013: mediana ruchu po zamknięciu w dni publikacji **3.56% wobec 0.11%** w pozostałe (32×), obrót **96× tła**, zero publikacji z pustym oknem danych. Ujawniła też dwie pułapki pomiarowe: (1) pole `acceptanceDateTime` z API bywa czasem ET z sufiksem `Z` — 29 publikacji MSFT trafiłoby w środek sesji; (2) **pojedynczy odczyt o 17:00 ma przeciwny znak niż stan przed otwarciem w 16% zdarzeń**, bo kurs potrafi przejść całą amplitudę reakcji i wrócić. Wniosek procesowy: **definicja okna pomiaru jest częścią mechanizmu, nie detalem implementacyjnym**, i musi być rozstrzygnięta kryterium pomiarowym przed backtestem, nigdy po zobaczeniu P&L. | W008 |
| **W007** | **R² in-sample nie jest walidacją i nie wolno go publikować jako dowodu.** Model wrażliwości opublikowałem z tabelą R² 0.887–0.982 liczoną na tym samym oknie, na którym dopasowano współczynniki — przy ośmiu regresorach taka tabela wychodzi dobrze zawsze. Pomiar OOS (predykcja dnia t z okna do t−1, 1692 dni) daje R² **0.9436** wobec **0.9209** dla modelu naiwnego: przewaga realna, ale **skromna**. Przy okazji obalone własne twierdzenie, że ridge rozwiązuje współliniowość — OLS daje wynik identyczny do czterech miejsc po przecinku. **Reguła procesowa: żadna liczba nie trafia do karty ani do docstringa, dopóki nie została policzona out-of-sample przez skrypt w `research/`.** | W007 |
| **W001** | **Poziomy bezwarunkowe są poza zasięgiem tego projektu.** Przy dziennym odchyleniu zwrotu nocnego ~0.75% odróżnienie dryfu 3.7%/rok od zera wymaga ~86 lat danych. Każda karta, której teza brzmi „efekt X o sile kilku procent rocznie istnieje / wygasł", jest z góry nierozstrzygalna — **nie wolno na nią wydawać próby**. Dotyczy to też cudzych twierdzeń tej klasy: nie opieramy na nich decyzji projektowych, niezależnie od źródła. | W001 |
| **W006** | **Redukcja szumu przez hedge nie jest darmowa i przy małym edge'u jest stratna.** Druga noga podwaja koszt round-turn (2.20 → 4.40 USD). Zmierzone na H014: hedge ES obniża sd NQ o **63%**, podnosząc Sharpe brutto do 0.85 — ale koszty dwóch nóg zjadają **73%** przewagi, netto SR spada do **0.23**, a pod stress-testem ×2 jest **ujemne**. Próg opłacalności hedge'u przy naszych kosztach: ok. **2.2 pkt MNQ** przewagi brutto na transakcję ponad wersję jednonożną. Karta hedgowana musi to wykazać, zanim policzy Sharpe'a. | W006 |
| **W005** | **Silny efekt to nie to samo co użyteczny efekt.** H010 dała najmocniejszy pojedynczy wynik projektu (t > 10) i została odrzucona, bo mierzyła **amplitudę** tam, gdzie karta potrzebowała **kierunku**. Przed uruchomieniem karty pytamy nie tylko „czy efekt istnieje", ale „czy istnieje w zmiennej, której karta faktycznie używa". | W004 |
| **W004** | **Kontrole wyprowadzone z mechanizmu odrzucają więcej i wcześniej niż kontrole statystyczne.** Sygnał H005 przeszedł kontrolę pozorności, zmianę czterech parametrów i podział próbki — a upadł na symetrii, monotoniczności i stabilności rocznej, czyli na trzech przewidywaniach, które robi jego własny mechanizm. **Kolejność kontroli: najpierw mechanizm, potem statystyka.** Dodatkowo: pre-flight rozkładów kosztujący 0 prób uratował cały budżet 18 prób partii 1. | W004 |
| **W003** | **Metryki w R są niezdefiniowane bez stopa, a koncentracja bez zysku.** Strategia z wyjściem czasowym ma `r_multiple = 0` dla każdej transakcji → PF, win rate, expectancy i SQN wychodziły **zerami wyglądającymi na pomiar**. Tak samo `top5_concentration` zwracała 0.0 dla strategii stratnej, co czytało się jako „koncentracja wzorowa". Oba naprawione na NaN + flagę `r_metrics_valid`. **Wniosek procesowy: metryka, która przy zdegenerowanym wejściu zwraca liczbę zamiast błędu, jest pułapką** — przy przeglądzie każdej nowej metryki pytamy najpierw, co robi na wejściu bez sensu. | B00 |
| **W002** | **Warunkowanie ma cenę rosnącą jak 1/√f.** Sharpe liczymy po wszystkich dniach (rozdz. 6.3), więc strategia handlująca ułamek *f* okazji musi mieć na każdej z nich edge większy o czynnik 1/√f. Progi dla dryfu nocnego przy DSR ≥ 0.95 i 4 wariantach (SR ≥ 1.13): połowa nocy **3.6×**, kwintyl **5.6×**, decyl **8.0×** obecnej przewagi bezwarunkowej. **Każda karta warunkowa deklaruje *f* z góry** i uzasadnia, skąd weźmie koncentrację. Warunek odsiewający 90% okazji „bo tak wygląda lepiej" niemal na pewno nie przejdzie bramki — i można to stwierdzić **przed** testem. | W001 |

---

## Reguły trwałe projektu (R1–R3)

Zapisane 02.08.2026 na podstawie kontekstu właściciela projektu: ograniczony budżet,
docelowo konto fundowane 200 000 USD z limitem 5% dziennie i 10% całkowicie.
**Reguły obowiązują niezależnie od wyniku którejkolwiek karty.**

| # | Reguła |
|---|--------|
| **R1** | **Każde nowe płatne źródło danych lub narzędzie wymaga czterech rzeczy przed zakupem:** uzasadnienia (co konkretnie odblokowuje), oszacowania kosztu, sprawdzenia darmowej alternatywy i **zgody właściciela**. Formalizuje procedurę zastosowaną przy zakupie warstwy K6 za $7.82. |
| **R2** | **Zakaz strojenia pod wynik docelowy.** Żadna zmiana specyfikacji, parametru ani reguły wejścia po zobaczeniu P&L, jeśli motywem jest zbliżenie się do zakładanego wyniku miesięcznego. Deklarowane 1–2%/mies. jest potrzebą finansową właściciela, **nie targetem strategii**. Jeśli przewagi nie ma, projekt ma to wykazać, a nie dopasować. Wzmacnia W002 i W004. |
| **R3** | **Limity firmowe 5%/10% są barierami awaryjnymi, nie roboczymi.** Wewnętrzne limity strategii muszą być istotnie niższe. Metryką bramki operacyjnej jest **prawdopodobieństwo utrzymania konta**, nie zwrot ani Sharpe. |

### Bramka badawcza a bramka operacyjna

Rozróżnienie wprowadzone razem z R3, bo mieszanie ich byłoby błędem:

| Bramka | Pytanie | Metryka | Kiedy |
|---|---|---|---|
| **Badawcza** | Czy przewaga w ogóle istnieje? | SR, DSR, PBO | teraz |
| **Operacyjna** | Czy przy tej przewadze da się utrzymać konto z limitem 10%? | prawdopodobieństwo ruiny | po GO |

Strategia o dobrym Sharpie może mieć nieakceptowalne ryzyko ruiny przy limicie 10%,
jeśli jej rozkład ma gruby lewy ogon. Odwrotnie też: skromna przewaga o łagodnym
obsunięciu może być operacyjnie lepsza.

**Nie wolno cofać się z bramki operacyjnej do badawczej.** Gdyby karta przeszła badanie,
a potem okazała się zbyt ryzykowna dla konta, odpowiedzią jest zmiana **wielkości
pozycji**, nie zmiana reguły wejścia — to drugie byłoby strojeniem sygnału pod
ograniczenie kapitałowe, czyli dokładnie tym, czego zakazuje R2.

**Odłożone świadomie:** symulator zasad kont fundowanych. Wraca po GO/NO-GO dla H013.

---

## Licznik prób

Stan globalnego licznika: patrz `validation/trial_counter.json`.

**Reguła bezwzględna:** każdy przebieg backtestu — każda kombinacja parametrów w każdej siatce
każdej hipotezy — inkrementuje licznik. DSR każdego kandydata liczy się względem *całego*
licznika projektu, z korektą na korelację między wariantami (algorytm ONC, aneks A.3).

Limity: **≤ 10 wariantów na hipotezę**, **≤ 40 na partię**. Benchmarki nie liczą się do limitu,
bo nie są optymalizowane.

Dlaczego to jest twarde: przy N_eff = 30 nie przechodzi certyfikacji nawet strategia o Sharpe 1.5
(tabela wykonalności, PLAN rozdz. 6.5). Im dłużej szukamy, tym wyższy próg musi przeskoczyć
zwycięzca — to cena uczciwości i płacimy ją świadomie.

---

## Etap 2 — konsolidacja techniczna (03.08.2026)

Pierwsza generacja badawcza domknięta (`docs/SYNTEZA_GEN1.md`). Etap 2 to
**wyłącznie mapa i zamrożenie stanu** — żadnego usuwania, scalania ani
refaktoryzacji kodu.

| Artefakt | Zawartość |
|---|---|
| `docs/ARCHITEKTURA.md` | mapa 44 modułów (11 817 linii, 430 testów), kierunek zależności, trójstopniowa krytyczność |
| `golden/baseline.json` | pięć warstw, rozdzielone `hash_danych` i `hash_wynikow` |
| `golden/README.md` | jak używać, co zamrożone, znane wady |
| `golden/srodowisko.txt` | dokładne wersje, które wyprodukowały hashe |
| `docs/AUDYT_KODU.md` | kod martwy i zduplikowany w sześciu kategoriach |
| `docs/ZALOZENIA.md` | rejestr założeń, których zmiana unieważnia wyniki |
| `docs/OD_DANYCH_DO_PNL.md` | jedna realna transakcja prześledzona przez 9 etapów |
| `docs/PODRECZNIK.md` | 12 pytań właściciela |
| `docs/PLAN_REFAKTORU.md` | **do decyzji, nie wdrożone** |

**Odtwarzalność:** baseline odtworzony trzykrotnie z czystego stanu, bajt
w bajt (`hash_wynikow = 6a082749…`). Tag `gen1-baseline` oznacza ostatnią
wersję przed jakimkolwiek refaktorem.

### Ustalenie: błąd w `validation/spa.py` — ✅ NAPRAWIONE (R1)

Golden baseline ujawnił, że ścieżka `arch` dostawała zwroty tam, gdzie
`arch.bootstrap.SPA` oczekuje strat — znak odwrócony, testowana hipoteza
przeciwna. p = 0,898 identycznie dla czystego szumu i dla przewagi +0,30σ;
własny fallback dawał odpowiednio 0,303 i 0,002.

Naprawione w commicie `7f681ef` po dowodzie czerwieni testu przed poprawką
(`reports/R1_regresja_spa.md`). Po naprawie: szum 0,248, przewaga 0,000; oba
klucze fallbacku w baseline bit w bit bez zmian.

**Wpływ na wnioski W001–W013: żaden.** SPA nie było użyte, licznik prób 0.

### Wynik audytu kodu

79 linii kodu martwego i 4 ogniska duplikacji w 11 817 liniach (0,7%).
Trzy z czterech symboli martwych to **brak wykonania specyfikacji**, nie
śmieci — właściwą reakcją jest podpięcie, nie usunięcie. Rekomendacja:
refaktor minimalny, trzy pozycje zamiast dziewięciu.

**Licznik prób nadal 0.**

---

## Etap 2.5 — domknięcie techniczne (03.08.2026)

Minimalny refaktor wykonany i zamknięty. **Stabilny SHA: `b8572a5`** (R1+R2),
po Etapie 2.5 patrz koniec sekcji.

| Poz. | Zakres | Stan |
|---|---|---|
| **R1** | znak w ścieżce `arch` `validation/spa.py` | ✅ `7f681ef` — test czerwony przed poprawką, `golden/ZMIANY.md` v2 |
| **R2** | podpięcie `verify_continuity` i `describe` do `data_quality.py` | ✅ `b8572a5` — 8 testów, `golden/ZMIANY.md` v3 |
| **R3** | wspólne `t_stat` | ⏸ **nie migrowane** — kanoniczna wersja przy pierwszym użyciu w Gen2 |
| **N1–N6** | duży refaktor | ⏸ żadna pozycja nie weszła; N4 i N6 wyłącznie adnotacje |
| **2.5a** | `verify_continuity` z bramki na diagnostykę | ✅ `golden/ZMIANY.md` v4 |
| **2.5b** | empiryczna weryfikacja założenia A3 | ✅ `reports/A3_halt_weryfikacja.md` |

### Kontrola ciągłości — wynik

Niezmiennik arytmetyczny (offset back-adjustu stały w obrębie kontraktu):
**rozrzut 0,0000000000 w 90 z 90 kontraktów** na MNQ, NQ i ES. **PASS.**

Heurystyka „skok ≥ |spread|" **nie jest bramką** — jest nieidentyfikowalna,
nie odróżnia ruchu rynku od błędu korekty. Zgłasza 17/29 granic MNQ, 18/29 NQ,
12/29 ES przy zerowym rozrzucie offsetu; skrajny przypadek to ruch 659 pkt
z krachu covidowego przy spreadzie −13,50 pkt. Progu **nie zmieniano** —
problem leży w konstrukcji kryterium. Status: **INCONCLUSIVE**, nigdy
automatyczny FAIL.

### Założenie A3 — zamknięte empirycznie

Gęstość okna 16:15–16:30 ET: **0,05%** przed 27.06.2021 wobec **96,21%** po,
przy sąsiedztwie 16:00–16:15 na poziomie 96,2% po obu stronach. Kryterium to
kontrast, nie sama pustka — bary M1 nie odróżniają zamknięcia od braku obrotu,
więc rozstrzyga dopiero zestawienie z sąsiedztwem. Wszystkie wyjątki przed
granicą leżą na krawędzi okna (16:15 albo 16:29).

**Nie ma już w rejestrze założenia kalendarzowego bez własnego sprawdzenia.**

### Reguła trwała wyprowadzona z R1

Wszystkie testy SPA sprzed R1 wołały funkcję z `force_fallback=True` —
ścieżka domyślna nie była testowana w ogóle, więc 233 testy dawały **fałszywe
poczucie pokrycia**. Odtąd każdy moduł z implementacją podstawową i awaryjną
musi mieć osobne testy obu ścieżek oraz test ich zgodności co do werdyktu
(`docs/ZALOZENIA.md` G1a).

### Stan

- testów: **447**, ruff czysty, mypy bez uwag, golden `--sprawdz` zgodny
- **licznik prób: 0**
- wnioski W001–W013: **bez zmian**
- punkt odniesienia Gen1: `a1aba1c` (tag `gen1-baseline` tylko lokalnie —
  push odmówiony przez proxy, 403)

---

## Gen2-0 — brief kierunkowy (03.08.2026)

`docs/GEN2_BRIEF.md` — dokument **projektowy**, zero pomiarów. Żadna karta
nie powstała, żaden kierunek nie zmierzony, **licznik prób nadal 0**.

Pięć kierunków kandydackich, ocenionych przed pomiarem (0–5 w dziewięciu
kryteriach):

| Kierunek | Suma /45 | Uwaga |
|---|---|---|
| **D1** — rebalansowanie funduszy lewarowanych na zamknięciu | **43** | jedyny bez zakupu danych i z ~250 okazjami rocznie; benchmark = B04 |
| **D5** — mikrostruktura agresora (`trades`/MBP) | 33 | mechanizm najmocniejszy, **warunkowy** — wymaga decyzji zakupowej |
| D2 — baza i struktura terminowa NQ | 27 | ~4–20 okazji rocznie |
| D4 — oficjalne reguły indeksu NDX | 27 | efekt w spółkach, nie w indeksie |
| D3 — ekspozycja gamma dealerów | 24 | przewiduje charakter; zatłoczony publicznie |

### Ustalenie, które zmienia priorytety Gen2

Reguła „historia 2019–2026 = development only" w połączeniu z podłogą
N = 400 daje twardą konsekwencję arytmetyczną:

| Częstotliwość okazji | Czas do N = 400 na forwardzie |
|---|---|
| ~30 rocznie (profil H013) | **ponad 13 lat** |
| ~250 rocznie (raz na sesję) | ~1,6 roku |

**Częstotliwość okazji przestaje być jednym z kryteriów i staje się warunkiem
wstępnym.** Karta na zdarzeniach rzadkich jest w tym projekcie
niecertyfikowalna niezależnie od jakości mechanizmu.

### Rekomendacja (decyzja należy do właściciela)

D1 jako kierunek pierwszy, D5 jako warunkowy po osobnej decyzji zakupowej.
D2, D3 i D4 odradzane na teraz.

**Nie wybrano kierunku i nie napisano karty.** Kolejny krok wymaga decyzji.
