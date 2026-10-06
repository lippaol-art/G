# W010 — pre-flight partii 3 (H001, H002)

*Wygenerowane przez `research/W010_partia3_preflight.py`, 2026-08-02. 1771 sesji MNQ z pelnym tlem.*

**Status licznika prob: 0 zuzytych.**

H003 nie jest tu badana — wymaga kalendarza makro, ktorego jeszcze nie ma.

Skrypt byl **poprawiony przed pierwszym uruchomieniem** po przegladzie kodu:
szesc usterek, w tym blad czasowy dajacy cene wyjscia sprzed sygnalu i bledna
sigma VWAP. Lista w docstringu modulu. Zadna z nich nie rzucalaby bledu.

---

# H001 — kompresja nocna: przyczyna, nie fakt

## 1. Czy dwie kompresje daja rozny CHARAKTER sesji

Test, na ktorym karta stoi lub upada. H010 zginelo na tym, ze zakres nocny
przewiduje **amplitude** (t = +10.2), ale nie **charakter** (t ~ 0).

| Grupa | N | Efficiency ratio | Zakres RTH (pkt) | **Zakres nocny (pkt)** |
|---|---|---|---|---|
| **kompresja z rownowagi** (wolumen wysoki) | 95 | 0.5178 | 209.2 | 95.6 |
| **kompresja z braku** (wolumen niski) | 513 | 0.4912 | 198.1 | 88.1 |
| pozostale sesje | 1163 | 0.4879 | 277.3 | 201.0 |

**t roznicy efficiency ratio (rownowaga − brak): +0.91**

Kolumna zakresu nocnego jest kontrola konfundowania: t roznicy zakresu miedzy
grupami wynosi **+1.35**. Jesli grupy roznia sie zakresem, roznica
charakteru moze pochodzic z zakresu, a nie z wolumenu — i wtedy karta nie ma
swojej przeslanki, tylko powtarza H010.

## 2. Regresja ciagla — wolumen PO KONTROLI zakresu

Podzial kubelkowy nie wystarcza: wewnatrz tercyla kompresji nadal sa roznice
zakresu. Regresja liczona **wylacznie wewnatrz kompresji**:

`ER = α + β₁·percentyl_zakresu + β₂·percentyl_wolumenu + ε`

To nie jest model handlowy — to sprawdzenie, czy wolumen wnosi cokolwiek
po kontrolowaniu dokladnego zakresu.

| Wspolczynnik | Wartosc | t |
|---|---|---|
| α (wyraz wolny) | +0.5014 | **+24.52** |
| β₁ percentyl zakresu | -0.0300 | **-0.27** |
| **β₂ percentyl wolumenu** | -0.0050 | **-0.10** |

## 3. Kontynuacja po wybiciu z zakresu nocnego

**Kazda cena wyjscia pochodzi z bara pozniejszego niz bar wybicia** (asercja
w kodzie). Wynik do 10:30 raportowany **wylacznie dla wybic przed 10:30** —
inaczej mierzylby ruch sprzed sygnalu.

Wybic przed 10:30: **1435**, po 10:30: **274**.

### Wybicia przed 10:30, wynik do konca `rth_open`

| Grupa | N | Sredni wynik (pkt) | t |
|---|---|---|---|
| **kompresja z rownowagi** | 82 | +12.2 | +1.20 |
| **kompresja z braku** | 460 | +4.1 | +1.24 |
| pozostale sesje | 893 | -7.9 | -2.47 |

### Wszystkie wybicia, wynik do konca sesji

| Grupa | N | Sredni wynik (pkt) | t |
|---|---|---|---|
| **kompresja z rownowagi** | 93 | -8.4 | -0.57 |
| **kompresja z braku** | 505 | +7.5 | +1.28 |
| pozostale sesje | 1111 | -0.0 | -0.00 |

## 4. Stabilnosc roczna (kompresja z rownowagi, wybicia przed 10:30)

