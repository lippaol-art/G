# Audyt wykonalności kierunku D5 — przepływ zleceń i odpowiedź płynności

**Werdykt: `D5 WYKONALNY` — można rozważyć kartę i zakup minimalnej próbki.**
Z dwoma zastrzeżeniami zapisanymi w sekcji 12, których nie da się usunąć bez
danych.

Audyt **nie zużywa próby** i **nie kupuje danych**. Wycena wyłącznie przez
`metadata.get_cost` i `metadata.get_billable_size` — obie operacje są
read-only i nie obciążają konta.

---

## 1. Rozstrzygnięcie mechanizmu — jeden, przed danymi

Opis D5 w briefie zawierał dwie **przeciwne** historie. Trzeba było wybrać
jedną przed zakupem, bo testowanie obu jako wariantów jednej karty byłoby
gwarantowanym overfittingiem: przy dwóch przeciwnych znakach jakiś wynik
zawsze „wychodzi".

| | **A. Kontynuacja metaorderu** | **B. Absorpcja i wyczerpanie** |
|---|---|---|
| Mechanizm | duże zlecenie realizowane w częściach; wykonawca musi dokończyć wolumen | agresja nie rusza ceny, bo absorbuje ją silny pasywny kontrahent; po wyczerpaniu agresorów cena wraca |
| Przewidywany znak | **ten sam** co nierównowaga agresji | **przeciwny** do nierównowagi agresji |
| Wymagane obserwacje | strona inicjująca, wielkość, sekwencja | jw. **plus** trwałość i odnawianie płynności pasywnej |
| Kontrprzewidywanie | brak autokorelacji znaku zleceń | agresja bez ruchu ceny nie zapowiada powrotu |
| Horyzont | dziesiątki sekund do minut | nieokreślony, zależny od momentu wyczerpania |
| Warunek zaniku | metaordery przestają być dzielone; wykonanie staje się natychmiastowe | absorbujący uczestnik znika albo przestaje odnawiać |
| Źródło | Lillo–Mike–Farmer (2005) i replikacja *Phys. Rev. Lett.* 131, 197401 (2023); Lillo & Farmer — Hurst ≈ 0,7 dla znaków zleceń; Cont–Kukanov–Stoikov | głównie literatura praktyczna; brak kanonicznego testu ilościowego |
| **Rozróżnialne na danych anonimowych?** | **TAK** — autokorelacja znaku jest wielkością agregatową, nie wymaga tożsamości | **NIE** — wymaga stwierdzenia, że *konkretny* duży pasywny uczestnik zostanie wyczerpany |

### Wybór: **A — kontynuacja metaorderu**. Znak dodatni.

Trzy powody, wszystkie niezależne od tego, która historia „zarabia" (czego nie
sprawdzałem):

1. **Łańcuch przyczynowy jest zamknięty i zreplikowany.** Długa pamięć znaku
   zleceń — `C(τ) ∝ τ^(−γ)`, Hurst ≈ 0,7 — to jeden z najlepiej powtórzonych
   faktów mikrostruktury, a model Lillo–Mike–Farmer wiąże go ilościowo
   z rozkładem długości metaorderów (`γ ≈ α − 1`, potwierdzone bezpośrednio
   w 2023 na danych mikroskopowych).
2. **Absorpcja jest nierozstrzygalna na danych anonimowych.** `trades` i MBP
   pokazują stronę inicjującą, nierównowagę, reakcję ceny, głębokość
   i anulowania. **Nie pokazują**, czy uczestnikiem jest fundusz, czy działa
   algorytm wykonawczy, czy zlecenie jest częścią większego zlecenia
   macierzystego ani czy ktokolwiek *musi* kontynuować. Historia B wymaga
   właśnie tego, czego dane nie zawierają.
3. **Kontynuacja daje falsyfikowalne przewidywanie o znanym znaku z góry.**
   Absorpcja daje znak zależny od nieobserwowalnego stanu — czyli w praktyce
   swobodę wyboru znaku po zobaczeniu wyniku.

