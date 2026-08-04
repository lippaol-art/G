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
| **W014** | **Zgodnosc empiryczna nie zastepuje semantyki protokolu zrodlowego.** Grupowanie `(ts_event, sequence, side)` wygladalo niemal idealnie: ceny w grupach monotoniczne, tylko **0,0037%** grup dwustronnych, a definicje A, B i C dawaly zgodny VIF. Interpretacja i tak byla bledna — `sequence` to numer sekwencyjny wiadomosci CME, a jedna wiadomosc moze zawierac wiele Trade Summaries, takze po przeciwnych stronach. **Ladny rozklad empiryczny jest przeslanka, nie dowodem, ze pole znaczy to, co nam pasuje.** Regula procesowa: zanim zmienna zostanie nazwana jednostka mechanizmu, jej znaczenie musi byc potwierdzone **dokumentacja albo przez dostawce**, nie sama zgodnoscia danych. Koszt zignorowania tej reguly w D5: caly Etap 2 zmierzyl poprawnie niewlasciwa jednostke. | D5-B |
| **W013** | **Kolumna, ktorej nic nie konsumuje, nie ma jak sie zdemaskowac.** Flaga `short_day` byla `False` dla wszystkich **2 551 265** barow, bo produkcyjny pipeline tworzyl pusty kalendarz. Kolumna istniala w schemacie, przechodzila walidacje `REQUIRED_COLUMNS` i przez caly czas nie znaczyla nic — nie wykryl tego ani przeglad kodu, ani testy, bo **zaden modul badawczy jej nie czytal**. Wniosek procesowy: pole dodane na zapas jest dlugiem, nie zabezpieczeniem; kazda flaga w schemacie potrzebuje albo konsumenta, albo testu sprawdzajacego jej **rozklad**, a nie tylko obecnosc. Wykryte dopiero, gdy jedna sesja z probki D5-B zachowala sie niezgodnie z oczekiwaniem. | kalendarz CME |
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

## Reguły trwałe projektu (R1–R3, R9)

Zapisane 02.08.2026 na podstawie kontekstu właściciela projektu: ograniczony budżet,
docelowo konto fundowane 200 000 USD z limitem 5% dziennie i 10% całkowicie.
**Reguły obowiązują niezależnie od wyniku którejkolwiek karty.**

| # | Reguła |
|---|--------|
| **R1** | **Każde nowe płatne źródło danych lub narzędzie wymaga czterech rzeczy przed zakupem:** uzasadnienia (co konkretnie odblokowuje), oszacowania kosztu, sprawdzenia darmowej alternatywy i **zgody właściciela**. Formalizuje procedurę zastosowaną przy zakupie warstwy K6 za $7.82. |
| **R9** | **Zapytania do wsparcia dostawcy piszemy zwiezle: 2-4 zdania kontekstu, jeden przyklad, maksymalnie 2-3 pytania na zgloszenie.** Wprost poproszone przez Databento: *I think your LLM may be making these questions a bit longer and more complex than necessary. We have real humans respond to every message.* Nasze pierwsze zgloszenie mialo szesc pytan i pelna tabele statystyk. Odpowiedz byla wyczerpujaca mimo to, ale po drugiej stronie siedzi czlowiek i to jego czas. Jedno zgloszenie = jeden watek problemowy. |
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

---

## Gen2 — audyt kierunku D1 (03.08.2026): NIEWYKONALNY

Kierunek aktywny wybrany przez właściciela: **D1** (rebalansowanie funduszy
lewarowanych). Audyt mechanizmu i danych **przed** napisaniem karty.
`docs/D1_AUDYT_MECHANIZMU.md`, odtworzenie: `scripts/audit_d1.py`.

**Zero zużytych prób** — audyt nie liczy żadnego zwrotu okna wynikowego, nie
mierzy P&L i nie zawiera reguły wejścia.

### Werdykt: `D1 NIEWYKONALNY`

**Blocker:** zmienna `ΔE = L(L−1)·A·r` jest w praktyce przeskalowanym `r`.
Wewnątrz każdego roku współliniowość z pełnym zestawem kontrolnym B04
(`r, |r|, r², sign(r)`) wynosi **R² = 0,86–0,97** nawet po najlepszej dostępnej
normalizacji płynnością → średni VIF **23**, czyli błąd standardowy
współczynnika przyrostowego większy ok. 4,8 razy (w uproszczonej analogii
informacyjnej odpowiada to spadkowi N = 400 do ~17 — nie jest to jednak
dosłowna liczebność próby).

