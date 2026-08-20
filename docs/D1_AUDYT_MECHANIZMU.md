# Audyt mechanizmu D1 — rebalansowanie funduszy lewarowanych

**Werdykt: `D1 NIEWYKONALNY` w proponowanej postaci.**
Blocker: falsyfikator nr 8 — szacowany przepływ jest praktycznie współliniowy
z benchmarkiem B04. Szczegóły w sekcji 8.

Audyt **nie zużywa próby**: nie liczy ani jednego zwrotu okna wynikowego, nie
mierzy P&L, nie zawiera reguły wejścia. Mierzy wyłącznie własności proponowanego
regresora. Odtworzenie: `scripts/audit_d1.py --katalog <dir>`.

---

## 0. Co ten audyt miał rozstrzygnąć

Nie „czy D1 zarabia" — tego nie mierzyłem i nie mogę o tym nic powiedzieć.
Pytanie brzmiało: **czy da się zbudować point-in-time zmienną mechanizmu bez
lookaheadu i czy tę zmienną da się statystycznie odróżnić od B04.**

Odpowiedź na pierwszą część jest **twierdząca i to dobra wiadomość**. Odpowiedź
na drugą jest przecząca i to ona przesądza.

---

## 1. Wszechświat funduszy

### Uwzględnione — stała dzienna dźwignia na **sam** indeks Nasdaq-100

| Ticker | Emitent | L | Start | Status |
|---|---|---|---|---|
| TQQQ | ProShares | +3 | 2010-02-09 | aktywny |
| QLD | ProShares | +2 | 2006-06-19 | aktywny |
| SQQQ | ProShares | −3 | 2010-02-09 | aktywny |
| QID | ProShares | −2 | 2006-07-11 | aktywny |
| PSQ | ProShares | −1 | 2006-06-19 | aktywny |

Daty startu wzięte z **pierwszego wiersza pliku historycznego każdego funduszu**,
nie z materiałów marketingowych.

### Wykluczone i dlaczego — pułapki, które łatwo przeoczyć

| Fundusz | Dlaczego NIE wchodzi |
|---|---|
| **EQQQ** (ProShares, VII 2026) | 2× **Nasdaq-100 Equal Weighted** — inny indeks bazowy. Ta sama rodzina nazw, inny benchmark. |
| **QQQU / QQQD (Direxion)** | „Magnificent 7 Bull 2X / Bear 1X" — **nie NDX**, tylko koszyk siedmiu spółek. |
| **QQQU / QQQD (LongPoint)** | 3× i −3× NDX, ale to **kolizja tickerów z produktami Direxion** o zupełnie innym benchmarku. Bez jednoznacznego rozstrzygnięcia emitenta po dacie — ryzyko sklejenia dwóch różnych szeregów pod jednym tickerem. |
| ETN-y i produkty zagraniczne | inny mechanizm rozliczenia, poza zakresem |

**To jest realna pułapka, nie formalność.** Ticker `QQQU` oznacza dziś dwa różne
produkty u dwóch emitentów, o różnych indeksach bazowych. Automatyczne
zaciągnięcie „wszystkich lewarowanych QQQ" skleiłoby je w jeden szereg.

### Survivorship bias — stan częściowy ⚠

ProShares zlikwidowało 8 funduszy w marcu 2020 (ostatnie kreacje 2020-03-27).
**Nie zweryfikowałem, czy któryś z nich miał ekspozycję na NDX** — strony
emitenta zwracają 403 dla automatycznego pobrania, a rejestr zamkniętych
funduszy nie był dostępny w formie maszynowej.

Skala ryzyka jest jednak ograniczona: TQQQ (32,6 mld USD) i QLD (12,8 mld)
stanowią przytłaczającą większość aktywów kompleksu. Fundusz zamknięty w 2020
byłby mały. **To zastrzeżenie odnotowuję jako otwarte**, nie zamiatam go.

---

## 2. Dane point-in-time — DOSTĘPNE I DARMOWE ✅

To był największy przewidywany blocker i **on nie występuje**.

**Źródło:** `https://accounts.profunds.com/etfdata/ByFund/{TICKER}-historical_nav.csv`
HTTP 200, bez uwierzytelnienia, bez opłat.

**Schemat:** `Date, ProShares Name, Ticker, NAV, Prior NAV, NAV Change (%),
NAV Change ($), Shares Outstanding (000), Assets Under Management`

