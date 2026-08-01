# W001 — czy dryf nocny na NDX jeszcze istnieje?

*Wygenerowane przez `research/W001_overnight_drift.py`, 2026-08-01.*

**Status licznika prob: 0 zuzytych.** To dekompozycja rozkladow, nie backtest —
nie ma tu zadnej reguly wejscia ani zadnego dobieranego parametru (rozdz. 6.5).

## Pytanie

Audyt oryginalnosci przytoczyl badanie NY Fed: dryf overnight na indeksach US
~3.7%/rok w latach 1998-2020 i **~0% w latach 2021-2025**. Karta H004 warunkuje
ten efekt, wiec jesli efekt wygasl, karta warunkuje nieistniejace zjawisko.
REGISTRY.md nakazuje rozstrzygnac to przed jakakolwiek praca nad H004.

---

## 1. Dekompozycja zwrotu dobowego, rok po roku

Zwrot logarytmiczny, seria skorygowana (`px_adj`), dni sesyjne z co najmniej
200 barami RTH. Suma obu skladowych odtwarza pelny zwrot
buy-and-hold — tozsamosc weryfikowana w kodzie.

### MNQ

| Rok | Dni | Noc [%] | Sesja [%] | Razem [%] | t(noc) | t(sesja) |
|---|---|---|---|---|---|---|
| 2019 | 168 | +6.59 | +0.77 | +7.37 | +1.16 | +0.12 |
| 2020 | 257 | +23.18 | +6.36 | +29.54 | +1.40 | +0.37 |
| 2021 | 258 | +11.79 | +7.54 | +19.33 | +1.43 | +0.63 |
| 2022 | 258 | -20.84 | -11.99 | -32.83 | -1.51 | -0.56 |
| 2023 | 257 | +5.13 | +26.42 | +31.55 | +0.62 | +2.09 |
| 2024 | 259 | +18.71 | -3.71 | +14.99 | +1.79 | -0.29 |
| 2025 | 257 | +10.38 | +3.32 | +13.70 | +0.74 | +0.18 |
| 2026 | 149 | +5.47 | +2.85 | +8.31 | +0.50 | +0.24 |
| **2019-2026** | **1863** | **+60.40** | **+31.57** | **+91.97** | **+1.85** | **+0.75** |

### NQ

| Rok | Dni | Noc [%] | Sesja [%] | Razem [%] | t(noc) | t(sesja) |
|---|---|---|---|---|---|---|
| 2019 | 184 | +6.56 | +2.23 | +8.80 | +1.10 | +0.33 |
| 2020 | 257 | +23.53 | +5.98 | +29.51 | +1.41 | +0.35 |
| 2021 | 258 | +11.90 | +7.48 | +19.38 | +1.44 | +0.63 |
| 2022 | 258 | -20.92 | -11.91 | -32.83 | -1.52 | -0.56 |
| 2023 | 257 | +5.10 | +26.46 | +31.56 | +0.61 | +2.10 |
| 2024 | 259 | +18.71 | -3.72 | +14.99 | +1.79 | -0.29 |
| 2025 | 257 | +10.34 | +3.32 | +13.66 | +0.73 | +0.18 |
| 2026 | 149 | +5.51 | +2.81 | +8.32 | +0.50 | +0.24 |
| **2019-2026** | **1879** | **+60.73** | **+32.66** | **+93.39** | **+1.85** | **+0.78** |

### ES

| Rok | Dni | Noc [%] | Sesja [%] | Razem [%] | t(noc) | t(sesja) |
|---|---|---|---|---|---|---|
| 2019 | 184 | +6.65 | +1.43 | +8.09 | +1.25 | +0.24 |
| 2020 | 257 | +16.14 | -3.11 | +13.03 | +0.87 | -0.19 |
| 2021 | 258 | +12.70 | +8.12 | +20.81 | +2.00 | +0.95 |
| 2022 | 258 | -14.32 | -4.20 | -18.52 | -1.27 | -0.25 |
| 2023 | 257 | +0.39 | +15.12 | +15.50 | +0.06 | +1.57 |
| 2024 | 259 | +14.17 | +0.42 | +14.59 | +1.83 | +0.05 |
| 2025 | 257 | +5.16 | +5.95 | +11.11 | +0.46 | +0.38 |
| 2026 | 149 | +2.79 | +3.64 | +6.43 | +0.39 | +0.47 |
| **2019-2026** | **1879** | **+43.68** | **+27.37** | **+71.05** | **+1.52** | **+0.82** |

## 2. Podzial na okresy wg tezy zewnetrznej (granica 2021)

Przedzialy ufnosci **blokowe** (blok sredni 10 dni), nie iid — zmiennosc dzienna
wystepuje w seriach, a bootstrap po pojedynczych dniach dalby przedzialy wezsze,
niz uprawniaja dane.

