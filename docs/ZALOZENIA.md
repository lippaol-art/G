# Rejestr założeń

Krok 10 Etapu 2. Lista założeń, których **zmiana unieważnia wyniki** — nie lista
wszystkich decyzji projektowych.

Kryterium wpisu jest jedno i twarde: *gdyby to założenie okazało się fałszywe
albo zostało zmienione, czy któryś zapisany wniosek przestaje obowiązywać?*
Jeśli odpowiedź brzmi „nie", decyzja tu nie należy — jest w PLAN albo
w komentarzu przy kodzie.

Kolumna **„co unieważnia"** jest najważniejsza. Bez niej rejestr byłby listą
faktów; z nią jest narzędziem: po zmianie założenia wiadomo dokładnie, co
przeliczyć.

---

## A. Czas i sesje

### A1 — Doba handlowa zaczyna się o 18:00 ET

`trade_date` przypisuje bar do sesji zaczynającej się o 18:00 ET dnia
poprzedniego. Nie o północy UTC, nie o 09:30 ET.

- **Dlaczego tak:** to godzina otwarcia sesji CME Globex. Podział o północy
  rozcinałby noc na dwie „sesje" i zniszczyłby każdy pomiar dryfu nocnego.
- **Co unieważnia:** W001 (dryf nocny), W011 (model nocny), wszystkie limity
  ryzyka dzienne i tygodniowe, każdą agregację per sesja. Praktycznie cały
  dorobek badawczy.
- **Jak sprawdzić:** `tests/test_sessions.py`, przypadki przez weekend.
- **Pewność:** wysoka — to fakt o rynku, nie wybór.

### A2 — Strefa czasowa zawsze przez `America/New_York`, nigdy przez stały offset

- **Dlaczego tak:** ET jest UTC−5 zimą i UTC−4 latem, a przejścia nie pokrywają
  się z europejskimi. Stały offset przesuwa RTH o godzinę przez kilka tygodni
  w roku.
- **Co unieważnia:** każdy pomiar zależny od pory dnia — czyli wszystko poza
  metrykami zagregowanymi rocznie.
- **Jak sprawdzić:** baseline, warstwa `silnik.sesje` — dwa punkty graniczne
  przy zmianie czasu.
- **Pewność:** wysoka.

### A3 — Halt 15:15–15:30 CT istniał do 27.06.2021

- **Dlaczego tak:** CME zniosło tę przerwę dopiero wtedy; w danych 2019–H1 2021
  ona **jest**.
- **Co unieważnia:** analizy segmentu popołudniowego obejmujące lata 2019–2021,
  jeśli nie wykluczą tego okna.
- **Pewność: ZWERYFIKOWANE EMPIRYCZNIE** (Etap 2.5, 03.08.2026) na MNQ, NQ i ES.

  Gęstość okna 16:15–16:30 ET (udział wypełnionych minut):

  | Instrument | Przed 27.06.2021 | Po 27.06.2021 | Sąsiedztwo 16:00–16:15 przed |
  |---|---|---|---|
  | MNQ | **0,05%** | 96,21% | 96,2% |
  | NQ | **0,05%** | 96,21% | 96,3% |
  | ES | **0,07%** | 96,21% | 96,3% |

  Kryterium jest **kontrast, nie sama pustka**. Bary M1 nie odróżniają
  formalnego zamknięcia od braku transakcji (założenie B4), więc puste okno
  samo w sobie niczego by nie dowodziło. Dowodzi zestawienie z sąsiedztwem:
  te same dni, okno 15 minut wcześniej, wypełnione niemal w komplecie.

  Wszystkie wyjątki przed granicą (4 dni MNQ i NQ, 6 dni ES) leżą na **krawędzi
  okna** — minuta 16:15 albo 16:29, nigdy w środku. Dni po granicy bez barów
  (50) to święta amerykańskie.

  **Ograniczenie dowodowe zachowane:** to nie jest dowód formalnego zamknięcia,
  tylko braku obrotu nieodróżnialnego od niego przy rozdzielczości minutowej.
  Dla projektu różnica nie ma znaczenia — silnik i tak nie wykona zlecenia bez
  wolumenu (`bar.tradeable`).

  Raport: `reports/A3_halt_weryfikacja.md`. Test:
  `tests/test_sessions.py::test_granica_A3_zgodna_z_danymi`.

---

## B. Ceny i ciągłość

### B1 — `px_raw` do poziomów międzysesyjnych, `px_adj` do zwrotów i P&L

Poziomy odniesienia (PDH/PDL, profil wolumenowy, wszystko kotwiczone w cenie
absolutnej) liczone **wyłącznie** na serii surowej kontraktu aktywnego;
egzekucja i wynik — na serii ciągłej.