Jedyna zmienność identyfikująca pochodzi z **wolnego wzrostu aktywów kompleksu**
(K: 42,7 → 242,7 mld USD, 5,7× w siedem lat). Dodanie członu `r × trend`
podnosi `R²(ΔE ~ r)` z 0,826 do **0,981** — czyli informacja poza `r` jest
w 98% trendem, nieodróżnialnym od hipotezy „efekt B04 zmieniał siłę w czasie".

### Falsyfikatory

| # | Warunek | Wynik |
|---|---|---|
| 1 | point-in-time historia aktywów | ✅ darmowa, pełna od inception |
| 2 | universe bez survivorship bias | ⚠ częściowo |
| 3 | dźwignia i benchmark znane historycznie | ✅ |
| 4 | brak lookaheadu w publikacji | ✅ reguła t−1 ustalona z danych |
| 5 | ścieżka transmisji do NDX | ⚠ nierozstrzygnięte (trasa swapowa) |
| 6 | okno zamrażalne przed wynikiem | ✅ |
| 7 | przepływ odróżnialny od `r` | ❌ |
| 8 | brak współliniowości z B04 | ❌ |

### Ustalenia poboczne warte zapamiętania

- **Dane są darmowe i point-in-time** — `accounts.profunds.com/etfdata/ByFund/
  {TICKER}-historical_nav.csv`, pełna historia, kolumny NAV / jednostki / AUM.
  To korekta wobec GEN2_BRIEF, który zakładał to bez sprawdzenia.
- **`AUM_t = NAV_t × jednostki_t` co do centa** — dowodzi, że wiersz z dnia `t`
  jest wielkością **po zamknięciu**, więc dostępny jest wyłącznie wiersz `t−1`.
- **Ivanov & Lenkey (2018) potwierdzeni na naszej próbie 2019–2026:**
  corr(Δjednostek, r) = **−0,343** dla TQQQ i **+0,356** dla SQQQ — w obu
  przypadkach przepływ inwestorów działa **przeciw** rebalansowi.
- **Kolizja tickerów:** `QQQU`/`QQQD` to dziś dwa różne produkty u dwóch
  emitentów, o różnych indeksach bazowych. Automatyczne zaciągnięcie
  „lewarowanych QQQ" skleiłoby dwa różne szeregi.
- **Kryterium ogólne do przyszłych kierunków:** mechanizm, którego zmienna ma
  postać „wolno zmienny czynnik × zwrot dnia", jest z góry skazany na
  współliniowość z momentum dziennym. Da się to sprawdzić na kartce, **przed**
  pobraniem jakichkolwiek danych.

**Nie napisano karty H017. Nie kupiono żadnych danych. Licznik prób: 0.**

Kierunek rezerwowy D5 pozostaje rezerwą — wraca wyłącznie po zawężeniu do
jednej zamrożonej zależności, wskazaniu pól danych, wycenie i osobnej zgodzie.

---

## Gen2 — audyt kierunku D5 (03.08.2026): WYKONALNY warunkowo

`docs/D5_AUDYT_WYKONALNOSCI.md`. **Zero zużytych prób, zero zakupionych
danych** — wycena wyłącznie przez `metadata.get_cost` (read-only).

### Werdykt: `D5 WYKONALNY — można rozważyć kartę i zakup minimalnej próbki`

Wszystkie siedem warunków obowiązkowych spełnione.

**Mechanizm wybrany przed danymi: kontynuacja metaorderu, znak dodatni.**
Podstawa: długa pamięć znaku zleceń (Lillo–Mike–Farmer 2005, replikacja
*Phys. Rev. Lett.* 131, 197401 z 2023; Hurst ≈ 0,7).

**Historia absorpcji ODRZUCONA**, nie odłożona — wymaga stwierdzenia, że
konkretny duży pasywny uczestnik zostanie wyczerpany, czego dane anonimowe nie
zawierają. Dałaby znak zależny od nieobserwowalnego stanu, czyli w praktyce
swobodę wyboru znaku po zobaczeniu wyniku.