**Historia B zostaje odrzucona jako kierunek**, nie odłożona. Powrót do niej
wymagałby danych identyfikujących uczestnika, których na tym rynku nie ma.

---

## 2. Zawartość schematów — z biblioteki, nie z pamięci

Pola odczytane z zainstalowanego `databento_dbn` 0.82.0, nie z dokumentacji
webowej (ta zwraca 403 dla pobrania automatycznego).

### `trades` — rekord `TradeMsg`

```
ts_event, ts_recv, ts_in_delta, ts_out, sequence,
price, size, side, action, depth, flags,
instrument_id, publisher_id, rtype
```

| Pole | Rola w D5 |
|---|---|
| `ts_recv` | znacznik odbioru — **to on wyznacza granicę okna obserwacji**, bo tylko on jest dostępny w czasie rzeczywistym |
| `ts_event` | znacznik zdarzenia po stronie giełdy |
| `ts_in_delta` | opóźnienie wejściowe — pozwala oszacować realistyczne opóźnienie |
| `side` | **strona agresora**; wartości `BID`, `ASK`, `NONE` |
| `size` | wielkość transakcji |
| `sequence` | rekonstrukcja kolejności |

### ⚠ Ryzyko, którego nie da się zamknąć bez próbki

Enum `Side` dopuszcza **`NONE`**. Nie wiem, jaki odsetek transakcji MNQ ma
`side` wypełnione — i **nie udaję, że wiem**. Jeśli `side` jest często `NONE`,
poziom A (nierównowaga agresji) staje się niekompletny i całą konstrukcję
trzeba przemyśleć.

To jest **pierwsze pytanie do rozstrzygnięcia za 1,75 USD**, przed jakąkolwiek
większą decyzją.

### Czego `trades` nie zawiera

Głębokości, wielkości na poziomach, anulowań, odnawiania płynności pasywnej.
Wszystko to należy do MBP/MBO — i wszystko to jest potrzebne **wyłącznie
historii B**, którą właśnie odrzuciliśmy.

---

## 3. Minimalny potrzebny schemat — trzy poziomy informacji

| Poziom | Co mierzy | Minimalny schemat | Potrzebny dla kontynuacji? |
|---|---|---|---|
| **A** | nierównowaga agresji | `trades` | **TAK — i to wystarczy** |
| **B** | reakcja ceny na agresję | `trades` + BBO (`tbbo`) | pomocniczy, nie konieczny |
| **C** | absorpcja i odnawianie płynności | MBP-1 / MBP-10 / MBO | **NIE** — potrzebny tylko historii B |

**Wybór historii A czyni MBP zbędnym.** To jest bezpośrednia i największa
oszczędność wynikająca z rozstrzygnięcia mechanizmu — i dowód, że warto było
wybrać przed zakupem, a nie po.

Nie kupuję MBP „bo zawiera więcej danych". Pole, bez którego wybrany mechanizm
byłby nierozpoznawalny, to `side` w `trades` — i tylko ono.

---

## 4. Inwentaryzacja: czego już nie mamy

Sprawdzone bezpośrednio w `data/raw/` i w manifeście.

**Nie posiadamy żadnych danych `trades`, MBP ani MBO.** Miesiąc `trades` MNQ
figurował w planie Etapu 1 z wyceną 23,77 USD, ale **nigdy nie został kupiony
ani pobrany** — brak plików, brak wpisu w manifeście, brak skryptu
`verify_bars.py`.

Konsekwencja korzystna: **żadna próbka `trades` nie została jeszcze obejrzana**,
więc pierwsza kupiona próbka może zostać przeznaczona świadomie — na
infrastrukturę albo na development — bez długu ekspozycji z przeszłości.

Posiadane dane: `ohlcv-1m` dla MNQ, NQ, ES i dziesięciu instrumentów K6.
Wydatek Gen1 łącznie: **7,82 USD**.

