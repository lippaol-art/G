# W006 — pre-flight H014 (dywergencja NQ-ES)

*Wygenerowane przez `research/W006_H014_preflight.py`, 2026-08-01. N = 1816 dni wspolnych.*

**Status licznika prob: 0 zuzytych.**

Karta twierdzi, ze NDX **przereagowuje** na szok stopowy wzgledem SPX, wiec
rezyduum NQ − β·ES powinno sie odwracac. Kalendarza makro jeszcze nie mamy,
wiec zamiast go zmyslac uzywamy proxy: **wielkosci rezyduum pierwszej godziny**.
Szok, jesli dziala jak opisuje mechanizm, musi sie objawic duzym rezyduum.

## 1. Konstrukcja rezyduum

| Wielkosc | Wartosc |
|---|---|
| β(NQ~ES), pierwsza godzina | 1.216 |
| β(NQ~ES), reszta sesji | 1.143 |
| sd zwrotu NQ (cala sesja) | 0.980% |
| **sd rezyduum NQ − βES** | **0.245%** |
| **Redukcja szumu przez hedge ES** | **75%** |

Redukcja szumu jest realna i duza — i to ona czyni te karte atrakcyjna
na papierze, bo obniza wymagany edge o ten sam czynnik. Sekcja 4 pokazuje,
dlaczego to nie wystarcza.

## 2. Przewidywanie mechanizmu: rezyduum ma sie ODWRACAC

korelacja(z₁, z₂) = **+0.0331** — dodatnia oznacza kontynuacje, ujemna odwrocenie.

| Warunek | *f* | N | Sredni wynik fade'u | t |
|---|---|---|---|---|
| gorny decyl \|z₁\| | 0.10 | 182 | -0.0161% | **-0.66** |
| gorny tercyl \|z₁\| | 0.33 | 606 | -0.0172% | **-1.54** |
| wszystkie dni | 1.00 | 1816 | -0.0131% | **-2.28** |

### Werdykt: karta odrzucona, i to z dwoch niezaleznych powodow

**Kierunek jest odwrotny** — rezyduum kontynuuje, zamiast wracac.

**Warunkowanie dziala na opak** — i to jest rozstrzygajace. Efekt jest
najsilniejszy na WSZYSTKICH dniach i najslabszy w gornym decylu. Gdyby
mechanizm mowil prawde, byloby odwrotnie: im wiekszy szok, tym wieksze
przereagowanie. Przeslanka o szoku stopowym zostaje tym obalona niezaleznie
od znaku.

Karte ze zlym znakiem mozna odwrocic. Karte, ktorej warunek warunkujacy
**pogarsza** wynik, mozna tylko wyrzucic — bo to znaczy, ze warunek nie ma
z efektem nic wspolnego.

## 3. Wariant kontynuacyjny — statystycznie niezly

| Miara | Wartosc |
|---|---|
| N (*f* = 1.00) | 1816 |
| Sredni wynik | +0.0131% dziennie |
| t | **+2.28** |
| **Sharpe brutto** | **+0.85** |

### Stabilnosc roczna — test, ktory zabil H005

| Rok | N | Sredni wynik | t | Udzial w wyniku |
|---|---|---|---|---|
| 2019 | 178 | -0.0007% | -0.07 | -0% |
| 2020 | 249 | +0.0187% | +0.76 | +20% |
| 2021 | 251 | +0.0174% | +1.16 | +18% |
| 2022 | 250 | +0.0029% | +0.19 | +3% |
| 2023 | 248 | +0.0146% | +1.12 | +15% |
| 2024 | 249 | +0.0236% | +1.93 | +25% |
| 2025 | 247 | +0.0089% | +0.76 | +9% |
| 2026 | 144 | +0.0171% | +0.73 | +10% |

Lat dodatnich: **7 z 8**. Najlepszy rok (2024) daje **25%** wyniku.

Stabilnosc jest tu **wyraznie lepsza niz w H005**, ktore zginelo na jednym roku
dajacym ponad polowe wyniku. Statystycznie to wyglada na cos prawdziwego.

## 4. Ekonomia — i tu wariant umiera

| Struktura | Brutto/dzien | Koszt | Netto/dzien | **Sharpe netto** |
|---|---|---|---|---|
| 1 noga (tylko MNQ) | +6.02 USD | 2.20 | +3.82 USD | **+0.54** |
| **2 nogi (MNQ + MES)** | +6.02 USD | 4.40 | +1.62 USD | **+0.23** |
| 2 nogi, stress ×2 (bramka 7.6) | +6.02 USD | 8.80 | -2.78 USD | **-0.39** |

**Koszty dwoch nog zjadaja 73% przewagi brutto.**
Sharpe spada z 0.85 do 0.23, a pod obowiazkowym stress-testem ×2 wynik jest **ujemny**.

Jest w tym gorzka ironia: ta sama konstrukcja dwunozna, ktora redukuje szum
o 75% i przez to podnosi Sharpe brutto, wymaga drugiej nogi —
a ta noga kosztuje wiecej, niz warta jest redukcja szumu przy tej wielkosci
przewagi. **Hedge oplaca sie dopiero powyzej progu edge'u, ktorego tu nie ma.**

Dlatego nie otwieram dla tego wariantu nowego ID. Zmierzony obiekt nie
przechodzi bramki w zadnej ze swoich handlowalnych postaci; otwarcie karty
oznaczaloby wydanie prob na cos, o czym juz wiemy, ze upada na kosztach.

## 5. Wniosek przekrojowy W006

> **Redukcja szumu przez hedge nie jest darmowa i przy malym edge'u jest
> stratna.** Druga noga podwaja koszt round-turn (2.20 -> 4.40 USD), wiec
> karta hedgowana musi wykazac przewage brutto **wyzsza niz wynikaloby z samego
> progu Sharpe'a** — o tyle, ile kosztuje dodatkowa noga. Prog oplacalnosci
> hedge'u przy naszych kosztach: okolo **2 punktow MNQ** przewagi brutto na
> transakcje. Ponizej tego progu lepiej handlowac jedna noge z wiekszym szumem.

Zastosowanie praktyczne: **H013 handluje jedna noge** (rezyduum jest tam
sygnalem, nie pozycja), wiec tego problemu nie ma. Roznica strukturalna
miedzy tymi kartami jest wieksza, niz sugeruje ich wspolna klasa K6.

---

Odtworzenie: `python3 research/W006_H014_preflight.py`
