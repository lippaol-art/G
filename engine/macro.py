"""Kalendarz publikacji makro — PLAN.pdf rozdz. 4.5, karta H003.

ZRODLA SA URZEDOWE I DARMOWE. Zadnego wykrywania zdarzen po ruchu ceny —
uzasadnienie identyczne jak w `engine/earnings.py`: wybieranie zdarzen po
wielkosci badanej reakcji skazilo by probe selekcja.

    CPI, PPI, Employment Situation  ->  harmonogram BLS (bls.gov/schedule/YYYY)
    komunikat FOMC                  ->  kalendarz Fed + strona samego komunikatu

GODZINA POCHODZI Z DOKUMENTU, NIE Z KONWENCJI. Harmonogram BLS podaje godzine
w osobnej kolumnie (08:30 AM we wszystkich 8 latach naszego zakresu). Strona
komunikatu FOMC zawiera zdanie "For release at 2:00 p.m. EDT". Bierzemy je
stamtad zamiast wpisywac 14:00 z pamieci — dokladnie ta ostroznosc wykryla
w kalendarzu wynikow, ze pole `acceptanceDateTime` bywa czasem lokalnym
z sufiksem Z.

STREFA CZASOWA przez `America/New_York`, nigdy przez reczne przesuniecie UTC.
Publikacje sa o stalej godzinie SCIENNEJ, wiec offset zmienia sie z DST i recznie
wpisany byl by bledny przez pol roku.

DWA ETAPY POSIEDZENIA FOMC. Komunikat wychodzi o 14:00, konferencja prasowa
zaczyna sie okolo 14:30. Okno 5-60 minut po komunikacie obejmuje wiec w calosci
konferencje i mieszaloby dwa rozne zdarzenia informacyjne. Kalendarz zapisuje
oba znaczniki (`ma_drugi_etap`, `drugi_etap_et`), a karta H003 mierzy wynik
**przed konferencja**. Decyzja zapadla przed policzeniem czegokolwiek.

POSIEDZENIA PLANOWE A DZIALANIA NADZWYCZAJNE. Fed publikuje komunikaty takze
poza harmonogramem. W naszym zakresie sa to miedzy innymi 11.10.2019 oraz
awaryjne ciecia 03.03, 15.03, 23.03 i 31.03.2020. **Do proby podstawowej H003
wchodza wylacznie posiedzenia PLANOWE**, i jest to wykluczenie z mechanizmu,
nie z danych: karta bada rynek, ktory kompresuje sie przed ZNANYM terminem
publikacji. Dzialanie nadzwyczajne jest z definicji nieoczekiwane, wiec okna
rownowagi w sensie karty po prostu nie ma.

Uwaga na pulapke: **konferencja prasowa NIE odroznia posiedzen planowych od
nadzwyczajnych.** Marcowe ciecia awaryjne 2020 mialy konferencje. Rozroznienie
bierzemy z listy posiedzen na kalendarzu Fed, nie z obecnosci konferencji.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

CPI, PPI, NFP, FOMC = "CPI", "PPI", "NFP", "FOMC"

#: Nazwa publikacji w harmonogramie BLS -> nasz typ zdarzenia. Tylko te trzy;
#: pozostale pozycje harmonogramu (JOLTS, ECI, produktywnosc) nie sa w karcie.
NAZWY_BLS: dict[str, str] = {
    "Consumer Price Index": CPI,
    "Producer Price Index": PPI,
    "Employment Situation": NFP,
}

#: Ile minut po komunikacie FOMC zaczyna sie konferencja prasowa. Uzywane tylko
#: jako wartosc domyslna, gdy Fed nie poda godziny konferencji wprost.
OPOZNIENIE_KONFERENCJI = 30


@dataclass(frozen=True)
class Zdarzenie:
    """Jedna publikacja makro. Schemat wg ustalen audytu H003."""

    typ: str
    planowany_et: datetime            # znacznik z dokumentu, w czasie wschodnim
    data: date
    zrodlo: str
    sesja_reakcji: date | None = None
    ma_drugi_etap: bool = False
    drugi_etap_et: datetime | None = None
    okres: str = ""                   # miesiac referencyjny albo zakres posiedzenia
    uwagi: str = ""


def _miesiac(nazwa: str) -> int | None:
    m = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
         "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
         "december": 12}
    return m.get(nazwa.strip().lower()[:20])


def parsuj_harmonogram_bls(tekst_html: str, rok: int) -> list[Zdarzenie]:
    """Publikacje CPI/PPI/NFP z rocznego harmonogramu BLS.

    Funkcja czysta — przyjmuje tekst strony, nie adres. Wiersz harmonogramu ma
    postac: data | godzina | nazwa publikacji z miesiacem referencyjnym.
    """
    import html as _html

    wynik: list[Zdarzenie] = []
    for wiersz in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", tekst_html):
        kom = [re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
               for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", wiersz)]
        kom = [c for c in kom if c]
        if len(kom) < 3:
            continue
        m_data = re.search(r"([A-Z][a-z]+day),\s*([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})", kom[0])
        m_godz = re.search(r"(\d{1,2}):(\d{2})\s*([AP]M)", kom[1])
        if not (m_data and m_godz):
            continue
        # Dopasowanie musi byc PELNE i wymagac miesiecznego okresu referencyjnego.
        # `startswith` bylo za luzne i wpuszczalo "Employment Situation OF VETERANS
        # for Annual 2023" — publikacje roczna o 10:00, ktora nie ma nic wspolnego
        # z miesiecznym raportem o zatrudnieniu. Ta sama klasa bledu co pozycja
        # "12.02" zawierajaca "2.02" w `engine/earnings.py`.
        typ = next(
            (t for nazwa, t in NAZWY_BLS.items()
             if re.fullmatch(rf"{re.escape(nazwa)} for [A-Z][a-z]+ \d{{4}}", kom[2])),
            None,
        )
        if typ is None:
            continue
        mies = _miesiac(m_data.group(2))
        if mies is None or int(m_data.group(4)) != rok:
            continue
        g, mi = int(m_godz.group(1)), int(m_godz.group(2))
        if m_godz.group(3) == "PM" and g != 12:
            g += 12
        if m_godz.group(3) == "AM" and g == 12:
            g = 0
        d = date(rok, mies, int(m_data.group(3)))
        okres = kom[2].split(" for ", 1)[1] if " for " in kom[2] else ""
        wynik.append(
            Zdarzenie(typ=typ, planowany_et=datetime(d.year, d.month, d.day, g, mi, tzinfo=ET),
                      data=d, zrodlo="BLS", okres=okres)
        )
    return wynik


def parsuj_godzine_komunikatu(tekst_html: str) -> time | None:
    """Godzina z frazy "For release at 2:00 p.m." na stronie komunikatu FOMC.

    Zwraca None, gdy frazy nie ma — jawnie, zeby wywolujacy odrzucil zdarzenie
    zamiast dostac po cichu wartosc domyslna. Godzina jest tu podstawa calego
    pomiaru karty, wiec zgadywanie jej byloby najgorszym mozliwym skrotem.
    """
    import html as _html

    t = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", tekst_html)))
    m = re.search(r"For release at\s+(\d{1,2}):(\d{2})\s*([ap])\.?\s*m", t, re.I)
    if not m:
        return None
    g, mi = int(m.group(1)), int(m.group(2))
    if m.group(3).lower() == "p" and g != 12:
        g += 12
    if m.group(3).lower() == "a" and g == 12:
        g = 0
    return time(g, mi)


#: Etykiety, ktorymi Fed sam oznacza wpisy NIEBEDACE planowym posiedzeniem.
#: Bierzemy klasyfikacje ze zrodla zamiast ja wnioskowac — Fed pisze wprost
#: "March 2 (unscheduled) Meeting - 2020" i "March 17-18 (cancelled) Meeting".
ETYKIETY_NIEPLANOWE = ("unscheduled", "cancelled", "notation vote")


def parsuj_posiedzenia_fomc(tekst_html: str) -> set[date]:
    """Daty komunikatow z PLANOWYCH posiedzen FOMC.

    Data brana jest **z odnosnika do komunikatu** (`monetaryYYYYMMDDa.htm`), a nie
    z parsowania nazw miesiecy — odnosnik zawiera pelna date i nie ma w nim
    przypadkow brzegowych typu posiedzenia na przelomie miesiecy.

    Obsluguje dwa uklady stron Fedu, bo tak sa zbudowane:

      historyczny (2019-2020)  bloki <h5>...Meeting - YYYY</h5>, z jawnymi
                               etykietami (unscheduled) / (cancelled) /
                               (notation vote) w naglowku
      biezacy (2021+)          wiersze <div class="row fomc-meeting">, na ktorych
                               widnieja wylacznie posiedzenia planowe

    PULAPKA, KTORA TO OMIJA: obecnosc konferencji prasowej **nie** odroznia
    posiedzen planowych od nadzwyczajnych. Awaryjne ciecia z marca 2020 mialy
    konferencje. Klasyfikacja po konferencji dalaby zle wyniki i nie rzucilaby
    zadnego bledu.
    """
    wynik: set[date] = set()

    # uklad historyczny — segmenty rozpoczynane naglowkiem h5
    czesci = re.split(r'(?is)(<h5[^>]*class="panel-heading[^"]*"[^>]*>.*?</h5>)', tekst_html)
    for i in range(1, len(czesci), 2):
        naglowek = re.sub(r"<[^>]+>", " ", czesci[i]).lower()
        tresc = czesci[i + 1] if i + 1 < len(czesci) else ""
        if "meeting" not in naglowek:
            continue
        if any(e in naglowek for e in ETYKIETY_NIEPLANOWE):
            continue
        for d in re.findall(r"monetary(\d{8})a\.htm", tresc):
            wynik.add(datetime.strptime(d, "%Y%m%d").date())

    # Uklad biezacy. Kotwica to `fomc-meeting__month` — jedna na posiedzenie.
    # Kontener `<div class="row fomc-meeting" ">` NIE nadaje sie na kotwice: HTML
    # jest tam zle sformowany i czesc wierszy sie nie rozdziela, przez co jeden
    # segment obejmowal dwa posiedzenia, a w oknie znajdowaly sie odnosniki
    # do wydarzen niebedacych posiedzeniami (np. sympozjum w Jackson Hole).
    for seg in re.split(r"(?is)fomc-meeting__month", tekst_html)[1:]:
        # Etykiety nieplanowe wystepuja takze w ukladzie biezacym: wiersz
        # "August 22 (notation vote)" ma te sama strukture co posiedzenie
        # i bez tego filtra wchodzil do proby jako posiedzenie sierpniowe.
        naglowek = re.sub(r"<[^>]+>", " ", seg[:400]).lower()
        if any(e in naglowek for e in ETYKIETY_NIEPLANOWE):
            continue
        m = re.search(r"monetary(\d{8})a\.htm", seg)
        if m:
            wynik.add(datetime.strptime(m.group(1), "%Y%m%d").date())

    return wynik


def sesja_reakcji(dzien: date, sesje: frozenset[date] | set[date]) -> date | None:
    """Sesja, w ktorej rynek reaguje na publikacje z dnia `dzien`.

    Publikacje makro wypadaja przed otwarciem (08:30) albo w trakcie sesji
    (14:00), wiec reakcja jest ZAWSZE tego samego dnia — o ile jest to dzien
    sesyjny. Publikacja w dniu bez sesji to anomalia i zwracamy None, zeby
    wywolujacy musial ja obsluzyc jawnie.
    """
    return dzien if dzien in sesje else None


def okno_rownowagi(znacznik: datetime, minut: int = 60) -> tuple[datetime, datetime]:
    """Okno przedpublikacyjne — zakres rownowagi R z karty H003."""
    return znacznik - timedelta(minutes=minut), znacznik