---

## 5. Wycena bez zakupu

`metadata.get_cost` i `metadata.get_billable_size`, dataset `GLBX.MDP3`,
symbol ciągły `MNQ.v.0`. Dzień odniesienia 2025-03-03, miesiąc 2025-03.

| Schemat | 1 dzień | 1 tydzień | 1 miesiąc | Rekordów/mies. | Rozmiar/mies. |
|---|---|---|---|---|---|
| **`trades`** | **1,75** | 9,30 | **29,83** | 23,8 mln | **1,14 GB** |
| `tbbo` | 2,92 | 15,50 | 49,71 | 23,8 mln | 1,91 GB |
| `mbp-1` | 3,68 | 18,08 | 59,07 | 440 mln | **35,2 GB** |
| `mbo` | 4,67 | 24,06 | 75,27 | 802 mln | **44,9 GB** |
| `mbp-10` | 7,18 | 36,37 | 115,14 | 672 mln | **247,3 GB** |
| `bbo-1s` | 0,11 | — | — | — | — |

Kwoty w USD.

### Twarde ograniczenie infrastrukturalne, niezależne od ceny

Dostępne miejsce na dysku: **28 GB**.

- `trades` 1,14 GB/mies. — **mieści się**
- `tbbo` 1,91 GB/mies. — **mieści się**
- `mbp-1` 35,2 GB/mies. — **nie mieści się**
- `mbo` 44,9 GB/mies. — **nie mieści się**
- `mbp-10` 247,3 GB/mies. — **nie mieści się o rząd wielkości**

Nawet gdyby budżet pozwalał, MBP-10 jest niewykonalny w tym środowisku. Kolejny
argument, że wybór historii A był konieczny, nie wygodny.

### Zawężenie okna obniża koszt proporcjonalnie

| Zakres 2025-03-03 | Koszt |
|---|---|
| cała doba | 1,75 |
| RTH 14:30–21:00 UTC | 1,34 |
| ostatnia godzina RTH (15:00–16:00 ET) | **0,23** |

⚠ **Poprawka do własnego rachunku.** Pierwsza wersja ekstrapolowała rok
z jednego dnia i dawała ~57 USD. To było **zawyżone i policzone na złym
oknie**: stała ramka 20:00–21:00 UTC to przez pół roku godzina **po**
zamknięciu RTH, a nie ostatnia godzina sesji — różnica bierze się ze zmiany
czasu. Po zakotwiczeniu okna w ET i pomiarze na pięciu dniach z różnych
kwartałów:

| Dzień | Okno UTC | Koszt |
|---|---|---|
| 2025-03-03 | 20:00–21:00 | 0,2287 |
| 2025-06-11 | 19:00–20:00 | 0,1058 |
| 2025-09-16 | 19:00–20:00 | 0,0129 |
| 2025-12-02 | 20:00–21:00 | 0,0624 |
| 2026-02-10 | 20:00–21:00 | 0,0931 |

Średnia **0,1006 USD/sesję** → rok w oknie jednogodzinnym ≈ **25 USD**, nie 57.
Rozrzut jest duży (0,013–0,229), więc to nadal szacunek rzędu wielkości.

Dla porównania: `trades` przez cały 2025 bez zawężenia — **271,66 USD**.

---

## 6. Wykonalność czasowa — i dlaczego to nie jest HFT

Horyzont z literatury:

- powiązanie nierównowagi przepływu z kolejnymi zwrotami jest silne
  **w skali dziesiątek sekund**,
- człony wpływu krzyżowego niosą informację prognostyczną **do kilku minut**,
  po czym szybko zanikają,
- na kontraktach terminowych CME wpływ narasta przez pierwsze minuty i odwraca
  się w skali doby.

**To nie jest reżim mikrosekundowy.** Sygnał liczony po zamknięciu okna
obserwacji i wykonany z konserwatywnym opóźnieniem mieści się w horyzoncie,
w którym literatura widzi jeszcze predykcyjność.

