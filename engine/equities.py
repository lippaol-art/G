"""Akcje: sklejanie tickerow i korekta splitow — PLAN.pdf rozdz. 4.7 (warstwa K6).

Odpowiednik `engine/roll.py` dla instrumentow kasowych. Dwa problemy, ktorych
kontrakty terminowe nie maja, a akcje maja oba:

  (a) TICKER ZMIENIA SIE W CZASIE. Meta handlowala sie jako FB do 2022-06-09.
      Zapytanie o "META" za rok 2019 zwraca pusty wynik — po cichu gubi spolke,
      nie rzucajac bledu.

  (b) SPLITY. Databento podaje ceny JAK HANDLOWANE. Na dzien splitu 20:1 surowa
      cena spada o 95% i wyglada jak krach. W sumie wazonej skladnikow indeksu
      taki "krach" przenosi sie wprost na sygnal.

ROZNICA WOBEC KONTRAKTOW: korekta jest MULTIPLIKATYWNA, nie roznicowa. Przy
rolowaniu futures przesuwamy historie o staly SPREAD, bo znaczenie ma roznica
cen. Przy splicie dzielimy historie przez WSPOLCZYNNIK, bo znaczenie ma stosunek
— split nie zmienia wartosci pozycji, zmienia liczbe akcji.

DLACZEGO NIE WYKRYWAMY SPLITOW SAMA WIELKOSCIA RUCHU. Meta spadla 3 lutego 2022
o 26% w jedna sesje. To nie byl split — to byla reakcja na wyniki. Prog oparty
na samej wielkosci zmiany "poprawilby" ten krach, kasujac prawdziwe zdarzenie
rynkowe, ktore dla karty H013 jest wrecz najciekawszym punktem danych.

Stad DWA NIEZALEZNE WARUNKI, ktore musza zajsc jednoczesnie:

  1. wspolczynnik ceny blisko prostego ulamka (2, 3, 4, 5, 10, 20, 3/2, 4/3...),
  2. wolumen skaluje sie tym samym wspolczynnikiem — bo po splicie k:1 handluje
     sie okolo k razy wiecej akcji o k razy nizszej cenie.

Warunek 2 jest kluczowy: krach cenowy NIE zmienia liczby akcji w obrocie
w sposob proporcjonalny do spadku, a split zmienia — z definicji. Zadne
zdarzenie fundamentalne nie podrabia obu warunkow naraz.

Kazdy kandydat trafia do raportu razem z dowodami, takze odrzucony. Korekta ma
byc audytowalna, nie automatyczna.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np

#: Ticker -> (poprzednik, data zmiany). Szereg sklejamy w jeden pod nowa nazwa.
POPRZEDNIE_TICKERY: dict[str, tuple[str, date]] = {
    "META": ("FB", date(2022, 6, 9)),
}

#: Wspolczynniki splitow dopuszczane przez detektor. Lista jest krotka
#: i zaczyna sie od 1.5 CELOWO.
#:
#: Kusi, zeby dopisac 5/4, 4/3, 7/5 — takie splity istnieja. Ale odpowiadaja
#: spadkom ceny o 20-30%, czyli dokladnie temu, co robi megacap po zlych
#: wynikach. Meta stracila 26% dnia 03.02.2022, Netflix 35% w kwietniu tego
#: samego roku. Dopuszczenie tych ulamkow oznacza, ze detektor "poprawi"
#: prawdziwe reakcje na wyniki — a te sa dla karty H013 nie szumem, tylko
#: CALYM PRZEDMIOTEM BADANIA.
#:
#: Asymetria ryzyka jest jednoznaczna. Przeoczony split 5:4 to jeden bledny
#: zwrot dla jednej spolki, widoczny w raporcie jakosci. Skasowany krach po
#: wynikach to wyciecie najbardziej informacyjnego zdarzenia w calym zbiorze,
#: i to w sposob niewidoczny. Wybieramy pierwsze ryzyko.
#:
#: Megacapy w naszym zakresie dzielily sie 2:1, 3:1, 4:1, 5:1, 10:1 i 20:1 —
#: wszystkie powyzej progu. 1.5 rowniez usuniete: split 3:2 jest wsrod duzych
#: spolek praktycznie niespotykany, a odpowiada spadkowi o 33%, czyli wprost
#: zakresowi krachu po wynikach.
DOPUSZCZALNE_WSPOLCZYNNIKI: tuple[float, ...] = (
    2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 15.0, 20.0, 30.0,
)

PROG_KANDYDATA = 0.22        # |log(ratio)| — okolo 20% zmiany ceny

#: Tolerancja SZEROKA, i to jest wynik uruchomienia na realnych danych.
#:
#: W dniu splitu cena porusza sie takze normalnie, wiec stosunek NIE trafia
#: w okragla liczbe. Zmierzone przypadki z naszego zbioru:
#:
#:     AAPL 2020-08-31   cena x3.871  wolumen x4.44   split 4:1
#:     TSLA 2020-08-31   cena x4.441  wolumen x5.49   split 5:1  (TSLA +12.6% tego dnia)
#:     SOXX 2024-03-07   cena x2.900  wolumen x2.94   split 3:1
#:
#: Przy tolerancji 3% wszystkie trzy zostaly PRZEOCZONE. Ale samo poluzowanie
#: tolerancji jest niebezpieczne: krach META (-26%, stosunek 1.358) trafilby
#: wtedy w 1.5, a spadek AVGO w marcu 2020 (1.249) rowniez.
#:
#: Stad zmiana konstrukcji: wolumen przestaje byc samym WETEM, a staje sie
#: rownorzednym IDENTYFIKATOREM. Po splicie k:1 cena dzieli sie przez k
#: I wolumen mnozy przez k — obie wielkosci wskazuja TEN SAM k. Krach spelnia
#: to tylko przypadkiem: META ma cene 1.358 przy wolumenie 4.08, czyli zaden
#: wspolny wspolczynnik nie istnieje.
TOLERANCJA = 0.15            # dopuszczalne odchylenie stosunku CENY od k

#: Dopuszczalny zakres ilorazu (stosunek wolumenu / k). Wolumen NIE mnozy sie
#: dokladnie przez k — to drugi wynik uruchomienia na realnych danych, ktory
#: obalil moje pierwsze zalozenie. Zmierzone ilorazy dla osmiu prawdziwych
#: splitow w naszym zbiorze:
#:
#:     SOXX 3:1   0.98      GOOGL 20:1  0.95      AAPL 4:1   1.11
#:     TSLA 5:1   1.10      TSLA 3:1    0.79      AMZN 20:1  0.65
#:     NVDA 4:1   0.58      NVDA 10:1   0.56
#:
#: Liczba akcji rosnie k-krotnie mechanicznie, ale liczba TRANSAKCJI potrafi
#: spasc — po splicie znika czesc zainteresowania, ktore go poprzedzalo. Stad
#: przedzial, nie punkt.
#:
#: Gorna granica 1.4 nie jest kosmetyczna: krach z prawdziwym wybuchem obrotu
#: (META -26% miala wolumen x4.08 przy cenie x1.36, czyli iloraz 2.7 wzgledem
#: jakiegokolwiek sensownego k) wypada poza nia. Prawdziwy split nigdy nie ma
#: wolumenu istotnie WIEKSZEGO niz krotnosc splitu — bo to ta sama liczba akcji,
#: tylko podzielona.
ILORAZ_WOLUMENU_MIN = 0.40
ILORAZ_WOLUMENU_MAX = 1.40
OKNO_WOLUMENU = 5            # dni po kazdej stronie do usrednienia obrotu


@dataclass(frozen=True)
class KandydatSplitu:
    """Podejrzany skok ceny wraz z dowodami za i przeciw."""

    symbol: str
    dzien: date
    stosunek_ceny: float          # close(d-1) / close(d) — dla splitu k:1 wynosi ~k
    wspolczynnik: float | None    # dopasowany prosty ulamek albo None
    stosunek_wolumenu: float      # wolumen po / wolumen przed
    przyjety: bool
    powod: str

    def __repr__(self) -> str:
        w = "PRZYJETY" if self.przyjety else "ODRZUCONY"
        return (f"{self.symbol} {self.dzien}: cena x{self.stosunek_ceny:.3f}, "
                f"wolumen x{self.stosunek_wolumenu:.2f} -> {w} ({self.powod})")


@dataclass
class RaportSplitow:
    kandydaci: list[KandydatSplitu] = field(default_factory=list)

    @property
    def przyjete(self) -> list[KandydatSplitu]:
        return [k for k in self.kandydaci if k.przyjety]

    @property
    def odrzucone(self) -> list[KandydatSplitu]:
        return [k for k in self.kandydaci if not k.przyjety]

    def summary(self) -> str:
        return (f"kandydatow {len(self.kandydaci)}, "
                f"przyjetych jako splity {len(self.przyjete)}, "
                f"odrzuconych jako ruch rynku {len(self.odrzucone)}")


def dopasuj_wspolczynnik(stosunek: float, stosunek_wolumenu: float | None = None) -> float | None:
    """Wspolczynnik splitu, na ktory wskazuja CENA I WOLUMEN JEDNOCZESNIE.

    Bez `stosunek_wolumenu` dziala jak zwykle dopasowanie do najblizszego ulamka
    — tryb uzywany w testach jednostkowych samego dopasowania.

    Z wolumenem wymaga ZGODNOSCI: ten sam k musi tlumaczyc obie wielkosci.
    To jest test o wiele mocniejszy niz kazdy z osobna, bo split narzuca
    zaleznosc miedzy cena a wolumenem, ktorej zdarzenie fundamentalne nie ma
    powodu spelniac.
    """
    najlepszy, najlepszy_blad = None, float("inf")
    for w in DOPUSZCZALNE_WSPOLCZYNNIKI:
        for kandydat in (w, 1.0 / w):
            blad_ceny = abs(stosunek - kandydat) / kandydat
            if blad_ceny > TOLERANCJA:
                continue
            ocena = blad_ceny
            if stosunek_wolumenu is not None:
                iloraz = stosunek_wolumenu / kandydat
                if not (ILORAZ_WOLUMENU_MIN <= iloraz <= ILORAZ_WOLUMENU_MAX):
                    continue
                # Gdy DWA wspolczynniki mieszcza sie w tolerancji ceny,
                # rozstrzyga wolumen. TSLA 2020-08-31 (cena x4.441) pasuje
                # i do 4, i do 5 — bo spolka urosla tego dnia o 12.6%. Sama
                # cena wskazywalaby 4 (blad 11.0% wobec 11.2%), a wolumen
                # x5.49 nie zostawia watpliwosci: iloraz 1.10 przy k=5 wobec
                # 1.37 przy k=4.
                ocena = blad_ceny + abs(iloraz - 1.0)
            if ocena < najlepszy_blad:
                najlepszy, najlepszy_blad = kandydat, ocena
    return najlepszy


def wykryj_splity(
    dni: list[date],
    close: np.ndarray,
    volume: np.ndarray,
    symbol: str = "",
) -> RaportSplitow:
    """Kandydaci na split w dziennym szeregu jednej spolki.

    Wejscie musi byc posortowane rosnaco po dacie i pozbawione luk wewnatrz dnia
    (jeden wiersz = jeden dzien sesyjny).
    """
    rep = RaportSplitow()
    n = len(dni)
    if n < 2 * OKNO_WOLUMENU + 2:
        return rep

    close = np.asarray(close, dtype=float)
    volume = np.asarray(volume, dtype=float)

    for i in range(1, n):
        if close[i] <= 0 or close[i - 1] <= 0:
            continue
        stosunek = close[i - 1] / close[i]
        if abs(np.log(stosunek)) < PROG_KANDYDATA:
            continue

        # Wolumen: srednia z okna przed i po. Przy splicie k:1 liczba akcji
        # w obrocie rosnie okolo k-krotnie — czego krach cenowy nie robi.
        a = max(0, i - OKNO_WOLUMENU)
        b = min(n, i + OKNO_WOLUMENU)
        przed = float(np.mean(volume[a:i])) if i > a else 0.0
        po = float(np.mean(volume[i:b])) if b > i else 0.0
        stos_wol = (po / przed) if przed > 0 else 0.0

        w = dopasuj_wspolczynnik(stosunek, stos_wol)

        if w is None:
            sam_cena = dopasuj_wspolczynnik(stosunek)
            if sam_cena is None:
                powod = f"stosunek ceny {stosunek:.3f} nie odpowiada zadnemu splitowi"
            else:
                powod = (f"cena wskazuje na {sam_cena:.0f}, ale wolumen x{stos_wol:.2f} "
                         f"tego nie potwierdza — to ruch rynku, nie split")
            przyjety = False
        else:
            powod = f"cena i wolumen zgodnie wskazuja split {w:.0f}:1"
            przyjety = True

        rep.kandydaci.append(KandydatSplitu(
            symbol=symbol, dzien=dni[i], stosunek_ceny=stosunek,
            wspolczynnik=w, stosunek_wolumenu=stos_wol,
            przyjety=przyjety, powod=powod,
        ))
    return rep


def wspolczynniki_korekty(dni: list[date], rep: RaportSplitow) -> np.ndarray:
    """Mnoznik korekty ceny dla kazdego dnia — historia sprzed splitu w dol.

    Analogia do `roll.cumulative_offsets`, ale multiplikatywna: najnowszy okres
    ma mnoznik 1.0, a kazdy wczesniejszy jest dzielony przez iloczyn wszystkich
    pozniejszych splitow.

        px_skorygowana = px_surowa / mnoznik
    """
    mnozniki = np.ones(len(dni), dtype=float)
    for k in rep.przyjete:
        if k.wspolczynnik is None:
            continue
        maska = np.array([d < k.dzien for d in dni])
        mnozniki[maska] *= k.wspolczynnik
    return mnozniki


def skoryguj_ceny(
    dni: list[date],
    close: np.ndarray,
    volume: np.ndarray,
    symbol: str = "",
) -> tuple[np.ndarray, np.ndarray, RaportSplitow]:
    """Ceny i wolumen skorygowane o splity. Zwraca takze raport do przejrzenia.

    Wolumen korygujemy w DRUGA STRONE niz cene: po splicie k:1 akcji jest
    k razy wiecej, wiec historyczny wolumen mnozymy przez k, zeby byl
    porownywalny z dzisiejszym.
    """
    rep = wykryj_splity(dni, close, volume, symbol=symbol)
    m = wspolczynniki_korekty(dni, rep)
    return np.asarray(close, dtype=float) / m, np.asarray(volume, dtype=float) * m, rep


def scal_tickery(symbol: str) -> list[str]:
    """Wszystkie nazwy, pod ktorymi spolka handlowala sie w naszym zakresie.

    Uzywane przy wczytywaniu: szereg sklejamy w jeden pod nazwa AKTUALNA, bo to
    ona jest kluczem w tabeli wag indeksu.

    UWAGA: sama lista nazw NIE WYSTARCZA do sklejenia — patrz `nalezy_do_szeregu`.
    """
    poprzedni = POPRZEDNIE_TICKERY.get(symbol)
    return [poprzedni[0], symbol] if poprzedni else [symbol]


def nalezy_do_szeregu(symbol_docelowy: str, symbol_rekordu: str, dzien: date) -> bool:
    """Czy rekord `symbol_rekordu` z dnia `dzien` nalezy do szeregu spolki.

    TICKER JEST NAZWA, NIE TOZSAMOSCIA — i gielda go PRZETWARZA W OBIE STRONY.
    Zmierzone na naszych danych, nie zalozone:

    (1) Po tym, jak Meta porzucila "FB" w czerwcu 2022, symbol zostal z czasem
        przypisany innej spolce: zapytanie o FB zwraca 84 tys. rekordow za 2022
        (do 8 czerwca wlacznie), ZERO za lata 2023-2024 i ponownie po kilkaset
        za lata 2025-2026.

    (2) Powazniejsze i mniej oczywiste: symbol "META" JUZ ISTNIAL, zanim przejela
        go Meta Platforms. W surowych danych jest **38 920 rekordow META
        z okresu 2021-06-30 do 2022-01-28, o cenach 11.73-17.17 USD** — podczas
        gdy Facebook handlowal sie wtedy po 300-380 USD. Wszystkie 147 dni tych
        notowan pokrywa sie z dniami, w ktorych mamy juz FB.

    Sklejenie po samej nazwie wstawiloby wiec akcje za 15 USD w srodek historii
    spolki notowanej po 340 USD, na 147 dniach. Blad nie rzucilby wyjatku —
    wyprodukowalby dzienne zwroty rzedu +/-95% i zatrulby sume wazona skladnikow,
    czyli arytmetyczne serce karty H013.

    Odciecie po dacie jest obustronne wlasnie dlatego, ze zanieczyszczenie idzie
    z obu stron: stara nazwa po zmianie i nowa nazwa przed zmiana.

    Stad odciecie po dacie, obustronne:
      * poprzednik liczy sie WYLACZNIE przed data zmiany,
      * nazwa aktualna WYLACZNIE od daty zmiany.
    """
    poprzedni = POPRZEDNIE_TICKERY.get(symbol_docelowy)
    if poprzedni is None:
        return symbol_rekordu == symbol_docelowy

    stary, kiedy = poprzedni
    if symbol_rekordu == stary:
        return dzien < kiedy
    if symbol_rekordu == symbol_docelowy:
        return dzien >= kiedy
    return False


def data_zmiany_tickera(symbol: str) -> date | None:
    poprzedni = POPRZEDNIE_TICKERY.get(symbol)
    return poprzedni[1] if poprzedni else None


# --------------------------------------------------------------------------
# Sesja gieldy kasowej — INNA niz sesja CME
# --------------------------------------------------------------------------

#: Granice segmentow dla akcji notowanych na XNAS, w czasie ET.
#: Uwaga: `engine.sessions` opisuje dobe CME, ktora zaczyna sie o 18:00 ET dnia
#: POPRZEDNIEGO. Dla akcji dzien sesyjny to zwykla data kalendarzowa w ET —
#: uzycie tamtej funkcji przesuneloby kazda sesje po 18:00 o jeden dzien.
GIELDA_PREMARKET = (4, 0)
GIELDA_OPEN = (9, 30)
GIELDA_CLOSE = (16, 0)
GIELDA_AFTERHOURS_KONIEC = (20, 0)


def segment_akcji(et_hour: int, et_minute: int) -> str:
    """Segment doby dla akcji: premarket / rth / afterhours / zamkniete."""
    minuty = et_hour * 60 + et_minute
    if minuty < GIELDA_PREMARKET[0] * 60:
        return "zamkniete"
    if minuty < GIELDA_OPEN[0] * 60 + GIELDA_OPEN[1]:
        return "premarket"
    if minuty < GIELDA_CLOSE[0] * 60:
        return "rth"
    if minuty < GIELDA_AFTERHOURS_KONIEC[0] * 60:
        return "afterhours"
    return "zamkniete"