**Pokrycie:** pełna historia od inception każdego funduszu do bieżącej sesji.
TQQQ 4 144 wierszy (2010-02-09 → 2026-07-31), QLD 5 061 (od 2006-06-19).

**Sumy kontrolne pobranych plików** (SHA-256, 16 znaków): TQQQ `ca35bcafefe6494a`,
QLD `c857d5e1566a224d`, SQQQ `05f6d6e745b5ea0d`, QID `27150f416435373c`,
PSQ `d3aa80d41d4af7c9`.

Plików **nie commituję** — są zewnętrzne i odtwarzalne z podanego adresu.

### Kiedy wiersz staje się publiczny — ustalone z danych, nie z założenia

Sprawdziłem tożsamość na ostatnim wierszu każdego funduszu:

```
AUM_t  =  NAV_t × jednostki_t     różnica: 0.00 (TQQQ, QLD)
```

Zgodność co do centa dowodzi, że **wiersz datowany na dzień t jest wielkością
policzoną po zamknięciu dnia t** — używa NAV z tego zamknięcia. Nie jest więc
dostępny dla sygnału wykonywanego **przed** tym zamknięciem.

**Reguła point-in-time, która z tego wynika i którą przyjmuję:**

> Do oszacowania przepływu w dniu *t* wolno użyć wyłącznie wiersza z dnia *t−1*
> oraz zwrotu obserwowanego do momentu sygnału. Wiersz z dnia *t* jest
> niedostępny.

Spełnia to wymagany porządek: `timestamp(AUM) < timestamp(r) < timestamp(sygnał)
< timestamp(wejście) < timestamp(wyjście)`.

---

## 3. Założenia wzoru i błąd estymatora

Wyprowadzenie `ΔE = L(L−1)·A·r` zakłada odtwarzanie stałej dźwigni dziennej,
poprawne `A` przed ruchem i brak dominacji przepływów inwestorów.

Naiwny estymator PIT używa `A` z `t−1`. Ale część różnicy między `A_{t−1}`
a faktycznym `A_t` jest **mechaniczna i znana**: NAV funduszu zmienia się
o `L·r`, a `r` obserwujemy. Skorygowany estymator to `A_{t−1}·(1 + L·r)`.

Pomiar na 1 800 wspólnych sesjach (2019-05 → 2026-07):

| Estymator | mediana \|błędu\| | p90 | corr(błąd, r) |
|---|---|---|---|
| naiwny (`A` z t−1) | 1,23% | 3,97% | **+0,751** |
| skorygowany o efekt NAV | **0,66%** | 2,18% | **+0,147** |

**Wniosek pozytywny:** większość obciążenia naiwnego estymatora to efekt NAV,
który da się usunąć bez lookaheadu. Reszta — 0,66% mediany przy korelacji
+0,15 — to czysty efekt kreacji i umorzeń, którego PIT nie widzi. To **błąd
pomiaru**, nie model, i tak został nazwany.

---

## 4. Kreacje i umorzenia — Ivanov & Lenkey potwierdzeni na naszej próbie

Literatura (Ivanov & Lenkey, *Journal of Financial Markets* 2018, próba
2006–2014) twierdzi, że przepływy kapitału **redukują** zapotrzebowanie na
rebalans, a po ich uwzględnieniu wpływ na zwroty końcówki sesji jest
**ekonomicznie nieistotny**.

Zmierzone na naszej, późniejszej próbie (2019–2026):

| Fundusz | L | mediana \|Δjednostek\|/dzień | p90 | corr(Δjednostek, r) |
|---|---|---|---|---|
| TQQQ | +3 | 0,74% | 3,54% | **−0,343** |
| QLD | +2 | 0,54% | 2,86% | +0,134 |
| SQQQ | −3 | 1,75% | 6,08% | **+0,356** |
| QID | −2 | 1,60% | 7,47% | −0,066 |
| PSQ | −1 | 0,99% | 5,07% | −0,090 |

**Oba największe fundusze pokazują offset, każdy w swojej logice:**

- **TQQQ (−0,343):** inwestorzy umarzają po wzrostach. Fundusz musi *kupować*
  (bo `r > 0`), a umorzenia zmuszają go do *sprzedaży*. Kierunki przeciwne.