### Konsekwencja wyboru: MBP niepotrzebny

| Schemat | 1 dzień | 1 miesiąc | Rozmiar/mies. | Potrzebny? |
|---|---|---|---|---|
| **`trades`** | **1,75** | **29,83** | 1,14 GB | **TAK, wystarczy** |
| `tbbo` | 2,92 | 49,71 | 1,91 GB | pomocniczy |
| `mbp-1` | 3,68 | 59,07 | 35,2 GB | nie |
| `mbo` | 4,67 | 75,27 | 44,9 GB | nie |
| `mbp-10` | 7,18 | 115,14 | **247,3 GB** | nie |

**Twarde ograniczenie infrastrukturalne:** dostępne 28 GB dysku. MBP-1, MBO
i MBP-10 **nie mieszczą się** niezależnie od budżetu.

Zawężenie okna obniża koszt proporcjonalnie: doba 1,75 → RTH 1,34 → ostatnia
godzina **0,23**. Rok `trades` w oknie jednogodzinnym ≈ **25 USD** (średnia
z pięciu dni z różnych kwartałów, po zakotwiczeniu okna w ET) wobec 271,66 USD
za pełny rok.

### Plan etapowy — 32 USD do GO/NO-GO

1. **Etap 1, 1,75 USD, 1 dzień** — kompletność pola `side` (enum dopuszcza
   `NONE`, odsetek nieznany). Kryterium: >95% wypełnienia.
2. **Etap 2, ~30 USD, 1 miesiąc** — **lekcja z D1 zastosowana wcześnie**: czy
   nierównowaga przepływu daje się odróżnić od momentum ceny. Kryterium:
   **VIF < 5**. Powyżej — D5 dzieli los D1 za 32 USD zamiast za kilkaset.
3. **Etap 3** — dopiero po zielonych 1 i 2, osobna zgoda.

Próbki wybierane **mechanicznie** (ostatni zamknięty miesiąc kalendarzowy),
nie dlatego, że były zmienne albo ciekawe.

### Inwentaryzacja

**Nie posiadamy żadnych danych `trades`, MBP ani MBO.** Miesiąc `trades` z planu
Etapu 1 (23,77 USD) **nigdy nie został kupiony**. Korzystna konsekwencja: żadna
próbka nie została obejrzana, więc pierwsza kupiona może zostać przeznaczona
świadomie, bez długu ekspozycji.

### Korekta własnej oceny z briefu

D5 dostał w briefie **5/5 za liczbę okazji**. Przy poprawnej jednostce
niezależności — **sesja, nie sygnał** — zasługuje na tyle samo, co D1: sto
sygnałów z jednej sesji dzieli reżim, zmienność, makro i **często ten sam
metaorder**. Efektywna częstotliwość to ~250 sesji rocznie.

### Dwa zastrzeżenia zapisane jawnie

1. **Pytanie o przyrost ponad momentum to blocker D1 w innym przebraniu.**
   Różnica strukturalna: w D1 współliniowość była **algebraiczna i nieusuwalna**,
   w D5 jest **empiryczna** — przypadki rozjazdu (duża agresja, mały ruch ceny)
   są właśnie przypadkami interesującymi. Dlatego D1 dało się zamknąć na
   kartce, a D5 nie.
2. **To najbardziej zatłoczony sygnał w mikrostrukturze.** W horyzoncie, gdzie
   jest najsilniejszy (poniżej sekundy), nie konkurujemy. Zakład dotyczy
   horyzontu dziesiątek sekund do minut po kosztach. Literatura z lat 2010+
   jest raczej sceptyczna. **Uczciwie otwarte pytanie, nie przewidywana wygrana.**

**Nie napisano H017. Nie kupiono danych. Licznik prób: 0.**

---

## D5 Etap 1 — wykonany (03.08.2026): `D5-A GO`

**Pierwszy zakup danych od Etapu 1 projektu.** Specyfikacja zamrożona commitem
**przed** zakupem (`41d3eee`), korekta budżetu (`953b5ec`), dopiero potem
pobranie i kontrole. `docs/D5_ETAP1_SPEC.md`, `reports/D5_etap1_kontrole.md`,
`data/manifest_trades.md`.

