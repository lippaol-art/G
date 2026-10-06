# W004 — pre-flight partii 1 (H011, H010, H005)

*Wygenerowane przez `research/W004_partia1_preflight.py`, 2026-08-01. MNQ, 1861 dni sesyjnych.*

**Status licznika prob: 0 zuzytych.** Badanie rozkladow, nie backtest.
Zadna regula wejscia nie jest testowana ani optymalizowana — sprawdzamy,
czy zjawisko, o ktorym mowi mechanizm karty, da sie w ogole zmierzyc.

Powod istnienia: wniosek **W002** nakazuje deklarowac *f* i zakladana przewage
PRZED testem. Bez wiedzy, czy przeslanka istnieje, deklaracja bylaby zgadywaniem
za cene nieodnawialnego budzetu prob.

---

## H011 — sekwencja Azja->Europa jako predyktor RTH

**Mechanizm karty:** noc ma dwa rozne rezimy uczestnikow. Gdy Europa
KONTYNUUJE ruch Azji, oznacza to zgode co do kierunku i ustalona kontrole
nad rynkiem; gdy go ODWRACA, ruch azjatycki byl pozycjonowaniem, ktore
plynniejsza sesja europejska zbila.

Mechanizm robi **dwie przewidywania z gory** i sprawdzamy oba:

### Przewidywanie 1 — RTH podaza za kierunkiem uzgodnionym w nocy

| Kubelek | Dni | Udzial | Sredni zwrot RTH | t |
|---|---|---|---|---|
| Azja+ Europa+ | 536 | 28.8% | +0.0234% | +0.59 |
| Azja+ Europa− | 470 | 25.3% | -0.0043% | -0.10 |
| Azja− Europa+ | 486 | 26.1% | +0.0540% | +1.15 |
| Azja− Europa− | 369 | 19.8% | -0.0077% | -0.15 |

Kontrast zgoda − rozbieznosc: **-0.0198%, t = -0.44**. Brak efektu.

### Przewidywanie 2 — zgoda oznacza trend, rozbieznosc oznacza chaos

Miara charakteru sesji: *efficiency ratio* = |close − open| / (high − low).
Wysoki = ruch kierunkowy, niski = pilowanie.

| Wielkosc | Zgoda | Rozbieznosc | Roznica | t |
|---|---|---|---|---|
| efficiency ratio | 0.4800 | 0.4963 | -0.0163 | -1.34 |
| &#124;zwrot&#124; RTH | 0.0068 | 0.0071 | -0.0003 | -0.82 |
| zakres RTH / cena | 0.0132 | 0.0131 | +0.0001 | +0.25 |

### Werdykt H011 — **ODRZUCONA**

Oba przewidywania mechanizmu zawodza. Co gorsza, efficiency ratio idzie
w strone **przeciwna** do przewidywanej (rozbieznosc daje nieco wyzszy ER),
choc nieistotnie. Karta o najwyzszym priorytecie w katalogu — motywowana
najnizszym pokryciem z literatura — nie ma przeslanki.

Brak pokrycia w literaturze nie jest przewaga. Bywa informacja, ze nie ma
czego opisywac.

---

## H010 — zmiennosc zrealizowana wobec oczekiwanej jako warstwa rezimowa

**Mechanizm karty:** stosunek nocnego zakresu do jego normy przewiduje
CHARAKTER sesji (trend vs pilowanie) i moze sluzyc jako filtr rezimowy
dla innych kart.

| Wielkosc RTH | Szeroka noc (gorny tercyl) | Waska noc (dolny) | Roznica | t |
|---|---|---|---|---|
| zakres / cena | 0.0162 | 0.0112 | +0.0050 | **+10.22** |
| &#124;zwrot&#124; | 0.0084 | 0.0060 | +0.0024 | **+6.02** |
| efficiency ratio | 0.4850 | 0.4889 | -0.0039 | **-0.26** |

