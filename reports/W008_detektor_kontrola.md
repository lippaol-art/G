# W008 — detektor reakcji jako kontrola kalendarza

*Wygenerowane przez `research/W008_detektor_kontrola.py`, 2026-08-02. 14252 par (spolka, sesja), w tym 233 publikacji AMC.*

**Status licznika prob: 0 zuzytych.**

Detektor **nie definiuje proby** i nie moze jej definiowac — probe daje
kalendarz EDGAR. Tu jest testowany detektor, nie kalendarz. Uzasadnienie:
docstring `engine/earnings.py`.

Kontrola obejmuje wylacznie publikacje **AMC**, bo tylko one maja okno
after-hours w dniu publikacji. BMO wypadaja z tej kontroli z konstrukcji.

## 1. Czy publikacje w ogole odrozniaja sie od zwyklych dni

| Wielkosc | Dni publikacji | Pozostale dni | Iloraz |
|---|---|---|---|
| Ruch after-hours (mediana) | 3.56% | 0.11% | **32.5×** |
| Ruch after-hours (srednia) | 4.25% | 0.20% | **21.1×** |
| Iloraz obrotu (mediana) | 95.91× | 0.98× | **97.7×** |

To jest **warunek konieczny calej karty**, sprawdzony przed czymkolwiek
innym: gdyby publikacje nie odrozniały sie rozkladem od zwyklych sesji,
nie byloby czego transmitowac na indeks. Odroznia sie i to bardzo wyraznie.

Obrot liczony **z pominieciem minuty 16:00**, czyli wydruku aukcji zamkniecia.
Aukcja jest codziennie i jest ogromna, wiec wliczona do sumy rozcienczala
sygnal do niepoznaki — iloraz obrotu w dni publikacji wychodzil wtedy 1.8×
zamiast obecnych ~96×, a detektor wygladal na bezuzyteczny. Cena potrzebuje
tego wydruku (to jest zamkniecie), obrot nie.

### Okno pomiaru ma znaczenie — i to duze

Karta mierzy okno **16:00-17:00 ET** (sekcja 6). Gdyby mierzyc do konca
segmentu after-hours (20:00 ET), wyszlyby inne liczby:

| Okno | Mediana ruchu w dni publikacji |
|---|---|
| **16:00-17:00 (karta)** | **3.56%** |
| 16:00-20:00 (caly segment) | 4.16% |

Dla **22 z 233 publikacji** ruch do 17:00 jest wiekszy niz ruch
do 20:00 o co najmniej polowe — reakcja czesciowo **zawraca jeszcze przed
koncem sesji pozagieldowej**. Skrajny przypadek: MSFT 27.07.2021 poruszyl sie
o 3.33%, a o 19:59 stal 0.01% od zamkniecia RTH.

### Pomiar o 17:00 jest slabym estymatorem repricingu — to jest wazne

Trzy publikacje z sekcji 3 wygladaja na "brak reakcji" przy obrocie
130-270× tla. Przebieg wewnatrz godziny tlumaczy, dlaczego:

| Zdarzenie | Zakres 16:00-17:00 | Zwrot na 16:59 | Zwrot na 19:59 |
|---|---|---|---|
| META 2021-01-27 | 255.00 – 274.50 (**6.4%**) | **+0.01%** | −2.28% |
| AMZN 2023-10-26 | 118.47 – 126.00 (**5.3%**) | **+0.04%** | +5.21% |
| AVGO 2025-09-04 | 302.97 – 313.24 (**2.3%**) | **+0.03%** | +4.59% |

Kurs przechodzi przez cala amplitude reakcji i wraca do punktu wyjscia
dokladnie na koniec okna, po czym osiada kilka procent dalej. **Pojedynczy
odczyt o 17:00 nie mierzy tego, co karta chce zmierzyc.**

Zmierzone na calej probie AMC — zwrot na 17:00 wobec ostatniego notowania
przed otwarciem sesji kasowej (N = 231):

| Wielkosc | Wartosc |
|---|---|
| korelacja(r₁₇, r_przedotwarciem) | **0.850** |
| nachylenie regresji r_przed ~ r₁₇ | 1.04 |
| mediana \|r₁₇\| / \|r_przed\| | 81% |
| zdarzen, gdzie znak r₁₇ ≠ znak r_przed | **36 z 225 (16%)** |

Ostatni wiersz jest rozstrzygajacy dla konstrukcji karty. Sygnal karty to
**znak rezyduum**; jesli w kazdym takim przypadku znak samego zwrotu skladnika
zdazy sie odwrocic miedzy 17:00 a otwarciem, to rezyduum liczone na 17:00
opisuje stan, ktorego w momencie wejscia juz nie ma.

