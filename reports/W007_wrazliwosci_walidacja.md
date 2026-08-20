# W007 — walidacja out-of-sample modelu wrazliwosci

*Wygenerowane przez `research/W007_wrazliwosci_walidacja.py`, 2026-08-02. N = 1692 dni predykcji, 2019-10-25 → 2026-07-29.*

**Status licznika prob: 0 zuzytych.**

## 0. Dlaczego ten raport istnieje

Model wrazliwosci opublikowalem z tabela R² 0.887-0.982 podana tak, jakby
byla jego walidacja. **Nie byla** — to bylo R² in-sample, liczone na tym
samym oknie, na ktorym dopasowano wspolczynniki. Osiem regresorow zawsze
wyjdzie z takiej tabeli dobrze, niezaleznie od wartosci predykcyjnej.

Ponizsze liczby sa liczone inaczej: **predykcja dnia t z okna konczacego
sie w t-1**, okno 250 dni, przez cala historie. Model nie widzial
zadnej z nich w momencie estymacji.

## 1. Wynik out-of-sample

| Wariant | OOS R² | Obciazenie | MAE |
|---|---|---|---|
| **ridge 0.001, bez wyrazu wolnego (obecny)** | 0.9436 | +0.30‱ | 26.31‱ |
| OLS, bez wyrazu wolnego (lambda = 0) | 0.9436 | +0.29‱ | 26.31‱ |
| ridge + nieregularyzowany wyraz wolny | 0.9399 | -0.67‱ | 27.38‱ |
| ridge + standaryzacja + wyraz wolny (postac podrecznikowa) | 0.9434 | -1.01‱ | 26.35‱ |
| standaryzacja BEZ wyrazu wolnego (wariant zle postawiony) | 0.9384 | -8.24‱ | 27.99‱ |
| rowne wagi ze skala z okna (odniesienie) | 0.9209 | +1.34‱ | 30.61‱ |

Obciazenie i MAE w **dziesietnych punktach bazowych** (‱ = 0.01% = 1e-4).
Obciazenie = srednia predykcji minus srednia realizacji; dodatnie oznacza,
ze model systematycznie oczekuje od indeksu wiecej, niz indeks robi.

### Co z tego wynika — takze to, co niewygodne

**Ridge nie wnosi nic.** OLS i ridge daja OOS R² identyczne do czterech
miejsc po przecinku (0.9436 wobec 0.9436); roznica MAE wynosi
0.0078‱, czyli zero w kazdym praktycznym sensie. Narracja
z pierwszej wersji modulu, ze ridge "stabilizuje wspolczynniki, ktore OLS
daje niestabilne i czesciowo ujemne", byla **nieuprawniona**: przy oknie
250 dni i osmiu regresorach macierz jest dobrze uwarunkowana i OLS
radzi sobie tak samo. Ridge zostaje w kodzie jako **tanie zabezpieczenie na
wypadek okna zdegenerowanego**, nie jako element niosacy wartosc.

**Przewaga nad modelem naiwnym jest skromna**: R² 0.9209 → 0.9436, MAE 30.61‱ → 26.31‱.
Rowne wagi przeskalowane jedna stala tlumacza wiekszosc tego, co tlumacza
wrazliwosci. Model jest lepszy, ale nie o rzad wielkosci — i tak nalezy
o nim mowic.

**Model jest praktycznie nieobciazony OOS**: +0.30‱ przy MAE 26.31‱, czyli 1.1% bledu typowego.
To byla wlasciwa obawa i tu wynik jest dobry: **stale przesuniecie w rezyduum
jest nieodroznialne od sygnalu**, ktorego szuka H013, wiec model dokladajacy
wlasny dryf falszowalby te karte w sposob niewidoczny w backtescie.

**Wyraz wolny nie pomaga i lekko szkodzi.** Wersja z nieregularyzowanym
wyrazem wolnym ma R² 0.9399 (wobec 0.9436) i obciazenie
-0.67‱ (wobec +0.30‱). Postac podrecznikowa —
standaryzacja plus nieregularyzowany wyraz wolny — daje odpowiednio
0.9434 i -1.01‱. Zaden z tych wariantow nie jest lepszy
od obecnego, a wprowadzaja stopien swobody, ktory model moze wykorzystac
na dryf. Brak wyrazu wolnego jest wiec **decyzja poparta pomiarem**.

**Sama standaryzacja bez wyrazu wolnego psuje model** (obciazenie -8.24‱).
Nie jest to argument przeciw standaryzacji jako takiej — to wariant zle
postawiony i wpisany do tabeli celowo. Centrowanie X przy niecentrowanym y
i braku wyrazu wolnego **zmienia model**, a nie tylko jego uwarunkowanie:
predykcja traci czlon, ktory wczesniej niosla srednia regresorow. Wniosek
praktyczny: standaryzacji nie wolno dokladac "na wszelki wypadek" bez
wyrazu wolnego, a skoro wyraz wolny nie pomaga (wyzej), obie rzeczy
zostaja poza modelem.

Skalery i lambda pochodza **wylacznie z okna** konczacego sie w t−1;
lambda jest stala projektowa, nie byla dobierana pod wynik OOS z tej tabeli.