- **Dlaczego tak:** back-adjust przesuwa całą historię o stałą; poziom
  „wczorajszy szczyt" policzony na serii skorygowanej rozjeżdża się na granicy
  rolowania (4 dni w roku).
- **Co unieważnia:** każdą kartę używającą poziomów (H005, H001 w wersji ORB).
- **Jak sprawdzić:** `engine.guards.assert_raw_series` — strażnik odmawia
  podania `px_adj` funkcjom poziomów.
- **Uwaga o zakresie:** to **nie** dotyczy VWAP sesyjnego. VWAP w całości leży
  w jednym kontrakcie, więc stałe przesunięcie go nie zmienia. Audyt 1 twierdził
  inaczej i to była przesada, którą wtedy odrzuciliśmy.

### B2 — Back-adjust futures różnicowy, korekta splitów akcji multiplikatywna

- **Dlaczego tak:** różnica cen kontraktów to baza (koszt finansowania), więc
  addytywna; split to przemnożenie liczby akcji, więc multiplikatywna.
- **Co unieważnia:** pomylenie ich psuje zwroty w K6 (megacapy) albo ciągłość
  MNQ/NQ/ES.
- **Jak sprawdzić:** `tests/test_roll_metrics.py`, `tests/test_equities.py`.

### B3 — Rolowanie po wolumenie, nie po kalendarzu

- **Co unieważnia:** dni rolowania przesuwają się o 1–3 sesje względem reguły
  kalendarzowej; wpływa na wszystko, co filtruje `days_to_roll`.
- **Pewność:** wysoka — reguła jest nasza i w pełni odtwarzalna z danych.

### B4 — Brak bara oznacza brak transakcji, nie lukę w danych

Databento: *„If no trade occurs within the interval, no record is printed."*

- **Co unieważnia:** sanity-report, który flagowałby to jako defekt; oraz każdą
  strategię, która wykonałaby zlecenie na barze o zerowym wolumenie.
- **Jak sprawdzić:** `engine.sessions.is_expected_gap`, baseline przypadek
  `zerowy_wolumen_blokuje_wejscie`.
- **Konsekwencja w kodzie:** forward-fill dozwolony dla wskaźników, **zakazany**
  dla barów wejścia i SL.

---

## C. Wykonanie i koszty

### C1 — Sygnał z bara *i* wykonuje się najwcześniej na barze *i+1*

- **Dlaczego tak:** w momencie zamknięcia bara *i* znamy jego close, ale nie
  trajektorię po nim. Wykonanie w tym samym barze to lookahead.
- **Co unieważnia:** **wszystko.** To jest jedno założenie, którego złamanie
  zamienia cały projekt w generator fikcyjnych zysków.
- **Jak sprawdzić:** `engine.guards.HistoryView` (strategia fizycznie nie widzi
  przyszłości), `tests/test_runner_loop.py`, baseline warstwa `silnik`.
- **Cena, którą płacimy świadomie:** benchmarki z literatury zakładają wejście
  „po cenie otwarcia sesji", my wchodzimy minutę później. Ta sama cena dla
  benchmarków i dla kart własnych, więc porównanie zostaje sprawiedliwe.

### C2 — Przy dotknięciu SL i TP w jednym barze wygrywa SL

- **Dlaczego tak:** dane M1 nie zawierają kolejności zdarzeń wewnątrz bara.
- **Co unieważnia:** systematycznie **zaniża** win rate strategii o wysokim R:R
  — to skrzywienie statystyczne, nie tylko konserwatyzm (ustalenie audytu 1).
- **Dlatego:** pasmo wrażliwości (wynik przy SL_WINS kontra TP_WINS) jest
  metryką **obowiązkową**, nie opcjonalną. Baseline zamraża oba przypadki.
- **Wyjście docelowe:** sub-bary 1s z Databento dla spornych minut — policzone
  jako 0,00024 USD za minutę, czyli 12 centów za 500 spornych minut w całej
  historii.

### C3 — Koszt bazowy 2,20 USD RT (1 tick na stronę + prowizja)

- **Historia:** dokument v1.0 miał tu **3,20 USD** — błąd arytmetyczny wykryty
  przez audyt 1 i poprawiony w v1.1.
- **Co unieważnia:** każdy wynik netto; przy 10 transakcjach dziennie różnica to
  5 522 kontra 8 000 USD rocznie.
- **Bufor:** wyłącznie w stress-teście ×2 jako warunku bramki — **nie** w bazie.

### C4 — Zlecenie limitowe wymaga penetracji o ≥1 tick

- **Dlaczego tak:** dotknięcie poziomu nie dowodzi wypełnienia; kolejki zleceń
  z OHLCV M1 policzyć się nie da.
- **Co unieważnia:** każdą kartę z wejściem limitowym.
- **Kontrola:** test wrażliwości przy 2 tickach.

