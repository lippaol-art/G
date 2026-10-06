"""Wrazliwosc indeksu na skladniki — PLAN.pdf rozdz. 4.7, karta H013.

CO TEN MODUL LICZY. Wspolczynnik regresji zwrotu indeksu na zwroty osmiu
megacapow, estymowany z okna kroczacego. Jest to **historyczna reakcja indeksu**
na ruch skladnika — wielkosc zmierzona, obejmujaca zarowno mechaniczny udzial
skladnika w koszyku, jak i wspolruch reszty koszyka z tym skladnikiem.

TO NIE JEST ZAMIENNIK WAG, TYLKO INNY ESTYMAND.

Karta H013 w pierwotnym brzmieniu zakladala WAGI NDX ze snapshotow kwartalnych.
Zmiana nie polega na wzieciu tej samej wielkosci z innego zrodla — pytanie jest
inne i kontrfaktyk jest inny:

  waga w:        o ile zmieni sie wartosc indeksu, jesli poruszy sie WYLACZNIE
                 ten jeden skladnik, a pozostale 92 stoja w miejscu.
                 Wielkosc ksiegowa, wynika z konstrukcji koszyka.

  wrazliwosc s:  o ile indeks poruszal sie HISTORYCZNIE, gdy ten skladnik
                 poruszal sie o r — lacznie z tym, co w tym samym czasie robila
                 reszta koszyka. Wielkosc statystyczna, wynika z danych.

Zadne z tych dwoch nie jest "poprawniejsze" bezwarunkowo. Dla karty H013
wlasciwy jest drugi, bo karta pyta, ile indeks POWINIEN sie poruszyc — a gdy
NVDA rosnie 8% po wynikach, w praktyce rosna takze AMD, AVGO i pol koszyka
polprzewodnikowego. Kontrfaktyk "reszta stoi w miejscu" nie opisuje tej sytuacji.

Wybor jest jednak takze wymuszony praktycznie: historyczne wagi NDX 2019-2026 nie
sa dostepne z darmowego zrodla (publikowany jest sklad biezacy, archiwum kwartalne
to produkt platny), a przyjecie wag dzisiejszych dla calej historii byloby powaznym
bledem — wrazliwosc NVDA wzrosla u nas 0.053 -> 0.162.

Konsekwencja: **ablacja "wrazliwosci vs wagi" pozostaje OTWARTA i niewykonalna
bez platnych danych.** Nie wolno jej uznawac za rozstrzygnieta na tej podstawie,
ze wrazliwosci wypadaja lepiej od modelu naiwnego — to inne porownanie.

CO ZOSTALO ZMIERZONE OUT-OF-SAMPLE (reports/W007_wrazliwosci_walidacja.md,
1692 dni, predykcja dnia t z okna konczacego sie w t-1):

    wariant                          OOS R²    obciazenie   MAE
    ridge 1e-3, bez wyrazu wolnego   0.9436     +0.30‱     26.31‱
    OLS (lambda = 0)                 0.9436     +0.29‱     26.31‱
    ridge + wyraz wolny              0.9399     -0.67‱     27.38‱
    rowne wagi ze skala (naiwny)     0.9209     +1.34‱     30.61‱

Trzy wnioski, ktore trafily stad do kodu:

  1. Przewaga nad modelem naiwnym jest SKROMNA (0.921 -> 0.944). Rowne wagi
     przeskalowane jedna stala tlumacza wiekszosc tego samego.
  2. Model jest praktycznie NIEOBCIAZONY OOS (1.1% typowego bledu). To bylo
     wazne pytanie, bo stale przesuniecie w rezyduum jest nieodroznialne od
     sygnalu, ktorego szuka H013.
  3. Wyraz wolny nie pomaga i lekko szkodzi — jego brak jest decyzja poparta
     pomiarem, nie przeoczeniem.

ROK 2026 ODSTAJE: OOS R² 0.72 i obciazenie -8.59‱ wobec +0.30‱ na calej probie.
Indeks rosl wtedy bardziej, niz implikowaly megacapy. Karta H013 musi raportowac
wynik per rok, bo w takim okresie rezyduum ma przesuniecie pochodzace z modelu,
a nie z rynku.

ZAKAZ LOOKAHEADU. Wspolczynniki na dzien D szacowane sa wylacznie z okna
konczacego sie PRZED dniem D. Funkcja nie przyjmuje calego szeregu i nie ma
sciezki, ktora pozwolilaby zajrzec w przod.
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
#: CZEGO RIDGE TU NIE ROBI. Pierwsza wersja tego komentarza glosila, ze megacapy
#: sa wzajemnie skorelowane, wiec OLS daje wspolczynniki niestabilne i czesciowo
#: ujemne, a ridge to naprawia. **To bylo twierdzenie bez pokrycia.** W007 mierzy
#: oba estymatory OOS i daja wynik identyczny do czterech miejsc po przecinku
#: (R² 0.9436, MAE 26.31‱); ujemny wspolczynnik pojawia sie w 1 dniu na 1692.
#: Przy oknie 250 dni i osmiu regresorach macierz jest po prostu dobrze
#: uwarunkowana.
#:
#: Ridge zostaje z jednego, wezszego powodu: jest **tanim zabezpieczeniem na
#: wypadek okna zdegenerowanego** (halt, swieto, spolka po debiucie), gdzie OLS
#: rzucilby LinAlgError albo dal wspolczynniki bez sensu. Shrinkage ponizej 1%,
#: wiec nie kosztuje nic. Nie jest elementem niosacym wartosc predykcyjna.
RIDGE_LAMBDA = 1e-3     # ulamek sredniej przekatnej X'X


@dataclass(frozen=True)
class Wrazliwosci:
    """Wspolczynniki na jeden dzien wraz z miara dopasowania.

    UWAGA NA POLE `r2`. Jest to R² **in-sample** — liczone na tym samym oknie,
    na ktorym dopasowano wspolczynniki. Sluzy do wykrywania okna zdegenerowanego
    (nagly spadek = cos jest nie tak z danymi), a NIE jako miara jakosci modelu.
    Osiem regresorow zawsze da wysokie R² in-sample, niezaleznie od wartosci
    predykcyjnej. Publikowanie tego pola jako walidacji bylo bledem, ktory
    naprawia W007 — miara OOS jest tam i tylko tam.
    """

    symbole: tuple[str, ...]
    beta: np.ndarray
    #: R² IN-SAMPLE — diagnostyka okna, nie walidacja. Patrz docstring klasy.
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