- **SQQQ (+0,356):** inwestorzy tworzą jednostki po wzrostach (kupowanie
  dołków). Fundusz musi *kupować* z tytułu rebalansu, a nowe środki wymagają
  ustanowienia *nowej krótkiej pozycji*. Kierunki przeciwne.

To nie jest szum — to systematyczna kompensacja skorelowana z `r`, dokładnie
tak, jak opisuje literatura. Nasza próba jest o 12 lat późniejsza i daje ten
sam obraz.

---

## 5. Kto faktycznie wykonuje przepływ — ⚠ NIEROZSTRZYGNIĘTE

Nie założyłem, że emitent kupuje kontrakt NQ na zamknięciu, i **dobrze, bo to
nieprawda w prostej postaci**.

Ustalone: TQQQ utrzymuje ekspozycję przez **swapy nałożone na koszyk akcji**
(ok. 80% aktywów w akcjach), a rebalans opisywany jest jako **wieczorne
przestawienie ekspozycji swapowej**.

Konsekwencja: transakcja domykająca dźwignię jest w znacznej części **resetem
swapu z kontrahentem**, a nie zleceniem funduszu w kontrakcie terminowym na
zamknięciu. Ścieżka do ceny NDX prowadzi wtedy przez **hedge kontrahenta**,
który może:

- trafić w NQ, QQQ albo koszyk akcji,
- zostać rozłożony w czasie,
- zostać częściowo zneutralizowany wewnętrznie przeciwstawnymi ekspozycjami.

**Czego nie udało się zweryfikować:** dokładnego momentu ustalania ekspozycji,
udziału swapów wobec futures i tego, czy kontrahent hedguje w oknie zamknięcia.
Strony emitenta i prospekt zwracają HTTP 403 dla automatycznego pobrania.

To pozostaje **luką audytu**, nie rozwiązanym punktem. Nie blokuje jednak
werdyktu, bo blocker z sekcji 8 wystąpiłby niezależnie od odpowiedzi.

---

## 6. Okno czasowe i normalizacja płynnością

**Okno nie zostało dobrane po obejrzeniu zwrotów** — nie oglądałem żadnych
zwrotów okna. Literatura (Cheng & Madhavan 2009) wskazuje końcówkę sesji
i podaje skalę: przy ruchu indeksu 1% rebalans lewarowanych może odpowiadać za
**~16,8% wolumenu na zamknięciu**, przy 5% — za ~50%.

Normalizacja płynnością liczona wyłącznie point-in-time: **ADV z 20 poprzednich
sesji**, z jawnym wykluczeniem dnia bieżącego (`rolling_mean(20).shift(1)`).
Przyszły wolumen badanego okna nie jest używany nigdzie.

---

## 7. Model przyrostowy — zapisany przed pomiarem

Zgodnie z wymogiem, obowiązkowa postać testu rozdzielającego D1 od B04:

```
wynik_okna ~ r + |r| + r² + sign(r) + ΔE_znormalizowane
```

Kontrola liniowa sama nie wystarcza, bo `ΔE = K·r` jest iloczynem — model musi
rozdzielić znak `r`, wielkość `|r|`, możliwą nieliniowość momentum dziennego
oraz wkład aktywów i dźwigni kompleksu.

**Ten model nie został uruchomiony** — audyt zatrzymał się wcześniej, na
sprawdzeniu, czy da się go w ogóle zidentyfikować.

---

## 8. FALSYFIKATOR nr 8 — i tu D1 upada

Pytanie: czy `ΔE` niesie informację niezależną od zestawu kontrolnego B04.

Miarą jest `R²` pomocnicze z regresji `ΔE` na `[r, |r|, r², sign(r)]` oraz
wynikająca z niego inflacja wariancji `VIF = 1/(1−R²)`.

### Wynik dla wariantu surowego

| Rok | R² | VIF | inflacja SE |
|---|---|---|---|
| 2019 | 0,9989 | 927 | ×30,4 |
| 2020 | 0,9509 | 20,4 | ×4,5 |
| 2021 | 0,9588 | 24,3 | ×4,9 |
| 2022 | 0,9925 | 134 | ×11,6 |
| 2023 | 0,9915 | 117 | ×10,8 |
| 2024 | 0,9955 | 224 | ×15,0 |
| 2025 | 0,9823 | 56,7 | ×7,5 |
| 2026 | 0,9867 | 75,3 | ×8,7 |

