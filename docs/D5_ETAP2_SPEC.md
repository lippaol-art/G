# D5-B — zamrożona definicja identyfikowalności

> ## ⚠ ZMIANA ZAKRESU — RTH zamiast pełnej doby (przed zakupem)
>
> **Zmiana z pełnej doby na RTH nastąpiła po informacji o koszcie i zakresie
> infrastruktury, ale przed zakupem miesięcznej próbki oraz przed pomiarem VIF,
> przyszłych zwrotów i P&L. Ogranicza zakres wnioskowania D5 wyłącznie do RTH.**
>
> Definicja kanoniczna: **`09:30–16:00 America/New_York`**. Kod wyprowadza UTC
> ze strefy ET — **nie** wolno zapisywać `13:30–20:00 UTC` jako stałej, bo po
> zmianie czasu przesunęłoby to sesję o godzinę. Dla lipca 2026 (EDT) odpowiada
> to 13:30–20:00 UTC.
>
> ### Co zostaje bez zmian
> okno 60 s · wyznaczanie okien po `ts_recv` · główna zmienna `I_count` ·
> benchmark momentum · VIF pooled i per sesja · próg VIF < 5 · warunek ≥75%
> sesji · limit koncentracji jednej sesji 20%.
>
> ### Ograniczenie wnioskowania
> D5 odpowiada odtąd **wyłącznie** na pytanie: *czy nierównowaga zdarzeń
> agresora w RTH wnosi informację odróżnialną od równoczesnego momentum
> w RTH?* Wyniku **nie wolno** rozszerzać na ETH, sesję nocną, pełny Globex
> ani metaordery poza RTH. Jeśli D5-B przejdzie, H017 również dotyczy
> **wyłącznie RTH**; ETH wymagałoby osobnej karty i osobnego forwardu.

**Commitowane PRZED wyceną i zakupem.** Cokolwiek pokażą dane, ta specyfikacja
się nie zmienia. Poprzednik: `docs/D5_ETAP1_SPEC.md` (`41d3eee`), wynik
Etapu 1: `reports/D5_etap1_kontrole.md` — werdykt `D5-A GO`.

---

## 1. Próbka i granice zakupu

Ostatni kompletny miesiąc kalendarzowy przed zamrożeniem: **lipiec 2026**.

### Co już posiadamy — dokładne granice

| | |
|---|---|
| Plik | `data/raw/mnq_trades_2026-07-30.dbn.zst` |
| Zamówione okno | `2026-07-29T22:00:00Z` → `2026-07-30T21:00:00Z` |
| Faktyczny `ts_recv` | `2026-07-29 22:00:00.013066Z` → `2026-07-30 20:59:59.765673Z` |
| Rekordów | 1 696 891 |
| Koszt | 2,1240 USD |

Sesja `2026-07-30` jest już **development** i wchodzi do próbki miesięcznej.
Nie jest wykluczana.

### Podział zakupu, żeby nie płacić dwa razy za ten sam zakres

Trzy rozłączne przedziały UTC, sumujące się na cały lipiec bez nakładania:

| # | Od (UTC) | Do (UTC) | Status |
|---|---|---|---|
**ZASTĄPIONE przez podział RTH — patrz §1a.**

### 1a. Podział zakupu po zmianie na RTH — i trzy ustalenia z danych

Enumeracja sesji lipca **z naszych własnych danych**, nie z kalendarza:

| Grupa | Sesji | Status |
|---|---|---|
| 07-01 … 07-29 z pokryciem RTH | **21** | **do kupienia** |
| 07-30 | 1 | **posiadane** (pełna doba, zawiera RTH) |
| **Razem RTH w próbce** | **22** | |

Każda sesja to osobne zapytanie o oknie wyprowadzonym z ET 09:30–16:00.
Żadne nie nakłada się na posiadany plik: 07-30 jest wyłączona z zakupu.