### Werdykt H010 — **ODRZUCONA W PROPONOWANEJ ROLI**

Tu efekt JEST i jest jednym z najsilniejszych w calym zbiorze: szeroka noc
zapowiada szerszy zakres RTH z t ponad 10. To jednak **klasteryzacja
zmiennosci** (Engle 1982), zjawisko opisane czterdziesci lat temu — i, co
rozstrzygajace, dotyczy WYLACZNIE amplitudy.

Efficiency ratio, czyli dokladnie ta wielkosc, o ktora karcie chodzilo,
**nie rozni sie miedzy rezimami** (t bliskie zera). Zmiennosc nocna mowi,
JAK DUZY bedzie ruch, ale nie mowi nic o tym, czy bedzie kierunkowy.

Karta zakladala filtr rezimowy typu trend/pilowanie dla innych hipotez —
i tego zalozenia dane nie potwierdzaja. Efekt zostaje w projekcie jako
**wejscie do wielkosci pozycji**, nie jako filtr kierunkowy.

> To rozroznienie jest wazniejsze niz sam wynik: **silny efekt to nie to samo
> co uzyteczny efekt.** t = 10 przy zlej zmiennej zaleznej jest wart mniej
> niz t = 2 przy wlasciwej.

---

## H005 — mikrostruktura kolejnych testow poziomu

**Mechanizm karty:** kolejne dotkniecia poziomu z dnia poprzedniego zuzywaja
plynnosc broniaca tego poziomu, wiec prawdopodobienstwo przebicia rosnie
z numerem dotkniecia.

Parametry pomiaru zadeklarowane z gory: bufor 5 pkt (ile cena musi sie cofnac, by kolejne dotkniecie liczylo sie osobno), horyzont 30 min. Poziom liczony na serii SUROWEJ (rozdz. 4.3).

### Sygnal wstepny

| Poziom | k | Zdarzen | Sredni zwrot [pkt] | t |
|---|---|---|---|---|
| PDH | 1 | 1029 | -1.401 | -0.62 |
| PDH | 2 | 616 | -1.046 | -0.48 |
| PDH | 3 | 419 | -1.186 | -0.50 |
| PDH | 4+ | 733 | **+4.816** | **+2.98** |
| PDL | 1 | 822 | +0.139 | +0.05 |
| PDL | 2 | 518 | +1.437 | +0.53 |
| PDL | 3 | 375 | +1.505 | +0.44 |
| PDL | 4+ | 789 | +1.670 | +0.89 |

Jedna komorka wyroznia sie: PDH przy czwartym i dalszym dotknieciu, **+4.82 pkt, t = +2.98** na 733 zdarzeniach.
Zgodne z kierunkiem mechanizmu. Ponizej cztery kontrole, ktore taki wynik
musi przejsc, zanim uznamy go za cokolwiek.

### Kontrola 1 — pozornosc: czy to nie jest po prostu pora dnia

Sredni zwrot bezwarunkowy w tych samych minutach sesji: **+0.098 pkt**. Nadwyzka zdarzen ponad ta kontrole: **+5.278 pkt, t = +3.03**.

Kontrola **zdana** — efekt nie jest przebrana pora dnia ani ogolnym dryfem.

### Kontrola 2 — symetria: mechanizm nie wyroznia strony

Ten sam pomiar po stronie PDL: **+1.670 pkt, t = +0.89** na 789 zdarzeniach.

Kontrola **niezdana**. Zuzywanie plynnosci broniacej poziomu nie ma powodu
dzialac tylko w gore. Asymetria bez wyjasnienia mechanizmem jest ostrzezeniem,
nie ciekawostka.

### Kontrola 3 — monotonicznosc: efekt ma rosnac z k, nie skakac