Średni VIF wewnątrz roku: **197** — wariancja estymatora większa ok. 197 razy,
błąd standardowy ok. 14 razy.

### Wynik po normalizacji płynnością — najlepszy dostępny wariant

| Rok | R² | VIF | inflacja SE |
|---|---|---|---|
| 2019 | 0,9447 | 18,1 | ×4,3 |
| 2020 | 0,8642 | 7,4 | ×2,7 |
| 2021 | 0,9661 | 29,5 | ×5,4 |
| 2022 | 0,9609 | 25,6 | ×5,1 |
| 2023 | 0,9715 | 35,1 | ×5,9 |
| 2024 | 0,9556 | 22,5 | ×4,7 |
| 2025 | 0,9456 | 18,4 | ×4,3 |
| 2026 | 0,9639 | 27,7 | ×5,3 |

Średni VIF wewnątrz roku: **23,0**.

**Jak to czytać.** VIF = 23 oznacza wariancję estymatora współczynnika większą
ok. 23 razy i błąd standardowy większy ok. **4,8 razy**. W uproszczonej analogii
informacyjnej odpowiadałoby to spadkowi N = 400 do około **17**, ale **nie jest
to dosłowna liczebność próby** — to przybliżenie przy uproszczonych założeniach
OLS, podane jako intuicja skali, nie jako liczba niezależnych obserwacji.

### Dlaczego pełna próba nie ratuje sprawy

Na całej próbie `R²` spada do 0,784 (VIF 4,6), więc pozornie identyfikacja jest
znośna. **Ale ta identyfikacja pochodzi z niewłaściwego źródła.**

Współczynnik `K = Σ L(L−1)·A` urósł monotonicznie:

| Rok | średnie K | CV wewnątrz roku |
|---|---|---|
| 2019 | 42,7 mld USD | 0,035 |
| 2021 | 114,0 | 0,178 |
| 2023 | 163,5 | 0,090 |
| 2026 | 242,7 | 0,119 |

**5,7-krotny wzrost w siedem lat.** Dodanie jednego członu `r × trend` do modelu
podnosi `R²(ΔE ~ r)` z 0,826 do **0,981**. Innymi słowy: informacja w `ΔE`
wykraczająca poza `r` jest w ~98% **wolnym trendem wzrostu kompleksu pomnożonym
przez `r`** — a nie dzienną zmiennością intensywności przepływu.

To jest problem identyfikowalności, nie mocy. Jedyna zmienność, która pozwala
odróżnić `ΔE` od `r`, jest **nieodróżnialna od hipotezy „efekt B04 zmieniał siłę
w latach 2019–2026"**. Żaden wynik takiego testu nie byłby rozstrzygający.

**Falsyfikator nr 7** (przepływ zmienia się wystarczająco, by odróżnić go od `r`)
— **nie przechodzi**.
**Falsyfikator nr 8** (przepływ nie jest praktycznie współliniowy z B04) —
**nie przechodzi**.

---

## 9. Zgodność literatury z tym ustaleniem

Wynik audytu nie jest odosobniony:

| Źródło | Ustalenie |
|---|---|
| Cheng & Madhavan (2009) | rebalans realny i przewidywalny; przy ruchu 1% ≈ 16,8% wolumenu MOC |
| agregaty rynkowe | szacowany rebalans tłumaczy ~⅓ **zmienności** końcówki sesji, >50% w dni ±3% |
| **Ivanov & Lenkey (2018, JFM)** | po uwzględnieniu przepływów kapitału wpływ na zwroty i zmienność końcówki jest **ekonomicznie nieistotny** |
| badania okresu 2010–2017 | większe i bardziej przewidywalne przepływy mają **mniejsze** współczynniki wpływu na cenę; **brak nadwyżkowych zysków** z wyprzedzania rebalansu |
| badania okresu 2006–2011 | wyprzedzanie działało (0,60% na transakcję), ale zyski **skoncentrowane w końcu 2008 roku** |

Dwa ostatnie wiersze trafiają dokładnie w cmentarz Gen1:

- „tłumaczy ⅓ **zmienności**" to **amplituda**, a nie kierunek — cmentarz 3.3,
- „zyski skoncentrowane w końcu 2008" to jeden reżim dominujący wynik —
  kryterium, na którym zginęło H005 (żaden rok nie może dawać ponad 40%).

---

## 10. Werdykt