#### Ustalenie 1 — sesji z RTH jest 22, nie 23

`2026-07-31` ma w naszym `ohlcv-1m` **120 barów i ZERO w RTH** (pokrywa tylko
18:00–19:59 ET, czyli wieczór 07-30). Nie ma odniesienia do **obowiązkowej**
rekonstrukcji OHLCV, która wg §10 musi poprzedzić VIF.

**Wykluczona z zakupu.** Powód jest **weryfikacyjny, nie budżetowy**: sesji,
której nie da się skontrolować, nie wolno wpuścić przed pomiarem. Gdyby powodem
były pieniądze, byłoby to zawężanie pod budżet — tu nim nie jest, bo 26,41 USD
mieści się w limicie także bez tego wykluczenia.

#### Ustalenie 2 — `2026-07-03` to sesja skrócona

RTH kończy się o **12:59 ET** zamiast 15:59 — 210 barów zamiast 390. To
obserwowane święto 4 lipca (w 2026 przypada w sobotę, więc rynek zamyka się
wcześniej w piątek 3 lipca).

**Kupowana i raportowana, ale wyłączona z mianownika „kompletnych sesji".**
Definicja przyjęta tu i teraz: **kompletna sesja = 390 dostępnych minut RTH.**

| | Liczba |
|---|---|
| sesji RTH w próbce | 22 |
| **kompletnych (390 min)** | **21** |
| skróconych | 1 (07-03) |

Warunek „≥75% kompletnych sesji z VIF < 5" stosuje się do **21**.

#### Ustalenie 3 — defekt flagi `short_day` w naszym pipeline

`2026-07-03` ma `short_day = False`, mimo że RTH kończy się trzy godziny
wcześniej. **Flaga nie wykryła skróconej sesji.** To defekt naszego kalendarza,
nie danych dostawcy. Odnotowany jako otwarta pozycja — nie naprawiam go teraz,
bo dotknięcie `engine/sessions.py` przed pomiarem zmieniłoby baseline w środku
Etapu 2.

---

## 2. Limit wydatku

| | |
|---|---|
| **Maksymalny dodatkowy wydatek Etapu 2** | **30,00 USD** |
| **Wycena 21 sesji RTH (2026-08-03)** | **26,4060 USD** — mieści się |
| Rekordów | 21 096 133 |
| Stawka | 1,2517 USD/mln — **identyczna** jak w Etapie 1 |

Limit jest bezpiecznikiem **tego zapytania**, nie globalnym budżetem projektu.
Budżet Databento to odnawialny kredyt 125 USD; środki własne wydane na dane:
**0 USD**.

Wycena `metadata.get_cost` wykonywana **ponownie tuż przed pobraniem**.
Powyżej 30,00 USD **zatrzymuję się** — nie skracam miesiąca, nie wybieram
mniej aktywnych dni, nie zmieniam schematu.

Reguła z korekty Etapu 1 obowiązuje: zapisuję konkretną wycenę dla dokładnego
zapytania, koszt per milion rekordów, limit z marginesem i datę wyceny.

---

## 3. Jednostka agresora

**`candidate_aggressor_event`** — *deterministyczna grupa wypełnień o wspólnym
kluczu technicznym, używana jako empiryczne przybliżenie jednego zdarzenia
agresora.*

**NIE** „zidentyfikowane pojedyncze zlecenie konkretnego uczestnika". Nazwa jest
częścią specyfikacji: nie wolno twierdzić, że grupa jest udowodnionym
pojedynczym zleceniem rynkowym ani metaorderem.

### Klucz grupowania

```
candidate_aggressor_event  =  (ts_event, sequence, side)
```

Dla każdego zdarzenia zapisujemy: `event_timestamp` (`ts_event`),
`receive_timestamp` (`ts_recv`, **maksimum** w grupie — moment, w którym całe
zdarzenie stało się znane), `side`, łączny `size`, liczbę wypełnień, cenę
minimalną i maksymalną oraz klucz grupowania.