| Rok | N | Sredni wynik (pkt) | t |
|---|---|---|---|
| 2019 | 18 | +2.5 | +0.34 |
| 2020 | 13 | -0.1 | -0.01 |
| 2021 | 8 | +25.9 | +1.50 |
| 2022 | 11 | +41.4 | +1.90 |
| 2023 | 10 | -8.2 | -0.47 |
| 2024 | 7 | +28.1 | +0.69 |
| 2025 | 6 | +18.0 | +0.89 |
| 2026 | 9 | +7.9 | +0.10 |

---

# H002 — powrot do VWAP: gdzie odchylenie powstalo

Sesji z istotnym odchyleniem o 11:30 (\|d\| ≥ 1.0): **965** z 1801 (*f* = 0.54, karta deklarowala 0.33).

## 1. Trzy grupy, nie dwie

Odchylenie o 10:30 o **przeciwnym znaku** to nie jest odchylenie swieze —
to odwrocenie wczesniejszego. Poprzednia wersja wrzucala je do grupy swiezych
z udzialem 0. Podzial: \|d(10:30)\| < 0.5 to naprawde swieze,
reszta wedlug zgodnosci znaku.

| Grupa | N | \|d(11:30)\| srednia | mediana | Odsetek dotkniec VWAP |
|---|---|---|---|---|
| **swieze** (\|d₁₀:₃₀\| < 0.5) | 202 | 1.67 | 1.60 | 60.4% |
| **ten sam znak** (udzial ma sens) | 596 | 1.57 | 1.49 | 51.5% |
| odwrocenie znaku | 167 | 1.62 | 1.52 | 67.1% |

**Kolumny \|d(11:30)\| sa tu najwazniejsze.** Prawdopodobienstwo dotkniecia
VWAP zalezy mechanicznie od odleglosci od niego. Jesli grupy roznia sie
odlegloscia, roznica odsetka powrotow nie mowi nic o pochodzeniu odchylenia.

## 2. Powroty w porownywalnych przedzialach \|d(11:30)\|

| Przedzial \|d\| | swieze: N / powroty | ten sam znak: N / powroty |
|---|---|---|
| 1.0–1.5 | 85 / 64.7% | 305 / 56.4% |
| 1.5–2.0 | 66 / 53.0% | 198 / 48.0% |
| ≥ 2.0 | 51 / 62.7% | 93 / 43.0% |

## 3. Model prawdopodobienstwa powrotu z kontrola odleglosci

`P(dotkniecie) = α + β₁·\|d(11:30)\| + β₂·udzial_odziedziczony`, wewnatrz grupy o zgodnym znaku.

Model liniowy, bez dobierania progow i **bez interpretowania go jako
strategii** — sluzy wylacznie temu, zeby zobaczyc znak i istotnosc β₂
po kontrolowaniu tego, co dziala mechanicznie.

| Wspolczynnik | Wartosc | t |
|---|---|---|
| α | +0.8234 | **+6.26** |
| β₁ \|d(11:30)\| | -0.1557 | **-2.57** |
| **β₂ udzial odziedziczony** | -0.0637 | **-1.23** |

## 4. Powrot to nie tylko dotkniecie — zwrot, MFE i MAE

Brak dotkniecia VWAP nie znaczy kontynuacja; rynek moze stac w miejscu.
Ponizej zwrot 11:30→15:00 **w kierunku powrotu** (dodatni = zblizenie do
VWAP) oraz skrajne zblizenie i oddalenie w tym oknie.

| Grupa | N | Zwrot | t | MFE (do VWAP) | MAE (od VWAP) |
|---|---|---|---|---|---|
| **swieze** (\|d₁₀:₃₀\| < 0.5) | 202 | +0.0338% | +0.69 | +0.506% | -0.506% |
| **ten sam znak** (udzial ma sens) | 596 | -0.0041% | -0.16 | +0.470% | -0.438% |
| odwrocenie znaku | 167 | -0.0529% | -0.98 | +0.490% | -0.564% |

## 4a. Kto sie do kogo zbliza — kontrola mechaniki VWAP

**Dotkniecie VWAP nie dowodzi, ze cena wrocila.** VWAP jest srednia wazona
narastajaco, wiec nowy wolumen drukowany przy nowym poziomie **przyciaga VWAP
do ceny**. Odchylenie swieze ma z definicji mniej wolumenu przy nowym poziomie,
wiec VWAP ma wobec niego wiecej drogi do nadrobienia — i wyzszy odsetek
dotkniec moze byc czysta mechanika, nie powrotem ceny.

