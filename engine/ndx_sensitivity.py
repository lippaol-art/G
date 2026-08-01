"""Wrazliwosc indeksu na skladniki — PLAN.pdf rozdz. 4.7, karta H013.

CO TEN MODUL LICZY I DLACZEGO NIE SA TO WAGI INDEKSU.

Karta H013 w pierwotnym brzmieniu zakladala uzycie WAG NDX ze snapshotow
kwartalnych. Odstepujemy od tego swiadomie, z dwoch powodow — pierwszy jest
praktyczny, drugi metodologiczny i wazniejszy.

PRAKTYCZNY. Historyczne wagi NDX za lata 2019-2026 nie sa dostepne z zadnego
darmowego zrodla. Publikowany jest sklad BIEZACY; archiwum kwartalne to produkt
platny. Przyjecie wag dzisiejszych dla calej historii byloby powaznym bledem —
waga NVDA wzrosla w tym okresie kilkukrotnie.

METODOLOGICZNY. Nawet majac prawdziwe wagi, uzycie ich byloby ZANIZENIEM.
Karta pyta: "o ile POWINIEN poruszyc sie indeks, skoro skladnik poruszyl sie
o r?". Odpowiedz "w * r" jest poprawna tylko w swiecie, w ktorym pozostale
92 spolki stoja w miejscu. W rzeczywistosci wynik megacapa przenosi sie
na caly sektor: gdy NVDA rosnie 8% po wynikach, rosna takze AMD, AVGO
i polowa koszyka polprzewodnikowego. Oczekiwany ruch indeksu jest wiec
WIEKSZY niz sama waga przemnozona przez zwrot.

Wielkoscia, ktora to obejmuje, jest WRAZLIWOSC — wspolczynnik regresji zwrotu
indeksu na zwrot skladnika. Zawiera oba kanaly: mechaniczny (waga) i posredni
(korelacja z reszta koszyka). Zmierzone na naszych danych sumy wspolczynnikow
wynosza 0.65-0.86 przy lacznej wadze osemki okolo 0.50 — roznica to wlasnie
kanal posredni.

Dla karty jest to zmiana na korzysc: rezyduum liczone wzgledem zanizonego
oczekiwania bylo by systematycznie przesuniete, a przesuniecie w rezyduum jest
nieodroznialne od sygnalu.

ZAKAZ LOOKAHEADU. Wspolczynniki na dzien D szacowane sa wylacznie z okna
konczacego sie PRZED dniem D. Funkcja nie przyjmuje calego szeregu i nie ma
sciezki, ktora pozwolilaby zajrzec w przod.

REGULARYZACJA. Megacapy sa wzajemnie skorelowane na poziomie 0.4-0.7, wiec
zwykly OLS daje wspolczynniki niestabilne i czesciowo ujemne. Ridge o malym
parametrze stabilizuje je, nie przesuwajac istotnie sumy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: Osiem najwiekszych skladnikow NDX w calym naszym zakresie. Sklad pierwszej
#: osemki byl w latach 2019-2026 stabilny; zmieniala sie kolejnosc i wagi.
MEGACAPY: tuple[str, ...] = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA")

OKNO_DNI = 250          # okolo roku sesyjnego — kompromis miedzy szumem a aktualnoscia
MIN_OKNO = 120          # ponizej tego wspolczynniki sa zbyt niestabilne, by ich uzyc
#: Sila regularyzacji jako UŁAMEK SREDNIEJ WARTOSCI WLASNEJ X'X, nie wartosc
#: bezwzgledna. Skalowanie bezwzgledne bylo pierwsza wersja tego modulu i bylo
#: bledem: zwroty dzienne maja rzad 0.02, wiec elementy X'X sa rzedu 0.2, a stala
#: lambda 0.06 kurczyla wspolczynniki o 20%. Suma spadala z 0.79 do 0.63.
#:
#: Konsekwencja bylaby powazna i cicha. Implikowany impuls wychodzilby
#: systematycznie ZA MALY, wiec rezyduum karty H013 mialoby stale przesuniecie
#: w strone ruchu indeksu — a takie przesuniecie jest nieodroznialne od sygnalu,
#: ktorego karta szuka. Backtest pokazalby przewage tam, gdzie jest tylko blad
#: estymatora.
#:
#: Wersja skalowana niezmienniczo daje shrinkage ponizej 1% i nadal stabilizuje
#: przypadek wspolliniowy.
RIDGE_LAMBDA = 1e-3     # ulamek sredniej przekatnej X'X


@dataclass(frozen=True)
class Wrazliwosci:
    """Wspolczynniki na jeden dzien wraz z miara dopasowania."""

    symbole: tuple[str, ...]
    beta: np.ndarray
    r2: float
    n_obs: int

    @property
    def suma(self) -> float:
        return float(self.beta.sum())

    def implikowany_impuls(self, zwroty: np.ndarray) -> float:
        """Oczekiwany zwrot indeksu przy zadanych zwrotach skladnikow.

        To jest lewa strona rownania H013: ile indeks POWINIEN sie poruszyc.
        Rezyduum karty to roznica miedzy ruchem faktycznym a ta wartoscia.
        """
        z = np.asarray(zwroty, dtype=float)
        if z.shape != self.beta.shape:
            raise ValueError(
                f"oczekiwano {self.beta.shape[0]} zwrotow ({', '.join(self.symbole)}), "
                f"dostano {z.shape[0]}"
            )
        return float(self.beta @ z)


def _ridge(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    """Ridge o sile skalowanej wzgledem danych — patrz komentarz przy RIDGE_LAMBDA."""
    G = X.T @ X
    skala = float(np.trace(G)) / X.shape[1]
    A = G + lam * skala * np.eye(X.shape[1])
    return np.linalg.solve(A, X.T @ y)


def dopasuj(
    zwroty_indeksu: np.ndarray,
    zwroty_skladnikow: np.ndarray,
    symbole: tuple[str, ...] = MEGACAPY,
    *,
    lam: float = RIDGE_LAMBDA,
) -> Wrazliwosci:
    """Wspolczynniki z JEDNEGO okna. Wejscie musi byc juz przycięte do okna.

    Rozdzielenie `dopasuj` od `krocząca` jest celowe: funkcja dopasowujaca nie
    widzi zadnej daty i nie moze przypadkiem siegnac poza okno.
    """
    y = np.asarray(zwroty_indeksu, dtype=float)
    X = np.asarray(zwroty_skladnikow, dtype=float)
    if X.ndim != 2 or X.shape[0] != y.shape[0]:
        raise ValueError(f"niezgodne ksztalty: y {y.shape}, X {X.shape}")
    if X.shape[1] != len(symbole):
        raise ValueError(f"{X.shape[1]} kolumn wobec {len(symbole)} symboli")
    if y.size < MIN_OKNO:
        raise ValueError(f"okno {y.size} dni ponizej minimum {MIN_OKNO}")

    beta = _ridge(X, y, lam)
    reszty = y - X @ beta
    war = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float((reszty**2).sum()) / war if war > 0 else 0.0
    return Wrazliwosci(symbole=symbole, beta=beta, r2=r2, n_obs=int(y.size))


def kroczaca(
    zwroty_indeksu: np.ndarray,
    zwroty_skladnikow: np.ndarray,
    indeks_docelowy: int,
    symbole: tuple[str, ...] = MEGACAPY,
    *,
    okno: int = OKNO_DNI,
    lam: float = RIDGE_LAMBDA,
) -> Wrazliwosci | None:
    """Wspolczynniki obowiazujace w dniu `indeks_docelowy`.

    Okno konczy sie na `indeks_docelowy - 1` WLACZNIE — dzien docelowy nie
    wchodzi do estymacji. To jest cala ochrona przed lookaheadem i dlatego jest
    tu jedna linijka, a nie rozproszona konwencja.

    Zwraca None, gdy historii jest za malo — jawnie, zeby wywolujacy musial
    zdecydowac, co z tym zrobic, zamiast dostac ciche zero.
    """
    if indeks_docelowy < MIN_OKNO:
        return None
    a = max(0, indeks_docelowy - okno)
    b = indeks_docelowy                      # wykluczajacy — klucz do braku lookaheadu
    return dopasuj(zwroty_indeksu[a:b], zwroty_skladnikow[a:b], symbole, lam=lam)