### ⚠ NA CZYM TA REGUŁA STOI — i czego NIE udało się potwierdzić

Wymóg brzmiał: reguła ma **wynikać z semantyki CME/Databento**. Spełniam go
**częściowo** i mówię to wprost, zanim wydam pieniądze.

**Czego NIE mam:** dokumentacja Databento zwraca HTTP 403 dla pobrania
automatycznego, a `databento_dbn` nie niesie docstringów pól. **Nie znalazłem
zdania producenta mówiącego, że rekordy dzielące `sequence` należą do jednego
zlecenia agresora.**

**Co mam — i dlaczego uważam to za wystarczające:**

1. **`flags` jest zawsze 0** w tych danych, więc udokumentowany znacznik
   `F_LAST` (ostatnia wiadomość zdarzenia) **nie jest dostępny**. Droga
   flagowa odpada nie z wyboru, tylko z braku.
2. `sequence` to **udokumentowany numer sekwencyjny CME**, nie heurystyka
   czasowa. Nie grupuję „po podobnym timestampie".
3. Databento dokumentuje, że **MDP 3.0 publikuje informację o zleceniu
   agresora** wprost, w odróżnieniu od innych feedów L3.
4. **Walidacja empiryczna na 1 479 365 grupach** z posiadanej sesji:

   | Kontrola | Wynik |
   |---|---|
   | grupy ciągłe w kolejności `ts_recv` | **1 479 365 z 1 479 365** |
   | grupy mieszające obie strony agresji | 26 (**0,0018%**) |
   | grupy wielocenowe z cenami monotonicznymi w stronę agresora | **99,98%** (134 220 z 134 245) |

   Monotoniczność jest tu argumentem rozstrzygającym: agresywne kupno
   zamiatające książkę **musi** wypełniać się po cenach niemalejących.
   Przykład z danych — jedno zdarzenie, cztery poziomy:

   ```
   ts_recv 20:27:08.220109514  seq 558767065  B  28363.00 ×3
   ts_recv 20:27:08.220109514  seq 558767065  B  28363.25 ×1
   ts_recv 20:27:08.220109514  seq 558767065  B  28363.50 ×3
   ts_recv 20:27:08.220109514  seq 558767065  B  28363.75 ×3
   ```

**Dlaczego `side` wchodzi do klucza.** Nie dla wygody: to czyni niezmiennik
„grupa nigdy nie miesza stron" **strukturalnym, nie życzeniowym**. Rozstrzyga
też deterministycznie 26 grup mieszanych, dzieląc je zamiast odrzucać.

**Ryzyko resztkowe, nieusunięte:** dwa zlecenia agresora **tej samej strony**
w jednym pakiecie zostaną scalone w jedno zdarzenie. Górne ograniczenie
częstości: 21 633 grupy z powtórzoną ceną, czyli **1,46%** wszystkich grup.
Skutek jest **konserwatywny dla `I_count`** — zaniża liczbę zdarzeń po obu
stronach mniej więcej proporcjonalnie, więc rozcieńcza nierównowagę, a nie
ją zawyża.

**Status reguły: zweryfikowana empirycznie, nie potwierdzona dokumentacją
producenta.** Gdyby właściciel uznał to za niewystarczające, właściwym
momentem na zatrzymanie jest teraz — przed zakupem.

### Niezmienniki, sprawdzane w kodzie i testami na ręcznych przypadkach

1. suma `size` zdarzeń = suma `size` wypełnień,
2. liczba zdarzeń ≤ liczba wypełnień,
3. każde wypełnienie należy do **dokładnie jednego** zdarzenia,
4. żadne zdarzenie nie łączy dwóch stron (**strukturalnie**, przez klucz),
5. rekordy `side == NONE` **nie uczestniczą** w wyznaczaniu znaku.

---