| Grupa | N | Luka o 11:30 (pkt) | Ruch VWAP (pkt) | Ruch ceny (pkt) | Udzial VWAP |
|---|---|---|---|---|---|
| **swieze** (\|d₁₀:₃₀\| < 0.5) | 202 | 61.7 | 33.8 | 77.5 | **0.49** |
| **ten sam znak** (udzial ma sens) | 596 | 73.3 | 35.7 | 66.4 | **0.45** |
| odwrocenie znaku | 167 | 58.6 | 35.4 | 73.5 | **0.48** |

**Hipoteza sprawdzona i ODRZUCONA.** Udzial VWAP w domknieciu luki jest
praktycznie taki sam we wszystkich grupach (0.49 wobec 0.45), wiec roznica odsetka dotkniec
**nie jest artefaktem mechaniki VWAP**. Podejrzenie bylo uzasadnione i okazalo
sie nietrafione — odnotowuje to, bo negatywna kontrola tez jest wynikiem.

### Wewnatrz grupy o zgodnym znaku, wedlug udzialu odziedziczonego

| Udzial | N | \|d\| srednia | Powroty | Zwrot | t |
|---|---|---|---|---|---|
| < 0.33 | 30 | 2.19 | 60.0% | +0.1392% | +1.15 |
| 0.33–0.67 | 124 | 1.77 | 54.8% | -0.0421% | -0.73 |
| > 0.67 | 442 | 1.48 | 50.0% | -0.0031% | -0.10 |

## 5. Ablacja 2 karty — czy prosty wolumen daje to samo

**Wazniejszy test niz poprzednie.** Karta przyznaje w sekcji 4, ze grozi jej
sprowadzenie do detalicznej reguly "ruch bez wolumenu jest falszywy".

| Podzial | N | Odsetek powrotow | t roznicy |
|---|---|---|---|
| wg **pochodzenia** (swieze vs zgodny znak) | 202 / 596 | 60.4% vs 51.5% | **+2.21** |
| wg **wolumenu 10:30-11:30** (niski vs wysoki) | 428 / 522 | 56.3% vs 55.4% | +0.29 |

## 6. Stabilnosc roczna (grupa swieza)

| Rok | N | Powroty | Zwrot |
|---|---|---|---|
| 2019 | 17 | 52.9% | -0.0517% |
| 2020 | 29 | 62.1% | +0.1595% |
| 2021 | 23 | 60.9% | +0.0272% |
| 2022 | 24 | 62.5% | +0.0198% |
| 2023 | 37 | 59.5% | -0.0254% |
| 2024 | 34 | 76.5% | +0.1235% |
| 2025 | 26 | 46.2% | -0.0389% |
| 2026 | 12 | 50.0% | -0.0225% |

---

# Werdykty

## H001 — **ODRZUCONA**

Karta stala na jednym zdaniu: **wolumen przy zadanym zakresie niesie
informacje o charakterze sesji, ktorej sam zakres nie niesie.** Zdanie jest
falszywe na naszych danych.

| Test | Wynik |
|---|---|
| Roznica efficiency ratio miedzy dwoma kompresjami | t = **+0.91** |
| β₂ percentyl wolumenu, po kontroli zakresu | t = **-0.10** |
| β₁ percentyl zakresu, wewnatrz kompresji | t = -0.27 |

Regresja ciagla jest tu rozstrzygajaca: **po kontrolowaniu dokladnego zakresu
wolumen nie wnosi nic** — wspolczynnik jest zerowy co do znaku i wielkosci.
Podzial kubelkowy dawal t = +0.91, czyli tez nic, ale mozna bylo go tlumaczyc
mala liczebnoscia grupy wysokiego wolumenu (95 sesji). Regresja korzysta
z wszystkich obserwacji i odpowiedz jest ta sama.

