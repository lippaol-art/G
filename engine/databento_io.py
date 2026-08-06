"""Odporne wywolania API Databento — z ROZROZNIENIEM, co wolno ponawiac.

Specyfikacja: PLAN.pdf rozdz. 4.1 (Databento jako zrodlo podstawowe), poprawka
A4-11 z audytu 4 (odpornosc na zmiany i awarie po stronie dostawcy).

DLACZEGO TO ISTNIEJE I DLACZEGO NIE JEST ZWYKLYM `retry`.

Blad HTTP 504 wystapil w tym projekcie trzy razy i za kazdym razem w innym
miejscu. Rozroznienie jest krytyczne dla kosztu:

  * **METADANE** (`get_cost`, `get_record_count`, `get_billable_size`) sa
    DARMOWE, read-only i idempotentne. Zaden plik nie powstaje. Ponowienie
    jest calkowicie bezpieczne i tutaj je stosujemy.

  * **POBIERANIE** (`timeseries.get_range`) jest PLATNE i tworzy plik.
    Slepe ponowienie grozi podwojnym naliczeniem i cichym pozostawieniem
    obcietej sesji, ktora parsuje sie bez bledu. Tego NIE ponawiamy
    automatycznie — decyzje podejmuje czlowiek po sprawdzeniu, czy plik
    powstal i czy jest kompletny.

Ten modul obsluguje WYLACZNIE pierwszy przypadek. Brak funkcji ponawiajacej
pobieranie jest celowy.
"""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable, Iterator
from typing import TypeVar

T = TypeVar("T")

#: Domyslna dlugosc kawalka przy dzieleniu zapytania metadanych, w minutach.
#: 30 min daje dla MBO ~1,3-6,2 mln rekordow i czasy 2,5-37 s — z zapasem
#: pod 60-sekundowym limitem bramy.
KAWALEK_MIN = 30

#: Odstepy miedzy probami, w sekundach. Rosnace, zeby nie dobijac bramy,
#: ktora wlasnie zglosila przeciazenie.
ODSTEPY = (2, 5, 12, 30)


def metadane_z_ponowieniem(
    fn: Callable[..., T],
    *args,
    opis: str = "zapytanie metadanych",
    odstepy: tuple[int, ...] = ODSTEPY,
    **kwargs,
) -> T:
    """Wywoluje DARMOWE zapytanie metadanych, ponawiajac po bledzie serwera.

    Ponawiamy tylko bledy 5xx i przekroczenia czasu — czyli awarie po stronie
    dostawcy. Bledy 4xx (zly zakres, brak uprawnien, przekroczony limit) sa
    trwale i ponawianie ich niczego nie naprawi, wiec przechodza dalej od razu.
    """
    ostatni: Exception | None = None
    for i, pauza in enumerate((*odstepy, None), start=1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:                       # noqa: BLE001
            tekst = f"{type(e).__name__}: {e}"
            przejsciowy = any(
                s in tekst for s in ("504", "502", "503", "gateway", "Gateway",
                                     "timed out", "timeout", "Timeout")
            )
            if not przejsciowy or pauza is None:
                raise
            ostatni = e
            print(f"  {opis}: proba {i} nieudana ({tekst[:80]}), "
                  f"ponawiam za {pauza} s...", flush=True)
            time.sleep(pauza)
    raise RuntimeError(f"{opis}: wyczerpano proby") from ostatni


def _kawalki(start: str, end: str, minut: int) -> Iterator[tuple[str, str]]:
    """Dzieli zakres `YYYY-MM-DDTHH:MM` na odcinki po `minut`."""
    fmt = "%Y-%m-%dT%H:%M"
    a = dt.datetime.strptime(start, fmt)
    koniec = dt.datetime.strptime(end, fmt)
    while a < koniec:
        b = min(a + dt.timedelta(minutes=minut), koniec)
        yield a.strftime(fmt), b.strftime(fmt)
        a = b


def metadane_dzielone(
    fn: Callable[..., float],
    *,
    start: str,
    end: str,
    opis: str = "metadane",
    minut: int = KAWALEK_MIN,
    postep: bool = False,
    odstepy: tuple[int, ...] = ODSTEPY,
    **kwargs,
) -> float:
    """Sumuje DARMOWE metadane po kawalkach zakresu czasu.

    DLACZEGO DZIELIMY, A NIE TYLKO PONAWIAMY. Dla schematu `mbo` jedno
    zapytanie o pelna sesje RTH (38,3 mln rekordow) trwa 54-60 s, a brama
    Databento tnie na 60 s. To nie jest chwilowa awaria, tylko ROZMIAR
    zapytania na granicy limitu — ponawianie takiego wywolania jest loteria.
    Zmierzone na tej samej sesji: `get_cost` 504 po 60,6 s, `get_record_count`
    OK po 53,9 s, `get_billable_size` 504 po 60,5 s. Trzy identyczne co do
    zakresu zapytania, trzy rozne wyniki.

    POPRAWNOSC SUMOWANIA JEST ZWERYFIKOWANA EMPIRYCZNIE, nie zalozona.
    Ta sama sesja, 13 kawalkow po 30 min: suma **38 306 877** rekordow
    i **3,5961 USD** — zgodne z wartoscia dla calego zakresu co do rekordu
    i co do czwartego miejsca po przecinku. Koszt Databento jest liniowy
    w liczbie rekordow i nie ma oplaty minimalnej, wiec podzial NIE zmienia
    kwoty.

    Dziala dla `get_cost` (float), `get_record_count` (int) i
    `get_billable_size` (int) — wszystkie sa addytywne.
    """
    czesci = list(_kawalki(start, end, minut))
    if not czesci:
        raise ValueError(f"{opis}: pusty zakres {start}..{end} — nie ma czego "
                         "wyceniac; sprawdz kolejnosc granic")
    suma: float = 0
    for i, (a, b) in enumerate(czesci, start=1):
        v = metadane_z_ponowieniem(fn, start=a, end=b, odstepy=odstepy,
                                   opis=f"{opis} [{i}/{len(czesci)}]", **kwargs)
        # KAWALEK UJEMNY NIE ISTNIEJE. Liczba rekordow, bajtow i koszt sa
        # nieujemne z definicji, wiec wartosc ujemna oznacza, ze `fn` nie jest
        # tym, czym myslimy — sumowanie jej dalej ukryloby blad w totalu.
        if v < 0:
            raise ValueError(f"{opis}: kawalek {i}/{len(czesci)} ({a}..{b}) "
                             f"zwrocil {v} — wartosc ujemna jest niemozliwa")
        suma += v
        if postep:
            print(f"  {opis} {a[11:]}-{b[11:]}: {v:,}" if isinstance(v, int)
                  else f"  {opis} {a[11:]}-{b[11:]}: {v:.4f}", flush=True)
    # ZERO W SUMIE TO ALARM, NIE WYNIK. Wywolujemy to wylacznie dla sesji,
    # o ktorych z gory wiadomo, ze sa handlowe — zero oznacza wiec zly symbol,
    # zly zbior albo zakres poza dostepnoscia danych, a nie "tania sesja".
    # Bez tej kontroli blad objawilby sie jako ZANIZONA wycena, czyli w strone,
    # ktora przepuszcza zakup przez limit kosztu zamiast go zatrzymac.
    if suma <= 0:
        raise ValueError(f"{opis}: suma {len(czesci)} kawalkow wynosi {suma} "
                         f"dla zakresu {start}..{end}. Sesja handlowa nie moze "
                         "byc pusta — sprawdz symbol, zbior i dostepnosc danych "
                         "ZANIM cokolwiek kupisz.")
    return suma