## 2. Wlasnosci wspolczynnikow — sprostowanie, nie dowod

| Wielkosc | Wartosc |
|---|---|
| Suma wspolczynnikow, zakres | 0.653 – 0.896 |
| Suma wspolczynnikow, mediana | 0.818 |
| Dni z **jakimkolwiek** ujemnym wspolczynnikiem | 1 z 1692 (0.1%) |
| Wrazliwosc NVDA, poczatek → koniec | 0.053 → 0.162 |

**Zadna z tych liczb nie jest testem modelu i nie nalezy ich tak podawac.**

Suma wspolczynnikow **nie ma powodu** rownac sie sumie wag osemki. To sa
dwie rozne wielkosci: waga mierzy mechaniczny udzial w koszyku, wspolczynnik
regresji mierzy historyczna reakcje indeksu, ktora obejmuje takze ruch
reszty koszyka skorelowanej ze skladnikiem. Roznica jest **spodziewana
z konstrukcji** i jej wystapienie nie potwierdza niczego.

Rosnaca wrazliwosc NVDA jest **kontrola sensownosci**, nie niezaleznym
potwierdzeniem. Zgadza sie z tym, co wiadomo o wzroscie wagi NVDA, ale
wspolczynnik moglby rosnac takze z innych powodow — na przyklad dlatego, ze
caly sektor polprzewodnikowy zaczal poruszac indeksem mocniej. Kontrola
wypada dobrze; dowodem nie jest.

Odsetek dni z ujemnym wspolczynnikiem (0.1%) mowi
tylko tyle, ze estymacja jest stabilna znakowo. **Nie dowodzi, ze ridge
cokolwiek naprawil** — OLS z sekcji 1 daje ten sam wynik predykcyjny.

## 3. Stabilnosc w czasie

| Rok | N | OOS R² | Obciazenie | Mediana sumy wspolczynnikow |
|---|---|---|---|---|
| 2019 | 45 | 0.9072 | +1.75‱ | 0.848 |
| 2020 | 252 | 0.9751 | +1.36‱ | 0.883 |
| 2021 | 251 | 0.9445 | +2.98‱ | 0.834 |
| 2022 | 251 | 0.9736 | -1.58‱ | 0.822 |
| 2023 | 250 | 0.9346 | +3.06‱ | 0.819 |
| 2024 | 251 | 0.9184 | +2.41‱ | 0.731 |
| 2025 | 249 | 0.9333 | -1.67‱ | 0.758 |
| 2026 | 143 | 0.7217 | -8.59‱ | 0.744 |

### Rok 2026 odstaje i nie wolno tego przemilczec

R² spada do **0.7217** wobec 0.9072–0.9751
w pozostalych latach, a obciazenie rosnie do **-8.59‱** — przy
maksimum 3.06‱ gdzie indziej. Prawie dziesieciokrotnie wiecej
niz w calej probie.

Znak jest tu informacja. Ujemne obciazenie znaczy, ze **indeks rosl bardziej,
niz implikowaly megacapy** — czyli ruch przenosil sie na pozostale spolki
koszyka, ktorych model nie obserwuje. Osiem regresorow opisuje wtedy mniej
niz zwykle i systematycznie zaniza oczekiwanie.

**Dla H013 jest to ostrzezenie pierwszej kategorii.** Karta czyta rezyduum
jako niedowycenienie kontraktu. W okresie o takim obciazeniu rezyduum ma
**stale przesuniecie pochodzace z modelu, nie z rynku** — a karta nie ma jak
tych dwoch rzeczy odroznic. Pre-flight musi wiec raportowac wynik per rok
i osobno sprawdzic, czy efekt nie pochodzi z 2026.

Zastrzezenie: 2026 jest u nas niepelny (**143 dni**), wiec czesc
roznicy to mniejsza probka. Nie tlumaczy to jednak znaku obciazenia, ktory
jest zjawiskiem, nie szumem.

## 4. Czego ten raport NIE rozstrzyga

**Ablacja "wrazliwosci vs wagi NDX" pozostaje otwarta.** Historycznych wag
NDX nie mamy — sa produktem platnym, a przyjecie wag dzisiejszych dla calej
historii byloby bledem powazniejszym niz problem, ktory miałyby rozwiazac
(wrazliwosc NVDA wzrosla u nas 0.053 → 0.162).

Ten raport porownuje wrazliwosci z modelem **naiwnym**, nie z wagami.
To dwie rozne rzeczy i nie wolno drugiej podstawiac za pierwsza. W karcie
H013 ablacja piata zostaje oznaczona jako **NIEWYKONALNA bez platnych
danych**, a nie jako rozstrzygnieta.

Nie rozstrzygamy tez, czy model jest **wystarczajaco dobry dla H013**.
MAE 26‱ to okolo 0.26% dziennie — wielkosc porownywalna
z rezyduum, ktorego karta szuka. **To jest ostrzezenie, nie detal:** jesli
blad modelu jest tego samego rzedu co sygnal, karta moze mierzyc wlasny
szum estymacyjny. Pre-flight musi to sprawdzic wprost, porownujac rozklad
rezyduum w dni zdarzen z rozkladem w dni zwykle.

---

Odtworzenie: `python3 research/W007_wrazliwosci_walidacja.py`