| Instrument | Okres | Dni | Dryf nocny [%/rok] | 95% CI [%/rok] | Sharpe | t |
|---|---|---|---|---|---|---|
| MNQ | 2019-2020 | 425 | +19.3 | [-4.1, +43.6] | +1.31 | +1.70 |
| MNQ | 2021-2026 | 1438 | +5.5 | [-3.2, +14.6] | +0.47 | +1.11 |
| NQ | 2019-2020 | 441 | +18.8 | [-4.4, +42.3] | +1.28 | +1.69 |
| NQ | 2021-2026 | 1438 | +5.5 | [-3.6, +14.7] | +0.47 | +1.11 |
| ES | 2019-2020 | 441 | +13.9 | [-11.5, +40.5] | +0.89 | +1.18 |
| ES | 2021-2026 | 1438 | +3.7 | [-3.5, +10.8] | +0.41 | +0.99 |

## 3. Czy to pytanie w ogole da sie rozstrzygnac?

**To jest najwazniejsza sekcja tego raportu.** Zanim zinterpretujemy liczby
z sekcji 2, trzeba sprawdzic, jaka moc ma test, ktory je wyprodukowal.

Odchylenie standardowe dziennego zwrotu nocnego MNQ: **0.755%**.
Przy takim szumie liczba dni potrzebna, by odroznic zadany dryf od zera
przy mocy 80% i alfa 5%:

| Hipotetyczny dryf | Srednia dzienna | Wymagane N | To jest |
|---|---|---|---|
| 2.0%/rok | 0.0079% | 72,531 dni | **288 lat** |
| 3.7%/rok | 0.0144% | 21,547 dni | **86 lat** |
| 5.0%/rok | 0.0194% | 11,948 dni | **47 lat** |
| 10.0%/rok | 0.0378% | 3,131 dni | **12 lat** |
| 20.0%/rok | 0.0723% | 856 dni | **3 lat** |

Teza NY Fed dotyczy dryfu **3.7%/rok**. Odroznienie go od zera wymaga
**86 lat danych.**
Nasza probka 2021-2026 liczy 1438 dni, czyli 5.7 roku.

### Co z tego wynika

Najmniejszy dryf wykrywalny na naszej probce 2021-2026 przy mocy 80%:
**+15%/rok**. Przedzial ufnosci dla dryfu nocnego MNQ
w tym okresie wynosi **[-4.4%, +16.4%] rocznie** — szerokosc 21 punktow procentowych.

**Zarowno 0%, jak i 3.7% lezy wewnatrz tego przedzialu.** Nasze dane nie
potwierdzaja tezy o wygasnieciu ani jej nie obalaja — po prostu jej nie
rozstrzygaja. I nie rozstrzygnie jej zadna ilosc danych, jaka ten projekt
kiedykolwiek zdobedzie: 5.7 roku historii MNQ nie zamieni
sie w 86.

> **Uwaga o samej tezie zrodlowej.** Ten sam rachunek stosuje sie do niej.
> Punktowa ocena "~0% w latach 2021-2025" oparta na piecioletnim oknie ma
> dokladnie taki sam przedzial ufnosci jak nasza. Zdanie "dryf nocny wygasl"
> nie jest wnioskiem, ktory pieciolatek danych moze udzwignac — niezaleznie
> od tego, kto go wypowiada. Nie zarzucam bledu autorom; zwracam uwage, ze
> **nie wolno nam oprzec decyzji projektowej na twierdzeniu tej klasy.**

## 4. Pytanie, ktore ma odpowiedz

"Czy dryf wygasl" jest pytaniem zle postawionym — nie da sie na nie odpowiedziec.
Pytanie operacyjne brzmi inaczej i **ma** odpowiedz:

> Czy bezwarunkowy dryf nocny daje Sharpe'a, ktory przechodzi bramke projektu
> (SR >= 0.8 OOS, rozdz. 1.3)?

| Okres | Dni | Sharpe (bezwarunkowo, przed kosztami) | Prog 0.8 |
|---|---|---|---|
| 2019-2026 | 1863 | **0.68** | **nie przechodzi** |
| 2021-2026 | 1438 | **0.47** | **nie przechodzi** |

Odpowiedz jest jednoznaczna i nie zalezy od tego, czy efekt "wygasl":
**bezwarunkowy dryf nocny nie przechodzi bramki w zadnym okresie** — i to
jeszcze przed odjeciem kosztow. Roznica miedzy "efekt wygasl" a "efekt trwa,
ale jest za slaby" nie ma dla projektu znaczenia operacyjnego: obie prowadza
do tej samej decyzji.

## 5. Cena warunkowania — ile musi dac wersja warunkowa H004