## 4. Główna zmienna — nierównowaga LICZBY ZDARZEŃ

```
I_count = (N_buy − N_sell) / (N_buy + N_sell)          zakres [−1, +1]
```

`N_buy`, `N_sell` — liczba **zdarzeń agresora**, nie wypełnień i nie wolumenu.

Uzasadnienie mechanizmem: długa pamięć dotyczy **znaku kolejnych zleceń
rynkowych** (Lillo–Mike–Farmer), a nie ich wielkości. Liczenie po wypełnieniach
mierzyłoby fragmentację płynności; liczenie po wolumenie mierzyłoby coś innego
niż to, co model opisuje.

`side == NONE`: raportowane osobno, wykluczone z licznika znaku. Przy
kompletności 99,9999% (Etap 1) bez znaczenia ekonomicznego.

### Wersja wolumenowa — wyłącznie kontrola opisowa

```
I_volume = (V_buy − V_sell) / (V_buy + V_sell)
```

**ZAKAZ ZAPISANY PRZED DANYMI:** nie wolno zastąpić `I_count` wersją
`I_volume` po zobaczeniu wyników, jeśli wolumenowa da korzystniejszy VIF.
Gdyby `I_count` nie przeszła, a `I_volume` przeszła, werdykt dla D5-B brzmi
**NO-GO w zadeklarowanej postaci**, a wersja wolumenowa jest **obserwacją
wygenerowaną przez dane**, wymagającą nowej historii albo forwardu.

### Obsługa grup niejednoznacznych

Klucz zawiera `side`, więc grupa **nie może** zawierać obu stron. Gdyby mimo to
powstała rozbieżność (np. przy zmianie danych): **nie przypisywać do strony
dominującej** — oznaczyć jako niejednoznaczną, **wykluczyć z `I_count`**,
zachować jej wolumen w raporcie jakości i podać udział takich grup.

### Testy niezmienników — przed VIF, nie po

1. suma `size` po agregacji = suma `size` raw,
2. każde wypełnienie należy do **dokładnie jednej** grupy,
3. grupa nie zawiera obu stron,
4. liczba grup ≤ liczba wypełnień,
5. ceny i znaczniki czasu pozostają uporządkowane,
6. wynik **nie zależy od kolejności wejściowego pliku**,
7. ponowne uruchomienie daje **identyczny** wynik,
8. rekordy niejednoznaczne są **raportowane, nie ukrywane**.

---

## 4a. Kontrole A / B / C

| | Definicja | Rola |
|---|---|---|
| **A** | `I_count` po `candidate_aggressor_event` | **główna — jedyne źródło werdyktu** |
| **B** | nierównowaga po **surowych wypełnieniach** | kontrola fragmentacji |
| **C** | `I_volume` — signed volume imbalance | kontrola wolumenowa |

**B i C nie mogą zastąpić A po zobaczeniu wyniku.**

| Układ wyników | Interpretacja |
|---|---|
| A, B, C zgodne | niepewność grupowania prawdopodobnie niematerialna |
| A daje GO, B/C nie | **`INCONCLUSIVE`** |
| GO zależne wyłącznie od niepotwierdzonej agregacji | **brak H017** do czasu wyjaśnienia |
| A daje NO-GO, C daje GO | D5-B pozostaje **NO-GO** w zamrożonej postaci; C staje się obserwacją wygenerowaną przez dane |

---

## 5. Okno obserwacji

**60 sekund**, wyrównane do pełnych minut **według `ts_recv`**.

Uzasadnienie: zgodne z minimalną rozdzielczością silnika, wykonalne dla
retailu, nie konkuruje w horyzoncie sub-sekundowym, mieści się w deklarowanym
zakresie „dziesiątki sekund do minut", daje obserwacje rozłączne.

