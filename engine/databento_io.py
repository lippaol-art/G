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

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

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