# `D1 NIEWYKONALNY`

**Dokładny blocker:** proponowana zmienna mechanizmu `ΔE = L(L−1)·A·r` jest
w praktyce przeskalowanym `r`. Wewnątrz każdego roku badanej historii
współliniowość z pełnym zestawem kontrolnym B04 wynosi **R² = 0,86–0,97 nawet
po najlepszej dostępnej normalizacji płynnością**, co daje średni VIF **23** —
błąd standardowy współczynnika przyrostowego większy ok. 4,8 razy (w uproszczonej
analogii informacyjnej: jakby z N = 400 zostało ~17, choć nie jest to dosłowna
liczebność próby). Jedyna zmienność identyfikująca
pochodzi z **wolnego wzrostu aktywów kompleksu**, nieodróżnialnego od zmiany
siły samego efektu B04 w czasie.

Zgodnie z regułą przyjętą przed audytem: *„jeżeli ΔE jest w praktyce jedynie
przeskalowanym r, D1 nie dostaje karty"*.

### Stan pozostałych falsyfikatorów

| # | Falsyfikator | Wynik |
|---|---|---|
| 1 | point-in-time historia aktywów | ✅ darmowa, pełna od inception |
| 2 | universe bez survivorship bias | ⚠ częściowo — 8 zamknięć ProShares 2020 niezweryfikowane |
| 3 | dźwignia i benchmark znane historycznie | ✅ |
| 4 | moment publikacji nie powoduje lookaheadu | ✅ reguła t−1 ustalona z danych |
| 5 | wiarygodna ścieżka transmisji do NDX | ⚠ **nierozstrzygnięte** — trasa swapowa |
| 6 | okno zamrażalne przed wynikiem | ✅ |
| 7 | przepływ odróżnialny od samego `r` | ❌ **NIE** |
| 8 | brak praktycznej współliniowości z B04 | ❌ **NIE** |
| 9 | koszty do pokrycia | niebadane — bezprzedmiotowe po 7 i 8 |

### Czego ten werdykt NIE mówi

**Nie twierdzę, że przepływ rebalansowy nie istnieje ani że nie wpływa na cenę.**
Literatura pokazuje, że istnieje i wpływa — na **zmienność**. Nie zmierzyłem
żadnego zwrotu okna wynikowego i nie mam podstaw, by wypowiadać się o P&L.

Twierdzę wyłącznie: **przy tej konstrukcji zmiennej i tej historii nie da się
statystycznie oddzielić D1 od B04.** To jest orzeczenie o możliwości dowodu,
nie o istnieniu zjawiska.

### Czy istnieje wariant, który by przeżył

Nie widzę takiego w obrębie tego mechanizmu, i to jest uczciwa odpowiedź, a nie
brak pomysłu. Problem jest strukturalny: `ΔE` ma postać `(wolny czynnik) × r`,
a każda zmienna tej postaci będzie współliniowa z `r`. Wyjście wymagałoby
składnika przepływu, który zmienia się **szybko i niezależnie od `r`** —
czyli komponentu kreacji i umorzeń. A ten jest z definicji **niedostępny
point-in-time**: jest publikowany dopiero po zamknięciu, czyli po momencie,
w którym musiałby zostać użyty.

To domyka pętlę: jedyna informacja, która mogłaby uratować D1, jest tą samą
informacją, której reguła braku lookaheadu zabrania użyć.

---

## 11. Rekomendacja

**D1 nie dostaje karty.** Nie proponuję wariantu ratunkowego ani zawężenia —
byłoby to szukanie „prawie działającego" podzbioru, czego zakazuje protokół
Gen2 (synteza 5.4).

Kierunek rezerwowy **D5** wraca do rozważenia zgodnie z ustalonymi warunkami:
zawężenie do jednej zamrożonej zależności, wskazanie dokładnych pól danych,
wycena minimalnej próbki i osobna zgoda na zakup. **Nie kupuję żadnych danych.**

Odnotowuję też ustalenie ogólniejsze, przydatne przy ocenie kolejnych kierunków:
**mechanizm, którego zmienna ma postać „wolno zmienny czynnik × zwrot dnia",
jest z góry skazany na współliniowość z momentum dziennym.** To kryterium da się
sprawdzić na kartce, przed jakimkolwiek pobieraniem danych — i warto je dodać do
listy pytań o kolejny kierunek.