`ts_recv` — bo to on wyznacza moment, w którym informacja była **dostępna
odbiorcy**. Ustalenie Etapu 1: rekonstrukcja `ohlcv-1m` zgadza się co do
jednego bara tylko na `ts_recv`; na `ts_event` daje 8/6/20 niezgodności.

Czas w ET przez `America/New_York`, bez stałego offsetu. Każde okno przypisane
do `trade_date` przez `engine.sessions`.

**Nie testuję równolegle 10 s, 30 s, 2 min ani 5 min.** To byłyby warianty
wybrane przed kartą.

---

## 6. Benchmark momentum

```
m_t = log(P_last / P_first)
```

`P_first`, `P_last` — cena pierwszego i ostatniego wypełnienia w oknie,
w kolejności `(ts_recv, sequence)`.

**Okno bez transakcji jest obserwacją brakującą, nie zerowym zwrotem.**

Raportowane obok: całkowity wolumen, liczba zdarzeń agresora, pora dnia,
`|m|`, `sign(m)`.

---

## 7. Test identyfikowalności

Jedno pytanie: **czy `I_count` jest statystycznie odróżnialne od równoczesnego
momentum ceny?**

Model pomocniczy — **nie zawiera przyszłego zwrotu**:

```
I_count ~ m + |m| + m² + sign(m) + log(1 + volume) + efekty pory dnia
```

Raportowane: `R²`; VIF dla `I_count`; VIF per sesja; mediana dziennych VIF;
percentyle VIF; pooled VIF po usunięciu efektów pory dnia; liczba okien;
liczba sesji; koncentracja obserwacji na sesję.

---

## 8. Zamrożony warunek GO/NO-GO

`D5-B GO` **tylko** gdy `I_count` spełnia **wszystkie**:

1. pooled VIF < 5,
2. mediana dziennego VIF < 5,
3. ≥ 75% kompletnych sesji ma VIF < 5,
4. wynik nie zależy wyłącznie od jednego segmentu dnia,
5. próbka zawiera wystarczającą zmienność **obu** stron agresji,
6. żadna sesja nie odpowiada za > 20% całkowitej zmienności `I_count`.

**`INCONCLUSIVE`**, jeśli pooled VIF < 5, ale identyfikacja pochodzi głównie
z różnic **między** sesjami albo porami dnia. To jest lekcja z D1: tam cała
identyfikacja siedziała w wolnym trendzie i dlatego nie znaczyła nic.

---

## 9. Czego Etap 2 NIE mierzy

Przyszłych zwrotów, korelacji z przyszłym P&L, skuteczności kierunku,
Sharpe'a, profit factora, optymalnego progu nierównowagi, najlepszego segmentu
dnia, najlepszego horyzontu utrzymania, strategii long/short.

**Licznik prób pozostaje 0.**

---

## 10. Reprodukcja

Zachowane pliki surowe; SHA-256 każdego; koszt; parametry zapytań; rzeczywista
liczba rekordów; rozmiar; wersja biblioteki; dokładne granice UTC i sesje ET.
Kontrola braku duplikatów na granicach z `2026-07-30`. Rekonstrukcja
`ohlcv-1m` dla **całego miesiąca** i porównanie z posiadanymi barami — **każda
niezgodność wyjaśniona przed liczeniem VIF**.

---

## 11. Status statystyczny

**Cały lipiec 2026 jest development setem.** Nie jest OOS i nie stanie się OOS
po zamrożeniu H017.

| Wynik | Co dalej |
|---|---|
| `D5-B GO` | dopiero wtedy powstaje H017; mechanizm, znak, okno i wykonanie zamrożone; następnie pre-flight trwałości znaku na wykonalnym horyzoncie; dopiero potem pierwszy backtest i **próba nr 1** |
| `NO-GO` | D5 odrzucone **bez** H017; licznik prób 0; nie kupujemy kolejnych miesięcy; nie zmieniamy okna ani definicji |

**H017 nie powstaje na tym etapie. P&L nie jest mierzony.**