| | |
|---|---|
| Sesja | `2026-07-30`, `MNQU6`, 1 696 891 transakcji |
| Koszt | **2,1240 USD** (limit 2,15) |
| Wydatek projektu łącznie | 7,82 + 2,1240 = **9,9440 USD** |
| Budżet pozostały | **60,2960 USD** |

### Werdykt: `D5-A GO`

`side != NONE` = **99,9999%** przy progu 95%. Kompletność ≥ 99,998%
w **każdym** z dziewięciu segmentów sesji. Największe ryzyko audytu D5 — że
pole agresora będzie rzadko wypełnione — **nie zmaterializowało się**.

Semantyka ustalona **z danych**, nie z pamięci: przy rosnącej cenie dominuje
`B` (87,7%), przy spadającej `A` (88,1%), więc **`B` = agresor kupujący**,
`A` = sprzedający. Tick posłużył wyłącznie do odczytania znaczenia etykiety,
nie do jej odtworzenia — zakaz rekonstrukcji strony z ruchu ceny nienaruszony.

### Dwa ustalenia projektowe dla Etapu 2

1. **Jednostką mechanizmu jest ZDARZENIE AGRESORA, nie wypełnienie.** CME
   drukuje osobny rekord na każde wypełnienie jednego zlecenia agresora:
   1 696 891 wypełnień → **1 479 365 zdarzeń** (1,15 na zdarzenie). Liczenie
   nierównowagi po wypełnieniach mierzyłoby fragmentację płynności zamiast
   agresji.
2. **Granica okna musi być liczona na `ts_recv`, nie `ts_event`.**

### Ustalenie uboczne o znaczeniu dla całego projektu

Rekonstrukcja `ohlcv-1m` z surowych transakcji: **0 niezgodności na 1 380
barach** w open, high, low, close **i** wolumenie — przy agregacji po `ts_recv`.
Na `ts_event` wychodzi 8 / 6 / 20 niezgodności przez przesunięcia na granicy
minuty (suma różnic wolumenu dokładnie zero — sygnał, że to granica, nie brak
danych).

**To domyka zaległość z audytu 4 (poprawka A4-10)** — niezależną kontrolę
jakości barów przez rekonstrukcję z transakcji, zaplanowaną w Etapie 1 projektu
i nigdy niewykonaną. Nasze bary odtwarzają się z surowych transakcji co do
ticka i co do sztuki.

### Ekspozycja na dane

Sesja `2026-07-30` została **obejrzana**, więc gdyby weszła do próby badawczej,
jest **development only**. Jedna sesja z ~250 rocznie — wpływ pomijalny,
odnotowany.

### Zatrzymanie

Miesiąc `trades` (~29,83 USD) wymaga **osobnej decyzji** oraz wcześniejszego
zamrożenia: definicji nierównowagi (po zdarzeniach agresora), okna obserwacji,
benchmarku momentum i sposobu liczenia VIF.

**H017 nie powstaje. P&L nie mierzony. Licznik prób: 0.**

---

## D5 Etap 2 — wykonany (03.08.2026): `D5-B GO`

Specyfikacja zamrożona **przed zakupem** (`docs/D5_ETAP2_SPEC.md`, commity
`91d2649` i `00fdcad`), zakup po zamrożeniu, wynik w
`reports/D5_etap2_wyniki.md`.

### Werdykt: `D5-B GO`

`I_count` — nierównowaga `candidate_aggressor_event` w oknie 60 s — **nie jest
odtwarzalna** z równoczesnego momentum ceny, jego przekształceń, wolumenu ani
efektów pory dnia.

| Warunek §8 | Wymóg | Zmierzone |
|---|---|---|
| pooled VIF | < 5 | **1,548** (R² = 0,354) |
| mediana dziennego VIF | < 5 | **1,787** |
| sesji z VIF < 5 | ≥ 75% | **100%** (21/21) |
| udział jednej pory dnia | ≤ 20% | **9,99%** |
| obie strony agresji, najsłabsza sesja | ≥ 20% okien | **39,2%** |
| udział jednej sesji | ≤ 20% | **10,21%** |

