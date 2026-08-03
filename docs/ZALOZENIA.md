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
- **Pewność:** wysoka (data z dokumentacji CME), ale **nikt tego nie sprawdził
  na naszych danych** — to jedyne założenie kalendarzowe przyjęte z dokumentacji
  bez własnej weryfikacji. Warte 20 minut przy okazji.

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

## G. Znane wady zamrożone świadomie

### G1 — Ścieżka `arch` w `validation/spa.py` ma odwrócony znak

`arch.bootstrap.SPA` oczekuje **strat** (mniej = lepiej), moduł podaje mu
**zwroty**. Testowana jest hipoteza przeciwna do zamierzonej: p = 0,898
identycznie dla czystego szumu i dla wariantu z przewagą +0,30σ.

- **Wpływ na dotychczasowe wnioski:** **żaden.** SPA nie było użyte w W001–W013,
  licznik prób wynosi 0, żadna karta nie doszła do bramki, na której SPA działa.
- **Status:** pozycja nr 1 planu refaktoru. Naprawa **świadomie zmieni**
  `hash_wynikow`; własny fallback (poprawny) jest w baseline jako punkt
  odniesienia dowodzący, że naprawiono znak, a nie przepisano test.

### G2 — Halt CME 2019–2021 przyjęty z dokumentacji bez weryfikacji na danych

Patrz A3. Jedyne założenie kalendarzowe bez własnego sprawdzenia.

---

## Jak używać tego rejestru

1. **Przed zmianą w `engine/`** — sprawdź, czy dotyka któregoś założenia.
2. **Jeśli dotyka** — kolumna „co unieważnia" mówi, co przeliczyć.
3. **Po zmianie** — `python3 scripts/golden_baseline.py --sprawdz`; każda
   rozbieżność musi być zamierzona i opisana w commicie.
4. **Nowe założenie** dopisuj tylko wtedy, gdy przechodzi kryterium z nagłówka.
   Rejestr, który rośnie o wszystko, przestaje być czytany.
