# Kalendarz publikacji wynikow — SEC EDGAR 8-K item 2.02

*Wygenerowane przez `scripts/build_earnings.py`, 2026-08-02. Zakres: 2019-05-06 → 2026-07-29, 1813 sesji.*

**261 publikacji** osmiu megacapow. Zrodlo darmowe i autorytatywne;
proba **nie jest** wybierana po wielkosci reakcji rynku — uzasadnienie
w docstringu `engine/earnings.py`.

## 1. Rozklad wzgledem sesji

| Klasa | N | Udzial | Sesja reakcji |
|---|---|---|---|
| **AMC** (po zamknieciu) | 235 | 90.0% | nastepna |
| **BMO** (przed otwarciem) | 25 | 9.6% | ta sama |
| POZA_SESJA (weekend/swieto) | 1 | 0.4% | najblizsza |
| SRODSESYJNE | 0 | 0.0% | **wykluczone z proby podstawowej** |

Zdarzen uzytecznych dla H013: **259**.

Klasyfikacja liczona wzgledem **zaobserwowanych granic sesji tego konkretnego
dnia**, nie stalych 09:30-16:00 — dzieki temu dni skrocone (13:00 ET) sa
obsluzone bez tablicy wyjatkow: publikacja o 13:30 w wigilie jest AMC,
a nie srodsesyjna.

## 2. Pulapka strefy czasowej — wykryta i ominieta

**Dla 29 z 261 publikacji pole `acceptanceDateTime`
z API `submissions` NIE jest tym, na co wyglada.** Konczy sie litera Z, ale
dla czesci spolek zawiera czas wschodni bez konwersji:

| Spolka | Publikacji z bledna strefa |
|---|---|
| MSFT | 29 |

Przyjecie tego pola za dobra monete przesunelo by te zdarzenia o cztery
godziny wstecz — z okolic 16:0x ET (po zamknieciu) na 12:0x ET (srodek sesji).
Karta H013 zaklasyfikowalaby je jako srodsesyjne i **odrzucila**, albo — gorzej
— liczylaby rezyduum z okna, w ktorym publikacji jeszcze nie bylo.
**Zaden wyjatek by nie poleciał.**

Dlatego czas przyjecia bierzemy ze **strony indeksu zlozenia** (pole
"Accepted", zawsze ET, zgodne co do sekundy z naglowkiem
ACCEPTANCE-DATETIME pelnego zlozenia). API `submissions` mowi nam, ktore
zlozenia istnieja — nie mowi, kiedy zostaly przyjete.

### Godzina publikacji AMC

| Godzina ET | N |
|---|---|
| 16:01 | 24 |
| 16:02 | 5 |
| 16:03 | 14 |
| 16:04 | 7 |
| 16:05 | 1 |
| 16:06 | 6 |
| 16:07 | 6 |
| 16:08 | 9 |
| 16:09 | 9 |
| 16:10 | 7 |
| 16:11 | 3 |
| 16:12 | 2 |

Koncentracja tuz po 16:00 ET jest kontrola poprawnosci: publikacje wynikow
megacapow wychodza kilka-kilkanascie minut po zamknieciu sesji kasowej.

## 3. Pokrycie

| Spolka | N publikacji | Oczekiwane (~4/rok) |
|---|---|---|
| AAPL | 28 | 29 |
| MSFT | 29 | 29 |
| NVDA | 30 | 29 |
| AMZN | 28 | 29 |
| GOOGL | 30 | 29 |
| META | 29 | 29 |
| AVGO | 29 | 29 |
| TSLA | 58 | 29 |

| Rok | N |
|---|---|
| 2019 | 20 |
| 2020 | 36 |
| 2021 | 36 |
| 2022 | 37 |
| 2023 | 37 |
| 2024 | 36 |
| 2025 | 36 |
| 2026 | 23 |

## 4. Zastrzezenia — znane ograniczenia tej proby

**Komunikat prasowy to nie konferencja wynikowa.** EDGAR datuje zlozenie 8-K,
czyli moment publikacji liczb. Konferencja zaczyna sie zwykle okolo godziny
pozniej i potrafi **odwrocic** reakcje na sam komunikat. Kalendarz tego nie
rozdziela i nie udaje, ze rozdziela.

**Nie kazdy 8-K 2.02 to wyniki kwartalne.** Pozycja 2.02 obejmuje kazde
ujawnienie wynikow operacyjnych, wiec trafiaja tu takze korekty i komunikaty
posrednie. Nie filtrujemy ich po wielkosci reakcji — to bylby dokladnie ten
selection bias, ktorego caly ten modul unika. Odchylenia od ~4/rok w tabeli
wyzej sa wiec spodziewane i **nie sa** defektem danych.

**TSLA jest tu przypadkiem osobnym: 58 publikacji zamiast
~29, w tym 23 przed otwarciem sesji.** Tesla sklada 8-K 2.02
takze dla kwartalnych danych o produkcji i dostawach — osobnego zdarzenia,
wychodzacego rano na poczatku kwartalu, kilkanascie dni przed wlasciwym
raportem finansowym. Sa to prawdziwe publikacje wynikow operacyjnych i zostaja
w probie, ale **karta H013 musi je raportowac osobno**: mechanizm transmisji
moze dzialac inaczej dla danych o dostawach niz dla rachunku zyskow i strat,
a przy jednej spolce dajacej dwa razy wiecej zdarzen niz pozostale roznica
ta nie rozmyje sie w sredniej.

**2 publikacji bez sesji reakcji** — na koncu probki nie ma
juz kolejnej sesji w naszych danych. Odrzucane jawnie, nie przypisywane
do zlej daty:

- META 2026-07-29 16:03 ET (AMC)
- MSFT 2026-07-29 16:04 ET (AMC)

---

Dane: `data/clean/earnings.csv`. Odtworzenie: `python3 scripts/build_earnings.py`