---

## D. Zdarzenia i próbki

### D1 — Zdarzenia pochodzą z rejestrów, nigdy z reakcji ceny

Kalendarze: SEC EDGAR (8-K item 2.02), BLS (harmonogramy roczne), Federal
Reserve (kalendarz FOMC). Detektor cenowo-wolumenowy służy **wyłącznie jako
kontrola** precision/recall.

- **Dlaczego tak:** wykrywanie zdarzeń z ceny to selection bias — wybierałoby
  zdarzenia po wielkości badanej reakcji, czyli po zmiennej zależnej.
- **Co unieważnia:** H013, H003, H014 i wszystko, co warunkuje na zdarzeniach.
- **Pewność:** wysoka, ale opiera się na pułapce udokumentowanej osobno:
  `acceptanceDateTime` w SEC ma **niespójną strefę czasową** (sufiks `Z` bywa
  fałszywy), więc czas czytamy ze strony indeksowej zgłoszenia.

### D2 — Rozliczenie AMC reaguje w następnej sesji RTH, makro w bieżącej

- **Co unieważnia:** przesunięcie o jedną sesję niszczy każdy pomiar reakcji.
- **Jak sprawdzić:** `tests/test_earnings.py`, `tests/test_macro.py`.

### D3 — Ranga i kwantyle liczone w oknie rozszerzającym, nigdy z pełnej próby

Rozgrzewka: 20 obserwacji.

- **Dlaczego tak:** kwantyl z pełnej próby zawiera przyszłość. Tercyle z całej
  historii to lookahead przebrany za normalizację.
- **Co unieważnia:** W013 (H003) i każdą przyszłą kartę z podziałem na tercyle.

---

## E. Metodologia

### E1 — Pre-flight nie zużywa próby, backtest zużywa

- **Dlaczego tak:** pre-flight bada rozkłady i mechanizm, nie optymalizuje
  reguły ani nie mierzy P&L.
- **Co unieważnia:** gdyby to było fałszywe, licznik prób nie wynosiłby 0, tylko
  ~13, a **próg DSR przesunąłby się dramatycznie** (przy N_eff=10 nawet SR 1,2
  nie przechodzi). To założenie ma bezpośrednią cenę statystyczną.
- **Uczciwe zastrzeżenie:** „zero prób" **nie znaczy „zero ekspozycji na dane"**.
  Projektowanie kolejnych kart było informowane wcześniejszymi ustaleniami,
  a tego DSR nie mierzy. Zapisane w `docs/SYNTEZA_GEN1.md` i podtrzymane tutaj.

### E2 — σ_SR z rozrzutu prób (FST), fallback 1/√T jawnie oznaczony

- **Co unieważnia:** fallback zakłada szum iid i **zaniża** SR₀, czyli zawyża
  DSR. Każde DSR policzone fallbackiem jest optymistyczne.
- **Stan:** dziś wszystkie liczby DSR w repo pochodzą z fallbacku, bo licznik
  prób wynosi 0 i nie ma z czego liczyć rozrzutu. Zapisane w baseline jako
  `sigma_sr_source`.

### E3 — Limit ≤10 wariantów na hipotezę

- **Dlaczego tak:** przy N_eff=30 nawet SR 1,5 nie przechodzi bramki DSR na
  realnej długości danych. Limit 30 był matematycznie zabójczy.
- **Co unieważnia:** przekroczenie limitu może uczynić kartę **niecertyfikowalną
  niezależnie od tego, jak dobra jest** — i to jest treść False Strategy Theorem,
  nie usterka procedury.

### E4 — Zakaz strojenia pod wynik docelowy (reguła R2)

Żadna zmiana specyfikacji ani parametru po zobaczeniu P&L, jeśli motywem jest
zbliżenie się do 1–2% miesięcznie.

- **Co unieważnia:** złamanie tej reguły unieważnia **wszystko naraz** i nie
  zostawia śladu w żadnej metryce. Nie ma testu, który by to wykrył — dlatego
  jest to jedyne założenie w rejestrze utrzymywane wyłącznie dyscypliną.

---

## F. Dane i środowisko

### F1 — Databento GLBX.MDP3 jako jedyne źródło cen

- **Co unieważnia:** brak drugiego źródła to pojedynczy punkt awarii. Kontrola
  krzyżowa istnieje tylko dla **jednego miesiąca** (rekonstrukcja barów M1
  z transakcji, poprawka A4-10).
- **Ryzyko otwarte:** zmiana normalizacji GLBX.MDP3 po stronie dostawcy wymaga
  regeneracji `data/clean/`. Data pobrania jest przypięta w `data/manifest.md`.

### F2 — Wyniki zależą od wersji bibliotek