Kontrole B (po wypełnieniach, VIF 1,971) i C (`I_volume`, VIF 2,291) zgodne
z A co do werdyktu. **Werdykt pochodzi wyłącznie z A** — B i C nie były użyte
do jego zmiany po zobaczeniu liczb.

### Dlaczego to nie jest powtórka D1

W D1 identyfikacja siedziała w wolnym trendzie i dlatego nie znaczyła nic.
Tutaj pooled VIF prawie nie zmienia się po usunięciu efektów pory dnia
(1,548 → 1,532), a dzienne VIF-y — liczone **wewnątrz** pojedynczych sesji —
też są niskie. Identyfikacja nie pochodzi więc ani z pory dnia, ani z różnic
między sesjami. To jest ta różnica, dla której D5 dostał kartę wstępu, a D1 nie.

### Próbka

22 sesje RTH lipca 2026, `MNQU6`, **22 080 246 wypełnień**, 19 837 327 zdarzeń,
**8 400 okien** 60 s. Koszt: wycena **26,406 USD**, górna granica **27,916 USD**
(urwany transfer jednej sesji mógł zostać naliczony dwa razy; API Databento
nie ma endpointu rozliczeniowego, więc podana jest granica, nie zmierzona
kwota). Limit zamrożony: 30,00 USD — dotrzymany.

### Bramka §10 przed VIF

Rekonstrukcja `ohlcv-1m` dla całego miesiąca: **8 400 z 8 400 minut zgodnych
co do ticka i co do sztuki**, zero minut bez pary po którejkolwiek stronie,
zero przecięć zakresów między plikami. Nie było niezgodności do wyjaśnienia.
Potwierdza na 22× większej próbce ustalenie z Etapu 1: bary Databento powstają
na **`ts_recv`**.

### Trzy błędy własne — wykryte przed wydaniem werdyktu

1. **Przepełnienie typu bez znaku.** Pierwszy przebieg dał `D5-B NO-GO`.
   Wynik był fałszywy: `I_count` jest z konstrukcji w [−1, +1], a przyjmował
   wartości rzędu 1,5 mln, bo `n_buy − n_sell` na typach bez znaku przepełnia
   się do ~1,8·10¹⁹ zamiast dać liczbę ujemną. **Fałszywy `NO-GO` nie został
   nigdzie zaraportowany jako wynik.** To druga wystąpienie tej samej klasy
   błędu w tym projekcie (pierwsze: różnica wolumenów w Etapie 1).
2. **Warunki 4 i 5 z §8 nie były liczone** — skrypt sprawdzał cztery z sześciu.
3. **Grupy niejednoznaczne nie były wykluczane** wbrew §3 (732 pary
   `(ts_event, sequence)` po obu stronach — 0,0037% grup; po wykluczeniu wyniki
   bez zmian do czwartego miejsca).

### Nowa reguła trwała projektu

**Każda zmienna o znanym z konstrukcji zakresie dostaje jawną asercję tego
zakresu w miejscu obliczenia.** Błąd przepełnienia nie rzuca wyjątku i nie psuje
wykresu — zmienia werdykt. Uzupełnia to regułę o rzutowaniu na `Int64` przy
odejmowaniu kolumn bez znaku, zapisaną po Etapie 1: samo rzutowanie okazało się
niewystarczające, bo trzeba jeszcze pamiętać, żeby je zastosować.

### Warunkowość reguły grupowania pozostaje w mocy

`candidate_aggressor_event = (ts_event, sequence, side)` jest nadal
**empirycznym przybliżeniem**, nie potwierdzonym identyfikatorem zlecenia
agresora. Pytanie do Databento przygotowane w `docs/D5_PYTANIE_DATABENTO.md`
(semantyka `sequence`, `F_LAST`, `flags == 0` w 22 mln rekordów, 732 pary
dwustronne). **Odpowiedź musi być dołączona do dokumentacji przed powstaniem
H017.**

### Status i co dalej

**Cały lipiec 2026 jest development setem** — nie jest OOS i nie stanie się nim
po zamrożeniu H017. Zgodnie z §11 `GO` uprawnia do napisania karty H017
z zamrożonym mechanizmem, znakiem, oknem i wykonaniem (**wyłącznie RTH**),
następnie pre-flightu trwałości znaku, i dopiero potem pierwszego backtestu.

