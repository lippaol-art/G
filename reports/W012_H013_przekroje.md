# W012 — przekroje proby H013 (audyt zamykajacy)

*Wygenerowane przez `research/W012_H013_przekroje.py`, 2026-08-02.*

**Status licznika prob: 0 zuzytych.**

## 0. Po co ten raport

Pierwotna karta H013 mowila o **kwartalnych wynikach osmiu megacapow
publikowanych po zamknieciu sesji** — okolo 8 x 4 x 7 = 224 zdarzen. W009
policzyl werdykt na wszystkich 261 zlozeniach 8-K item 2.02, w tym na
komunikatach Tesli o produkcji i dostawach oraz na publikacjach przed
otwarciem. To nie jest ta sama proba.

**Przekroje sa definicjami proby, nie wariantami strategii** — regula wejscia
i wyjscia jest w kazdym wierszu ta sama. Dlatego nie zuzywaja prob z budzetu
karty. Rozdzial wykonany z **tresci komunikatow prasowych**
(`scripts/classify_earnings.py`), nigdy z reakcji ceny.

## 1. Klasyfikacja zlozen

| Rodzaj | N | AMC | BMO |
|---|---|---|---|
| kwartalne wyniki finansowe | 230 | 228 | 2 |
| produkcja i dostawy | 29 | 5 | 23 |

Kontrola wewnetrzna: kazda spolka ma 28-30 raportow kwartalnych (~4 rocznie x 7 lat), a TSLA rozdziela sie na **29 dostaw i 29 raportow**.
Liczby te nie byly w zaden sposob dostrajane — reguly operuja na tytulach
komunikatow.

## 2. Wynik karty w kazdym przekroju

Kolumna `t` to wynik surowy (jak w W009), `t korr` — po korekcie obciazenia
modelu w sesje zdarzen (W011). `t gorny` dotyczy gornego tercyla \|rezyduum\|
i sprawdza, czy warunkowanie **poprawia** wynik, jak wymaga mechanizm.

| Przekroj | N | korelacja | sredni wynik | t | t korr | t gorny | lat + |
|---|---|---|---|---|---|---|---|
| **pelna proba W009** (wszystko) | 185 | +0.0893 | -0.0363% | **-0.79** | -0.11 | -0.56 | 4/7 |
| **tylko kwartalne wyniki** | 158 | +0.1220 | -0.0546% | **-1.10** | -0.71 | -0.80 | 4/7 |
| **kwartalne + AMC** (pierwotna definicja karty) | 157 | +0.1107 | -0.0512% | **-1.03** | -0.64 | -0.61 | 4/7 |
| kwartalne + BMO | 2 | — | — | — | — | — | — |
| tylko dostawy TSLA | 27 | -0.1841 | +0.0709% | **+0.60** | +1.50 | -0.07 | 0/0 |
| kwartalne, noce z jedna publikacja | 114 | +0.1552 | -0.1012% | **-1.76** | -1.27 | -1.15 | 2/7 |
| kwartalne, noce z wieloma publikacjami | 44 | +0.0241 | +0.0661% | **+0.69** | +0.66 | -0.36 | 3/6 |

## 3. Werdykt przekrojowy

**Przekroj zgodny z pierwotna definicja karty** (kwartalne wyniki, AMC) liczy
**157 sesji** i daje t = **-1.03** surowo, -0.64 po korekcie — wobec -0.79 na pelnej probie.

Sredni wynik na zdarzenie: **-5.7 pkt MNQ** przy progu
**+24.2 pkt** wymaganym dla SR ≥ 0.8 (sekcja 5 karty).

Warunkowanie na wielkosci rezyduum: t -0.64 → -0.61 w gornym tercylu. Mechanizm wymaga **poprawy**.

Stabilnosc: 4 lat dodatnich z 7.

**Kierunek wnioskow nie zmienia sie w zadnym przekroju.** Zawezenie proby do
pierwotnej definicji karty nie ujawnia efektu, ktory ginal w szumie dostaw
Tesli i publikacji przedsesyjnych.

Warto odnotowac przekroj **najczystszy mechanizmowo**: noce, w ktorych wyniki
publikowala **dokladnie jedna** spolka. Tam transmisja "news skladnika →
indeks" jest najmniej zaburzona, wiec karta powinna wypasc tam najlepiej.
Wypada **najgorzej** ze wszystkich przekrojow (N = 114, t = -1.76, po korekcie -1.27).

Dostawy Tesli daja jedyny dodatni odczyt (t korr +1.50), ale przy N = 27 i po
obejrzeniu wyniku — **nie jest to przeslanka do niczego** i nie otwieram na to
karty. Odnotowane wylacznie dla kompletnosci.

Przekroj "kwartalne + BMO" pominiety: w calej probie sa **2 takie zdarzenia**,
bo megacapy publikuja wyniki po zamknieciu. To samo w sobie potwierdza, ze
pierwotna karta slusznie mowila o publikacjach after-hours.

> **Mimo ograniczonej mocy uklad wynikow jest niezgodny z wczesniej
> zadeklarowanymi przewidywaniami mechanizmu, dlatego karta nie spelnia
> bramki GO.**

Nie jest to twierdzenie, ze udowodniono brak jakiegokolwiek edge'u — przy
157 zdarzeniach udowodnic tego nie sposob.

---

Odtworzenie: `python3 research/W012_H013_przekroje.py`