### Próg kosztowy w punktach bazowych — niski

Kontrakt MNQ przy 20 000 punktach to 40 000 USD nominału (mnożnik 2 USD/pkt).
Koszt bazowy 2,20 USD RT to:

```
2,20 / 40 000 = 0,55 bp
stress ×2      = 1,10 bp
```

Przewaga rzędu pojedynczych punktów bazowych wystarcza do pokrycia kosztów.
To **korzystna asymetria** wynikająca z dużego nominału wobec stałej opłaty —
odwrotnie niż przy strategiach o wysokiej częstotliwości na małym nominale.

### Warunek zamrożenia horyzontu

Horyzont **nie może** zostać dobrany po obejrzeniu danych. Deklaracja z góry,
z literatury:

- okno obserwacji nierównowagi: **60 s**,
- pierwszy możliwy moment wejścia: bezpośrednio po zamknięciu okna,
  z konserwatywnym opóźnieniem,
- horyzont wyniku: **300 s** (5 min) — górna granica przedziału, w którym
  literatura widzi predykcyjność.

---

## 7. Jednostka niezależności — i dlaczego to obniża pozorną przewagę D5

Największa deklarowana zaleta D5 w briefie brzmiała „bardzo wysoka
częstotliwość okazji". **Ta zaleta jest w dużej mierze pozorna.**

Sto sygnałów z jednej sesji dzieli ten sam reżim, tę samą zmienność, te same
informacje makro i **często ten sam metaorder** — czyli dokładnie ten obiekt,
którego mechanizm dotyczy. To nie jest sto niezależnych obserwacji.

Karta D5 musi więc raportować **osobno**:

- liczbę sygnałów,
- liczbę sesji,
- liczbę niezależnych klastrów,
- koncentrację sygnałów na sesję,
- efektywne N przy bootstrapie klastrowanym po sesji.

**Konsekwencja:** jednostką niezależności jest sesja, czyli ~250 rocznie —
**dokładnie ten sam profil, co miał D1**. Forward musi trwać minimum
12 miesięcy niezależnie od tego, czy 400 surowych sygnałów zbierze się
w kilka tygodni.

Odnotowuję to jako korektę własnej oceny z briefu: D5 dostał tam 5/5 za liczbę
okazji, a przy poprawnej jednostce niezależności zasługuje na tyle samo,
co D1 — nie więcej.

---

## 8. Benchmarki obowiązkowe

D5 musi wykazać wartość dodaną ponad **wszystkie** poniższe, łącznie:

| # | Benchmark | Dlaczego |
|---|---|---|
| 1 | momentum ceny w oknie obserwacji | najbliższy konkurent; nierównowaga jest z nim silnie skorelowana |
| 2 | sama nierównowaga wolumenu agresywnego (bez wagi wielkości) | oddziela „ile" od „jak zważone" |
| 3 | wolumen | kontrola aktywności |
| 4 | zmienność | Gen1: zmienność przewiduje amplitudę |
| 5 | spread bid–ask | kontrola stanu płynności |
| 6 | pora dnia | silny efekt sezonowy wewnątrzdzienny |

**Reguły rozstrzygające, zapisane przed pomiarem:**

- jeśli „absorpcja" nie dodaje nic ponad samą nierównowagę przepływu — nie jest
  nowym mechanizmem (i tak jest odrzucona w sekcji 1),
- **jeśli nierównowaga przepływu nie dodaje nic po kosztach ponad momentum
  ceny — D5 upada.**

---

## 9. Budżet parametrów — po jednym z każdego

D5 ma ogromny potencjał overfittingu: długość okna, próg nierównowagi,
definicja absorpcji, horyzont, pora dnia, minimalny wolumen, spread, głębokość,
agregacja, reguła wyjścia. **Zakaz przeszukiwania siatką jest bezwzględny.**