**H017 nie powstaje w tym wpisie. P&L nie został zmierzony.
Licznik prób: 0.**

---

## Reguły trwałe R4–R8

Numeracja R4 i R5 byla przeze mnie cytowana w opisie PR zanim trafila tutaj —
to byl blad zapisu, nie nowa regula. Obie formalizuja praktyke stosowana
od poczatku kierunku D5.

### R4 — specyfikacja zamrozona w commicie PRZED zakupem danych

**Zadne dane nie sa kupowane, dopoki definicja pomiaru, warunki GO/NO-GO
i limit kosztu nie sa zapisane w commicie.** Zamrozony limit zatrzymal zakup
dwukrotnie i za kazdym razem mial racje: moje ekstrapolacje kosztu myllily sie
o 21% (Etap 1) i o 40% (Etap 2, lipiec 2026 wobec marca 2025 przy identycznej
stawce za rekord).

Regula obejmuje takze **kolejnosc kontroli**: kontrola jakosci danych
zadeklarowana w specyfikacji musi przejsc PRZED policzeniem glownej metryki,
a nie po. W D5-B rekonstrukcja OHLCV calego miesiaca poprzedzila VIF wlasnie
z tego powodu.

### R5 — asercja zakresu dla zmiennych o znanych granicach

**Zmienna o granicach wynikajacych z konstrukcji dostaje jawna asercje tego
zakresu w miejscu obliczenia.** Wartosc poza zakresem jest dowodem bledu
obliczenia, nie wlasnoscia rynku. Wchlonieta przez druga warstwe R6, ale
zapisana osobno, bo dotyczy KAZDEJ zmiennej o znanym zakresie, nie tylko
roznic typow bez znaku.

### R6 — typy ze znakiem przed odejmowaniem

**Każda operacja, której wynik może być ujemny, musi zostać wykonana na typie
ze znakiem przed odejmowaniem, niezależnie od typu wyniku końcowego.**

Podstawa: ta klasa błędu wystąpiła dwa razy (różnica wolumenów w Etapie 1 D5,
`n_buy − n_sell` w Etapie 2 D5 — fałszywy werdykt `NO-GO`). Odejmowanie kolumn
bez znaku przepełnia się do ~1,8·10¹⁹ zamiast dać liczbę ujemną; **nie rzuca
wyjątku i nie psuje wykresu — zmienia werdykt**.

**Druga warstwa, bo samo rzutowanie kiedyś zostanie pominięte:** zmienna
o znanych z konstrukcji granicach dostaje jawną asercję zakresu w miejscu
obliczenia (`engine.guards`: `assert_imbalance` [−1,+1], `assert_udzial`
i `assert_prawdopodobienstwo` [0,1], `assert_liczebnosc` ≥ 0, `assert_vif` ≥ 1).
Skaner statyczny: `scripts/audit_typy_bez_znaku.py`.

### R7 — jeden kanoniczny entrypoint bramki lokalnej

**Przed pushem zmian w `engine/`, `validation/` albo pipelinie danych lokalna
bramka musi uruchamiać dokładnie ten sam zestaw co CI: ruff, mypy, testy
z pokryciem, strażniki, bramka 5.6 i golden check.**

Podstawa: push z błędami mypy przeszedł lokalnie, bo uruchomiłem ruff i testy,
a mypy pominąłem. Cztery komendy do zapamiętania to cztery okazje do pominięcia
jednej.

Realizacja: **`bash scripts/check_all.sh`** (wariant `--szybko` pomija bramkę
5.6 i golden). Rozjazd między tym skryptem a `.github/workflows/ci.yml` czyni
bramkę bezużyteczną — zmiana w jednym wymaga zmiany w drugim.

### R8 — przebudowa artefaktów danych tylko z jawnym zakresem zmian

**Przebudowa `data/clean/` wymaga: budowy do katalogu tymczasowego,
porównania kolumna po kolumnie ze zbiorem poprzednim, jawnej listy kolumn
dozwolonych i zabronionych, i podmiany atomowej dopiero po zgodności.**