**Co z tym robimy — i czego NIE robimy.** Nie zmieniam teraz definicji okna,
bo wybor okna po zobaczeniu, ktore daje lepszy wynik, bylby strojeniem
(regula R2). Zamiast tego pytanie o okno wchodzi do pre-flightu jako
**deklarowane z gory rozstrzygniecie na kryterium pomiarowym**, nie na P&L:
okno ma byc tym, ktore najwierniej opisuje stan skladnika **w momencie
wejscia w pozycje**. Kandydatem naturalnym jest ostatnie notowanie przed
otwarciem RTH — jest dostepne przed transakcja, wiec nie jest lookaheadem,
i z definicji opisuje moment, w ktorym karta dziala.

## 2. Skutecznosc detektora wzgledem kalendarza

| Prog ruchu | Prog obrotu | Wykryte | Precision | Recall |
|---|---|---|---|---|
| 1% | 2× | 509 | 36.9% | 80.7% |
| 1% | 5× | 414 | 45.4% | 80.7% |
| 1% | 10× | 314 | 59.9% | 80.7% |
| 2% | 2× | 251 | 62.9% | 67.8% |
| 2% | 5× | 241 | 65.6% | 67.8% |
| 2% | 10× | 217 | 72.8% | 67.8% |
| 3% | 2× | 162 | 80.2% | 55.8% |
| 3% | 5× | 161 | 80.7% | 55.8% |
| 3% | 10× | 157 | 82.8% | 55.8% |

Najlepszy kompromis: ruch ≥ 2%, obrot ≥ 10× tla.
**Ta wartosc nie jest do niczego uzywana** — sluzy wylacznie do wyliczenia
rozbieznosci ponizej. Zaden prog nie wchodzi do proby H013.

## 3. Publikacje bez widocznej reakcji — kontrola kompletnosci danych

**75 z 233 publikacji** nie przekracza progu detektora.
Z tego **0** ma mniej niz 5 barow after-hours, czyli jest
podejrzeniem **dziury w danych**, a nie spokojnej publikacji.

Zadna publikacja nie ma pustego okna after-hours — **dane sa pod tym
wzgledem kompletne**. To wazne, bo brak barow czytalby sie jako
zerowa reakcja i wchodzil do sredniej jako pomiar.

Publikacje o najmniejszej reakcji przy kompletnych danych — **zostaja
w probie**, bo odrzucenie ich byloby dokladnie tym selection biasem,
ktorego unikamy:

| Spolka | Sesja | Ruch AH | Iloraz obrotu |
|---|---|---|---|
| TSLA | 2024-04-02 | 0.01% | 1.9× |
| META | 2021-01-27 | 0.01% | 211.5× |
| AVGO | 2025-09-04 | 0.03% | 136.5× |
| TSLA | 2024-01-02 | 0.03% | 0.7× |
| AMZN | 2023-10-26 | 0.04% | 139.4× |
| TSLA | 2025-04-22 | 0.08% | 15.9× |
| AVGO | 2023-06-01 | 0.08% | 271.1× |
| TSLA | 2025-07-23 | 0.08% | 12.9× |
| MSFT | 2020-10-27 | 0.09% | 47.9× |
| AVGO | 2021-06-03 | 0.09% | 21.0× |

## 4. Duze reakcje bez publikacji — tlo zdarzeniowe

**59 sesji** ma duza reakcje po zamknieciu bez wpisu 8-K 2.02 —
to okolo **20%** wszystkich duzych
reakcji. Sa to inne zdarzenia: guidance, zmiany w zarzadzie, decyzje
regulacyjne, przejecia, szoki sektorowe.

**Dla H013 jest to liczba istotna, a nie ciekawostka.** Rezyduum karty moze
byc napedzane takim zdarzeniem u innego skladnika, ktory tego wieczoru nie
publikowal wynikow. Karta liczy rezyduum ze WSZYSTKICH osmiu spolek, wiec
nie ma tu pomylki w konstrukcji — ale interpretacja "to reakcja na wyniki"
jest o tyle slabsza, o ile duze jest to tlo.

| Rok | Sesji z duza reakcja bez 8-K |
|---|---|
| 2019 | 3 |
| 2020 | 6 |
| 2021 | 3 |
| 2022 | 15 |
| 2023 | 9 |
| 2024 | 7 |
| 2025 | 14 |
| 2026 | 2 |

## 5. Wniosek dla kalendarza

Detektor **nie znalazl podstaw do zmiany kalendarza** i nie ma prawa go
zmieniac. Jego wynik jest kontrola jakosci danych i miara tla, nic wiecej.

Rozbieznosci z sekcji 3 i 4 sa spodziewane z konstrukcji: detektor mierzy
wielkosc reakcji, kalendarz mierzy fakt publikacji, a to sa rozne rzeczy.
Gdyby zgadzaly sie w 100%, oznaczaloby to, ze jedno z nich jest zbudowane
z drugiego — czyli dokladnie ta pulapke, ktorej caly ten podzial unika.

---

Odtworzenie: `python3 research/W008_detektor_kontrola.py`