| k | Zdarzen | Sredni zwrot [pkt] | t |
|---|---|---|---|
| 1 | 1029 | -1.401 | -0.62 |
| 2 | 616 | -1.046 | -0.48 |
| 3 | 419 | -1.186 | -0.50 |
| 4 | 287 | +3.501 | +1.34 |
| 5 | 185 | +0.153 | +0.05 |
| 6 | 119 | +6.618 | +1.60 |
| 7 | 72 | +11.604 | +1.99 |

Kontrola **niezdana**. Profil nie rosnie — skacze przy k = 4, spada przy k = 5,
znow rosnie przy k = 6. Mechanizm mowi o stopniowym zuzywaniu plynnosci,
a to nie jest ksztalt stopniowego zuzywania. Prog 4 jest arbitralny.

### Kontrola 4 — stabilnosc w czasie

| Rok | Zdarzen | Sredni zwrot [pkt] | t | Udzial w wyniku |
|---|---|---|---|---|
| 2019 | 15 | -6.267 | -1.68 | -3% |
| 2020 | 116 | -1.338 | -0.37 | -4% |
| 2021 | 97 | +5.629 | +1.93 | +15% |
| 2022 | 95 | +10.208 | +2.27 | +27% |
| 2023 | 75 | +0.137 | +0.03 | +0% |
| 2024 | 119 | -1.964 | -0.51 | -7% |
| 2025 | 135 | +4.776 | +1.18 | +18% |
| 2026 | 81 | +22.744 | +3.43 | +52% |

Kontrola **niezdana, i to rozstrzygajaco**. Rok 2026 — niepelny, siedem miesiecy — daje **52% calego wyniku**. Lat ujemnych: 3 z 8.

Prog koncentracji z rozdz. 1.3 mowi o piatce najlepszych DNI ponizej 40%.
Tutaj pojedynczy niepelny ROK daje polowe wyniku.

### Werdykt H005 — **ODRZUCONA**

Efekt przeszedl kontrole pozornosci, przetrwal zmiane parametrow i podzial
probki na polowy — a mimo to jest jednym rokiem danych, widocznym tylko po
jednej stronie i bez monotonicznosci, ktorej wymaga jego wlasny mechanizm.

---

## Podsumowanie partii 1

| Karta | Wynik | Powod |
|---|---|---|
| H011 | **ODRZUCONA** | oba przewidywania mechanizmu zawodza, jedno ze znakiem przeciwnym |
| H010 | **ODRZUCONA W TEJ ROLI** | efekt bardzo silny, ale dotyczy amplitudy, nie charakteru |
| H005 | **ODRZUCONA** | sygnal upada na symetrii, monotonicznosci i stabilnosci rocznej |

**Zuzyte proby: 0 z budzetu 18** (3 karty x 6 wariantow). Pre-flight kosztowal
kilka godzin obliczen i uratowal caly budzet partii — a przy DSR kazda
niewydana proba podnosi szanse wszystkich pozostalych kart.

## Wnioski przekrojowe

### W004 — kolejnosc kontroli decyduje, co przezyje

> Sygnal H005 przeszedl kontrole pozornosci (pora dnia, dryf), zmiane czterech
> parametrow i podzial probki na polowy. Upadl dopiero na trzech kontrolach
> wyprowadzonych **z tresci mechanizmu**: symetrii, monotonicznosci i stabilnosci
> rocznej. Kontrole statystyczne sprawdzaja, czy liczba jest solidna; kontrole
> mechanizmu sprawdzaja, czy jest to ta liczba, o ktorej mowilismy.
> **Te drugie odrzucily wiecej i wczesniej.**

### W005 — silny efekt to nie to samo co uzyteczny efekt

> H010 dala najmocniejszy pojedynczy wynik calego dotychczasowego projektu
> (t > 10) i zostala odrzucona, bo mierzyla amplitude tam, gdzie karta
> potrzebowala kierunku. Przed uruchomieniem kazdej karty pytamy nie tylko
> "czy efekt istnieje", ale "czy istnieje w zmiennej, ktorej karta uzywa".

---

Odtworzenie: `python3 research/W004_partia1_preflight.py`