Baseline aktualizuje się **po** potwierdzeniu zakresu, nigdy dlatego, że stary
przestał przechodzić. Lista kolumn zabronionych jest **wyliczona jawnie**, a nie
zdefiniowana jako „wszystko poza dozwolonymi" — inaczej dopisanie kolumny do
schematu po cichu wyłącza kontrolę.

Realizacja: `scripts/rebuild_clean.py`. Pierwsze zastosowanie: baseline v9.

---

## D5 Etap 2 — WERDYKT ZASTĄPIONY (04.08.2026): `D5-B INCONCLUSIVE`

Wpis `D5-B GO` powyżej **pozostaje w rejestrze bez zmian** jako zapis tego, co
zmierzyliśmy i uznaliśmy 03.08.2026. Nie przepisuję historii.

### Co się zmieniło

Odpowiedź Databento z 2026-08-04, 11:00 UTC (pełna treść:
`docs/D5_PYTANIE_DATABENTO.md` §C) stwierdza wprost:

> `sequence` is the original CME venue message sequence number. It is not
> a unique matching-event identifier. A CME Trade Summary message can contain
> multiple trade summaries, so records sharing `(ts_event, sequence)` are not
> guaranteed to represent one aggressing order or matching event.

**Obliczenia D5-B nie są numerycznie błędne. Błędna była interpretacja głównej
zmiennej A jako liczby zdarzeń agresora.**

### Nowy status

```
D5-B INCONCLUSIVE — niewłaściwa jednostka pomiaru
```

**Nie `NO-GO`**, ponieważ nie wykazaliśmy, że mechanizm nie działa: pole `side`
jest poprawne, `trades` odtwarzają bary co do ticka, kontrole B i C też miały
niski VIF. Problemem jest **niemożność odtworzenia pojedynczego zdarzenia
agresora z wybranego schematu**.

**Nie `GO`**, ponieważ zamrożona specyfikacja mówiła, że główny werdykt pochodzi
**wyłącznie z A**, a A opiera się na grupowaniu oficjalnie odrzuconym przez
dostawcę. **B i C nie mogą przejąć roli A** — były kontrolami pomiaru, a zmiana
głównej definicji po zobaczeniu wyników złamałaby regułę zamrożoną przed
zakupem.

### Co pozostaje w mocy

| Ustalenie | Status |
|---|---|
| **`ts_recv` jako podstawa agregacji barów** | **oficjalnie potwierdzone przez dostawcę** (Q6) — bary agregowane po `ts_recv`, znacznik interwału wystawiany jako `ts_event` bara |
| Rekonstrukcja 8 400 z 8 400 minut co do ticka | bez zmian |
| Poprawność pola `side` (D5-A GO) | bez zmian |
| Kontrola jakości danych, brak duplikatów | bez zmian |
| 732 pary dwustronne | **wyjaśnione** — normalna struktura protokołu, nie defekt danych |
| `flags == 0` w `trades` | **wyjaśnione** — zachowanie oczekiwane, niezależne od wersji DBN |

### Kanoniczna droga rekonstrukcji

Dostawca wskazał **`mbo` jako minimalny właściwy schemat**: każde CME Trade
Summary normalizowane jest do rekordu Trade, po którym następują rekordy Fill
pasywnych zleceń; rekord Trade może zawierać `order_id` agresora, gdy CME go
podaje; granicę zdarzenia per instrument wyznacza **`F_LAST`**.
**MBP-1 i TBBO nie wystarczą** — nie zawierają szczegółu pasywnych wypełnień.

### H017 — nadal nie powstaje

Blocker się **zmienił**, nie zniknął. Nie jest nim już oczekiwanie na e-mail,
tylko **brak kanonicznej rekonstrukcji zdarzeń z MBO**. Powody:

1. nie mamy poprawnie zrekonstruowanych zdarzeń agresora,
2. główna zmienna A nie odpowiada deklarowanemu mechanizmowi,
3. B i C nie mogą przejąć roli głównej po zobaczeniu wyniku.

### Następny krok

Jednodniowy audyt `mbo` na sesji **2026-07-30** — tej samej, która już jest
development setem, więc **nie dokładamy nowej daty do ekspozycji**. Nie
kupujemy całego miesiąca. Nie mierzymy przyszłych zwrotów ani VIF.

**Licznik prób: 0.** Żaden przyszły zwrot ani P&L nie został obejrzany.