Sens karty warunkowej polega na wybraniu podzbioru nocy, w ktorym efekt jest
silny. Ale zwezanie okna ma **policzalna cene**: Sharpe liczymy po wszystkich
dniach, nie tylko czynnych (rozdz. 6.3), wiec strategia handlujaca ulamek *f*
nocy musi miec na kazdej z nich edge wiekszy o czynnik **1/sqrt(f)**.

Prog certyfikacji DSR >= 0.95 przy T = 1438 dni i 4 wariantach karty:
**SR >= 1.13**.

Bezwarunkowy zwrot nocny 2021-2026 wynosi 0.0213% na noc.
Ile musialaby dac pojedyncza WYBRANA noc:

| Warunkowanie | Nocy czynnych | Zwrot/noc dla SR 0.8 | Krotnosc | Zwrot/noc dla DSR | Krotnosc |
|---|---|---|---|---|---|
| wszystkie noce | 1438 | 0.038% | 1.8x | 0.054% | **2.5x** |
| polowa | 719 | 0.054% | 2.5x | 0.076% | **3.6x** |
| jedna trzecia | 474 | 0.066% | 3.1x | 0.094% | **4.4x** |
| kwintyl | 287 | 0.085% | 4.0x | 0.120% | **5.6x** |
| decyl | 143 | 0.120% | 5.7x | 0.170% | **8.0x** |

**To jest wynik, ktorego sie nie spodziewalem i ktory zmienia sposob projektowania
kart.** Warunkowanie nie jest darmowe: zawezenie do decyla nocy wymaga, by kazda
z nich niosla 8x obecna srednia przewage. Koncentracja sygnalu
rosnie liniowo z zawezeniem, a kara za rzadkosc tylko pierwiastkowo — wiec
oplaca sie zawezac tylko wtedy, gdy mechanizm naprawde koncentruje przewage.

---

## 6. Werdykt dla karty H004

**H004 w postaci bezwarunkowej schodzi do benchmarkow.** Nie dlatego, ze
wykazalismy zanik efektu — tego wykazac sie nie da — tylko dlatego, ze
bezwarunkowy dryf nocny nie osiaga progu, ktory projekt sobie postawil.

**Wersja warunkowa pozostaje otwarta, ale z jawnie wycenionym progiem wejscia.**
Karta przeformulowana (audyt 3) pyta "jaki mechanizm decyduje, KIEDY efekt
wystepuje". Zanim spali choc jedna probe, musi zadeklarowac:

1. jaki ulamek nocy *f* wybiera jej warunek,
2. jaki zwrot na noc czynna zaklada — i czy przekracza prog z tabeli wyzej,
3. dlaczego mechanizm mialby dawac akurat taka koncentracje.

Jesli punkt 2 nie da sie obronic **przed testem**, karta schodzi do benchmarkow
regula samoczyszczaca z REGISTRY.md. Nie odkrywamy progu po fakcie.

Konsekwencje dla REGISTRY.md:

- H004 bezwarunkowa -> **BENCHMARK** (nie zuzywa licznika prob),
- H004 warunkowa -> **IDEA** z obowiazkowa deklaracja *f* i progu przed testem,
- wnioski przekrojowe **W001** i **W002** wchodza do rejestru.

## 7. Wnioski przekrojowe (do REGISTRY.md)

### W001 — poziomy bezwarunkowe sa poza zasiegiem tego projektu

> Przy dziennym odchyleniu zwrotu nocnego rzedu 0.75% odroznienie dryfu
> 3.7%/rok od zera wymaga ~86 lat danych. Kazda karta, ktorej teza brzmi
> "efekt X o sile kilku procent rocznie istnieje / wygasl", jest z gory
> nierozstrzygalna. **Nie wolno na nia wydawac proby** — ani nie wolno opierac
> decyzji projektowej na cudzym twierdzeniu tej klasy, niezaleznie od zrodla.

### W002 — warunkowanie ma cene rosnaca jak 1/sqrt(f)

> Zawezenie sygnalu do ulamka *f* okazji podnosi wymagany edge na pojedyncza
> okazje o czynnik 1/sqrt(f), bo Sharpe liczy sie po wszystkich dniach.
> Dla decyla to **8x** obecnej przewagi bezwarunkowej.
> Wniosek projektowy: **karta warunkowa musi deklarowac *f* z gory** i uzasadniac,
> skad ma wziac koncentracje przewagi. Warunek, ktory odsiewa 90% okazji "bo
> tak wyglada lepiej na wykresie", niemal na pewno nie przejdzie bramki —
> i mozna to stwierdzic ZANIM sie go przetestuje.

---

### Kontrola poprawnosci

Suma skladowych: +91.97% — tozsamosc dekompozycji
zachowana (noc + sesja = pelny zwrot buy-and-hold z pominieciem pierwszego dnia).
Wyniki spojne miedzy trzema niezaleznymi instrumentami (MNQ, NQ, ES), co wyklucza artefakt jednego zbioru danych.

Odtworzenie: `python3 research/W001_overnight_drift.py`