Ciekawostka, ktora **nie ratuje karty**: wybicia po kompresji z rownowagi daja
+12 pkt do 10:30
wobec −8 pkt na pozostalych sesjach. Ale przeslanka karty juz upadla, N wynosi
82, wynik roczny waha sie od −8 do +41 pkt przy 6–18 obserwacjach na rok,
a roznica wobec kompresji z braku jest w granicach szumu. **Warunek zbudowany
na falszywej przeslance nie staje sie prawdziwy dlatego, ze podzbior wyglada
dobrze** — to jest dokladnie ten blad, przed ktorym chroni W004.

Karta schodzi do **B02** zgodnie z regula samoczyszczaca z sekcji 8.4 PLAN-u.

## H002 — **ODRZUCONA WLASNYM KRYTERIUM**, ale nie bez oporu

**Karta ma cos prawdziwego i trzeba to powiedziec, zanim padnie werdykt.**
Pochodzenie odchylenia rozdziela odsetek powrotow do VWAP i przetrwalo
cztery niezalezne kontrole:

| Kontrola | Wynik |
|---|---|
| Roznica odsetka powrotow (swieze vs odziedziczone) | t = **+2.21** |
| Ablacja 2: to samo po wolumenie 10:30-11:30 | t = +0.29 — **nic** |
| Kontrola \|d(11:30)\| w trzech pasmach | swieze wyzej we **wszystkich trzech** |
| Monotonicznosc wzgledem udzialu odziedziczonego | 60.0% → 54.8% → 50.0% |
| Mechanika VWAP (kto sie do kogo zbliza) | udzial VWAP ten sam w grupach |

To jest wiecej, niz przeszla ktorakolwiek z dziewieciu wczesniej odrzuconych
kart. Ablacja 2 byla tym testem, ktorego karta sie bala — i przeszla go
czysto: prosty warunek wolumenowy nie daje nic (t = +0.29), a pochodzenie daje.

**A jednak karta upada, i to na kryterium, ktore sama zadeklarowala z gory.**
Falsyfikator 2 z sekcji 9 brzmial: *dziala tylko jeden koniec skali*.

| Grupa | Zwrot 11:30→15:00 w kierunku VWAP | t |
|---|---|---|
| swieze (mial wracac) | +0.0338% | +0.69 |
| odziedziczone (mialy kontynuowac) | -0.0041% | -0.16 |

Koniec "odziedziczony" **nie kontynuuje** — daje zero. Mechanizm z sekcji 2
karty przewidywal przewage na obu koncach, w przeciwne strony. Dziala co
najwyzej jeden, i to slabo.

Drugi cios jest ekonomiczny i wazniejszy. **Odsetek dotkniec to nie jest P&L.**
Zwrot grupy swiezej wynosi +0.0338% przy t = +0.69,
czyli nie da sie go odroznic od zera, a MFE i MAE sa **symetryczne**
(+0.506% wobec -0.506%).
Symetryczne skrajnosci to sygnatura bladzenia losowego: cena bywa blizej VWAP
i bywa dalej, dokladnie tak samo czesto i tak samo daleko.

**To jest W005 po raz drugi.** H010 dalo najmocniejszy pojedynczy wynik projektu
(t > 10) i zginelo, bo mierzylo amplitude tam, gdzie karta potrzebowala
kierunku. H002 daje separacje odsetka dotkniec, ktora przezyla cztery kontrole,
i ginie, bo **dotkniecie nie jest zwrotem**.

Deklarowane *f* tez sie nie zgadza: karta zakladala 0.33, wyszlo 0.54 dla wszystkich istotnych odchylen, ale grupa
swieza to tylko 0.11 — czyli prog W002 rosnie
z 1.7× do **3.0×**.

## Co z tego zostaje

Obie karty odrzucone, **zero zuzytych prob z budzetu 14**. Partia 3 traci dwie
z trzech kart; H003 pozostaje zablokowana brakiem kalendarza makro.

Ustalenie warte zapamietania poza ta partia: **pochodzenie odchylenia jest
realna zmienna** — rozdziela zachowanie ceny lepiej niz wolumen i przezywa
kontrole na wielkosc odchylenia. Nie daje przewagi handlowej w tej postaci,
ale jest kandydatem na **wejscie do wielkosci pozycji** albo warstwe reżimowa,
tak jak H010 zostalo po W004. Nie otwieram na to karty teraz.

---

Odtworzenie: `python3 research/W010_partia3_preflight.py`