Baseline powstał na Python 3.11.15, polars 1.43.1, numpy 2.4.6, scipy 1.17.1,
arch 8.0.0 (`golden/srodowisko.txt`).

- **Co unieważnia:** zmiana generatora losowego w numpy albo algorytmu
  bootstrapu w `arch` przesunie warstwę walidacji **bez jednej linijki zmiany
  w tym repo**. To pierwsza rzecz do sprawdzenia przy niezgodnym `--sprawdz`.

---

## G. Wady wykryte i naprawione — wpisy historyczne

### G1 — ✅ NAPRAWIONE: odwrócony znak w ścieżce `arch` w `validation/spa.py`

**Wykryte** przez golden baseline, **naprawione** w commicie `7f681ef`
(R1, 03.08.2026).

`arch.bootstrap.SPA` oczekuje **strat** (mniej = lepiej), moduł podawał mu
**zwroty**. Testowana była hipoteza przeciwna do zamierzonej.

Fixture 400 obs × 6 wariantów, 500 replikacji, ziarno 7:

| Wejście | `arch` przed | `arch` po | fallback (niezmieniony) |
|---|---|---|---|
| sam szum | 0,898 | 0,248 | 0,303 |
| wariant z przewagą +0,30σ | **0,898** | **0,000** | 0,002 |

Identyczna p-wartość dla szumu i dla przewagi była rozstrzygająca — statystyka
nie zależała od tego, co miała mierzyć.

Odwrócenie widać też w drugą stronę. Osobny fixture (400 × 4, wszystkie warianty
przesunięte o −0,50σ, 300 replikacji, ziarno 4): przed poprawką ścieżka `arch`
dawała **p = 0,0000** dla puli, w której **każdy** wariant traci; po poprawce
0,5467, przy fallbacku 0,5681.

- **Wpływ na wnioski W001–W013: żaden.** SPA nie było użyte, licznik prób 0,
  żadna karta nie doszła do bramki, na której SPA działa.
- **Baseline:** `golden/ZMIANY.md` v2 — zmieniły się wyłącznie dwa klucze
  `walidacja.spa.*_arch.p`; oba klucze fallbacku bit w bit bez zmian.
- **Raport regresyjny:** `reports/R1_regresja_spa.md` z dowodem czerwieni testu
  przed poprawką.

### G1a — REGUŁA TRWAŁA: implementacja podstawowa i awaryjna testowane osobno

Najważniejszy wniosek z G1 jest szerszy niż sam znak. **Wszystkie** testy SPA
sprzed R1 wołały funkcję z `force_fallback=True`. Ścieżka domyślna — jedyna,
która działa produkcyjnie — nie była testowana w ogóle, więc 233 testy dawały
**fałszywe poczucie pokrycia**.

Odtąd każdy moduł z implementacją podstawową i awaryjną musi mieć:

1. testy **ścieżki domyślnej** na przypadkach o znanej odpowiedzi,
2. testy **ścieżki awaryjnej** na tych samych przypadkach,
3. test **zgodności obu** co do werdyktu.

Zgodność co do werdyktu, nie co do wartości — dwie implementacje bootstrapu mogą
dawać różne p-wartości, ale rozbieżny werdykt znaczy, że któraś testuje co innego.

### G2 — ✅ ZAMKNIĘTE: halt CME 2019–2021 zweryfikowany na danych

Patrz A3. Zweryfikowane empirycznie na MNQ, NQ i ES (Etap 2.5). Nie ma już
w rejestrze założenia kalendarzowego bez własnego sprawdzenia.

### G3 — ✅ PRZEETYKIETOWANE: `verify_continuity` nie jest bramką

Kryterium „skok ≥ |spread|" jest **nieidentyfikowalne** — nie odróżnia ruchu
rynku od błędu korekty. Zgłasza 17/29 granic MNQ przy dokładnie zerowym
rozrzucie offsetu. Rola zmieniona z PASS/FAIL na diagnostykę
(`golden/ZMIANY.md` v4); progu **nie zmieniano**, bo problem leży w konstrukcji
kryterium, nie w wartości progu.

O poprawności back-adjustu orzeka wyłącznie **niezmiennik stałości offsetu**
(zero rozrzutu w 90 z 90 kontraktów).

---

## Jak używać tego rejestru

1. **Przed zmianą w `engine/`** — sprawdź, czy dotyka któregoś założenia.
2. **Jeśli dotyka** — kolumna „co unieważnia" mówi, co przeliczyć.
3. **Po zmianie** — `python3 scripts/golden_baseline.py --sprawdz`; każda
   rozbieżność musi być zamierzona i opisana w commicie.
4. **Nowe założenie** dopisuj tylko wtedy, gdy przechodzi kryterium z nagłówka.
   Rejestr, który rośnie o wszystko, przestaje być czytany.