| Decyzja | Wartość | Skąd |
|---|---|---|
| długość okna obserwacji | **60 s** | skala „dziesiątek sekund" z literatury OFI |
| sposób liczenia agresji | **nierównowaga wolumenu ważona stroną agresora**: `(V_kupna − V_sprzedaży) / (V_kupna + V_sprzedaży)` | definicja kanoniczna, bez parametru |
| pomiar reakcji ceny | zmiana ceny środkowej w oknie | bez parametru |
| horyzont wyniku | **300 s** | górna granica predykcyjności z literatury |
| kierunek przewidywania | **dodatni** (kontynuacja) | sekcja 1 |
| wariant awaryjny | **jeden**: okno 30 s zamiast 60 s, wyłącznie jako kontrola niepewności pomiarowej | — |

Wszystkie decyzje podjęte **bez danych**. Warunek z punktu 9 audytu spełniony:
gdyby ich nie dało się podjąć bez danych, D5 byłby niezdefiniowany i nie
wolno by było kupować próbki.

---

## 10. Warunki pozytywnego audytu — stan

| # | Warunek | Stan |
|---|---|---|
| 1 | jeden mechanizm i jeden znak | ✅ kontynuacja, znak dodatni |
| 2 | dokładne pola danych dostępne | ✅ `TradeMsg` z `side`, `size`, `ts_recv`, `sequence` |
| 3 | minimalny schemat znany | ✅ `trades` |
| 4 | horyzont wykonalny dla retailowego MNQ | ✅ dziesiątki sekund–minuty; próg kosztowy 0,55 bp |
| 5 | sygnał liczony point-in-time | ✅ zamknięte okno na `ts_recv` |
| 6 | benchmarki zadeklarowane | ✅ sześć, sekcja 8 |
| 7 | parametry zamrażalne przed wynikiem | ✅ sekcja 9 |
| 8 | koszt minimalnej próbki akceptowalny | ✅ 1,75 USD na start |
| 9 | forward ≥ 12 miesięcy możliwy | ✅ |
| 10 | droga do certyfikacji przez niezależne sesje | ✅ ~250 sesji rocznie, jak D1 |

**Wszystkie siedem warunków obowiązkowych spełnione.**

---

## 11. Plan zakupu etapowego — 32 USD do decyzji GO/NO-GO

Nie proponuję kupna miesiąca „na wszelki wypadek". Każdy etap odpowiada na
jedno pytanie i warunkuje następny.

### Etap 1 — infrastruktura · **1,75 USD** · 1 dzień `trades`

Pytania: czy `side` jest wypełnione i w jakim odsetku; jaki jest rozkład
`Side.NONE`; czy parser działa; ile trwa przetworzenie; czy `ts_recv`
i `sequence` pozwalają odtworzyć kolejność.

**Zero pomiaru wyniku.** Dzień wybrany mechanicznie: **pierwsza pełna sesja
ostatniego zamkniętego miesiąca kalendarzowego** — nie dlatego, że była
zmienna albo ciekawa.

Kryterium przejścia: `side` wypełnione w ponad 95% transakcji.

### Etap 2 — identyfikowalność · **~30 USD** · 1 miesiąc `trades`

Jedno pytanie, i jest to **lekcja z D1 zastosowana przed wydaniem większych
pieniędzy**: czy nierównowaga przepływu daje się statystycznie odróżnić od
momentum ceny w tym samym oknie?

Miara: `R²` pomocnicze z regresji nierównowagi na zestaw kontrolny i wynikający
z niego VIF — dokładnie ta sama procedura, która zabiła D1.

**Nadal zero pomiaru wyniku.** Miesiąc wybrany mechanicznie: ostatni zamknięty
miesiąc kalendarzowy.

Kryterium przejścia: **VIF < 5** wewnątrz miesiąca. Powyżej — D5 dzieli los D1
i zostaje zamknięty za 32 USD zamiast za kilkaset.

### Etap 3 — dopiero po zielonym 1 i 2

