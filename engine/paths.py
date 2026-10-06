"""Sciezki do danych — z obsluga magazynu POZA repozytorium.

Specyfikacja: PLAN.pdf rozdz. 4.1 (trwalosc danych, manifest), rozdz. 4.5
(kontrola jakosci i wersjonowanie artefaktow).

PO CO TO ISTNIEJE.
Schemat `mbo` jest o dwa rzedy wielkosci ciezszy od `trades`: jedna sesja RTH
MNQU6 to **38,3 mln rekordow i 2,1 GB** wobec 0,98 mln i 0,047 GB dla `trades`.
Miesiac RTH w MBO to okolo **47 GB**. Takich danych nie trzyma sie ani
w repozytorium, ani w efemerycznym srodowisku o kilkudziesieciu gigabajtach.

`PROJECT_G_DATA_ROOT` pozwala wskazac katalog na dysku lokalnym. Bez tej
zmiennej wszystko dziala jak dotad, wzgledem katalogu repozytorium — dzieki
temu przelaczenie magazynu nie wymaga zmiany zadnego skryptu.

    export PROJECT_G_DATA_ROOT=/mnt/dane/projekt_g

CZEGO TA ZMIENNA NIE ROBI.
Nie przenosi `data/clean/` z repozytorium. Oczyszczone parquety sa **artefaktem
wersjonowanym** (rozdz. 4.1) i maja zostac w gicie — inaczej stracilibysmy
`hash_danych` jako punkt odniesienia golden baseline'u. Zmienna kieruje
wylacznie surowymi danymi, ktore i tak sa w `.gitignore`.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

#: Katalog repozytorium (dwa poziomy w gore od tego pliku).
REPO = Path(__file__).resolve().parent.parent

ZMIENNA = "PROJECT_G_DATA_ROOT"


def data_root() -> Path:
    """Katalog nadrzedny danych surowych.

    `PROJECT_G_DATA_ROOT`, gdy ustawiona i niepusta; inaczej `<repo>/data`.
    """
    v = os.environ.get(ZMIENNA, "").strip()
    return Path(v).expanduser().resolve() if v else REPO / "data"


def raw_dir(*czesci: str) -> Path:
    """Katalog danych surowych, opcjonalnie z podkatalogami."""
    return data_root().joinpath("raw", *czesci)


def clean_dir(*czesci: str) -> Path:
    """Katalog danych oczyszczonych.

    ZAWSZE w repozytorium, niezaleznie od `PROJECT_G_DATA_ROOT` — to artefakt
    wersjonowany, na ktorym stoi `hash_danych` golden baseline'u.
    """
    return REPO.joinpath("data", "clean", *czesci)


def wolne_gb(sciezka: Path | None = None) -> float:
    """Wolne miejsce w GB na systemie plikow danej sciezki.

    Sprawdzane PRZED pobraniem duzej probki: przerwany transfer na pelnym dysku
    zostawia obcieta sesje, a ta klasa awarii juz w tym projekcie wystapila.

    `shutil.disk_usage`, NIE `os.statvfs` — to drugie nie istnieje na Windows.
    Zlapane przy pierwszym uruchomieniu na maszynie lokalnej wlasciciela
    projektu (`mypy` na Windows: "Module has no attribute statvfs").
    """
    cel = sciezka or data_root()
    while not cel.exists() and cel != cel.parent:
        cel = cel.parent
    return shutil.disk_usage(cel).free / 1e9