Decyzja o próbce deweloperskiej, z osobną zgodą. Orientacyjnie: rok `trades`
w oknie jednogodzinnym ≈ 25 USD (pomiar na pięciu dniach), pełny rok bez
zawężenia 271,66 USD.

**Łączny wydatek do rozstrzygnięcia GO/NO-GO: ~32 USD.** Dla porównania cała
pierwsza generacja kosztowała 7,82 USD i zamknęła osiem kart.

---

## 12. Dwa zastrzeżenia, których nie da się usunąć bez danych

Werdykt jest pozytywny, ale nie bezwarunkowy. Dwie rzeczy trzeba powiedzieć
wprost, żeby decyzja o wydatku była świadoma.

### 12.1 Pytanie o przyrost ponad momentum jest blockerem D1 w innym przebraniu

Nierównowaga przepływu jest silnie skorelowana ze zwrotem w tym samym oknie —
to ta sama klasa problemu, która zamknęła D1.

**Jest jednak istotna różnica strukturalna.** W D1 współliniowość była
**algebraiczna i nieusuwalna**: `ΔE = K·r` jest z definicji przeskalowanym `r`.
W D5 jest **empiryczna**: nierównowaga i zwrot mogą się rozjechać, i to właśnie
przypadki rozjazdu — duża agresja przy małym ruchu ceny — są przypadkami
interesującymi.

Dlatego D1 dało się zamknąć na kartce, a D5 nie da się. **Etap 2 istnieje
dokładnie po to**, żeby odpowiedzieć na to pytanie za 30 USD, zanim wyda się
więcej.

### 12.2 To jest najbardziej zatłoczony sygnał w całej mikrostrukturze

Nierównowaga przepływu jest najlepiej przebadanym i najszerzej stosowanym
sygnałem mikrostrukturalnym. W horyzoncie, w którym jest najsilniejszy —
poniżej sekundy — **nie mamy z kim konkurować i nie próbujemy**.

Zakład brzmi: czy w horyzoncie dziesiątek sekund do minut, po kosztach i przy
retailowym opóźnieniu, zostaje cokolwiek. Literatura z lat 2010+ o wyprzedzaniu
przepływów jest w tej sprawie raczej sceptyczna.

**To jest uczciwie otwarte pytanie, a nie przewidywana wygrana.** 32 USD to
proporcjonalna cena za odpowiedź.

---

## 13. Werdykt

# `D5 WYKONALNY — można rozważyć kartę i zakup minimalnej próbki`

| | |
|---|---|
| **Mechanizm** | kontynuacja metaorderu (dzielenie zleceń, długa pamięć znaku) |
| **Przewidywany znak** | dodatni — ten sam co nierównowaga agresji |
| **Schemat** | `trades` (GLBX.MDP3), MBP **niepotrzebny** |
| **Pola** | `ts_recv`, `ts_event`, `side`, `size`, `sequence`, `price` |
| **Koszt 1 dzień / 1 tydzień / 1 miesiąc** | 1,75 / 9,30 / 29,83 USD |
| **Minimalny zakup** | **1,75 USD** (etap 1) |
| **Do decyzji GO/NO-GO** | **~32 USD** (etapy 1 + 2) |
| **Plan testu bez P&L** | etap 1: kompletność `side`; etap 2: VIF wobec momentum |
| **Ryzyko wykonania** | horyzont dziesiątek sekund; próg kosztowy 0,55 bp (1,10 bp po stresie) |
| **Plan forwardu** | ≥ 12 miesięcy, jednostka niezależności = **sesja**, ~250 rocznie |

**Nie piszę H017 i nie kupuję danych.** Obie rzeczy wymagają osobnej decyzji.

Gdyby etap 1 albo etap 2 wypadł negatywnie, D5 zostaje zamknięty — i zgodnie
z ustaleniem **nie wracam wtedy automatycznie do D2–D4 ani nie wymyślam
wariantów D1**, tylko zatrzymuję się i przygotowuję nową listę kierunków spoza
obecnej piątki.
