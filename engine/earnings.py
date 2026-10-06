"""Kalendarz publikacji wynikow z SEC EDGAR — PLAN.pdf rozdz. 4.5, karta H013.

DLACZEGO ZRODLEM JEST EDGAR, A NIE DETEKTOR REAKCJI RYNKOWEJ.

Kusi, zeby daty wynikow wykryc z samych danych: duzy ruch ceny plus skok wolumenu
w oknie after-hours to przeciez dokladnie to, co robi publikacja wynikow. Kod
bylby krotszy i nie wymagalby sieci.

**Byloby to skazenie proby selekcja (selection bias) i uniewaznialoby cala karte.**
H013 bada, jak indeks reaguje na wyniki skladnika. Gdyby zdarzenia byly wybierane
po WIELKOSCI tej wlasnie reakcji, do proby trafialyby tylko przypadki o duzej
reakcji — a to jest badana zmienna zalezna. Karta pokazalaby wtedy silny efekt
niezaleznie od tego, czy mechanizm istnieje, bo prog detektora sam by go wytworzyl.

Stad podzial rol, obowiazujacy bezwzglednie:

    EDGAR    = zrodlo etykiet. Definiuje probe. Backtest liczy sie na WSZYSTKICH
               publikacjach, takze tych o zerowej reakcji.
    DETEKTOR = wylacznie kontrola. Liczy precision i recall wzgledem kalendarza,
               wskazuje rozbieznosci do przejrzenia. NIGDY nie dodaje zdarzenia
               do proby ani zadnego z niej nie usuwa.

CO DOKLADNIE BIERZEMY. Formularz 8-K z pozycja **2.02 "Results of Operations and
Financial Condition"**. To jest raport biezacy, ktory spolka gieldowa MUSI zlozyc,
publikujac wyniki — obowiazek ustawowy, nie praktyka rynkowa. Nie uzywamy 10-Q
ani 10-K: te skladane sa czesto kilka dni PO komunikacie prasowym, wiec ich data
nie jest data reakcji rynku.

STREFA CZASOWA — TU BYLA PULAPKA I NIE JEST ONA HIPOTETYCZNA.

Pole `acceptanceDateTime` z API `submissions` konczy sie litera Z, wiec wyglada
na UTC. **Dla czesci spolek nim nie jest.** Zmierzone na naszej probie:

    AAPL  submissions: 2026-04-30T20:30:41Z   naglowek zrodlowy: 20260430163041
          -> przeliczone poprawnie (16:30:41 ET + 4h = 20:30:41 UTC)

    MSFT  submissions: 2026-07-29T16:04:53Z   naglowek zrodlowy: 20260729160453
          -> NIE przeliczone: czas ET dostal doklejone "Z"

Zaufanie temu polu przesunelo by wszystkie publikacje MSFT o cztery godziny
wstecz — z 16:04 ET (po zamknieciu) na 12:04 ET (srodek sesji). Karta H013
straciłaby wtedy 29 zdarzen jako "srodsesyjne", a gdyby ich nie odrzucila,
liczylaby rezyduum z okna, w ktorym zadna publikacja jeszcze nie nastapila.
Blad byly cichy: zadnego wyjatku, zadnej brakujacej wartosci.

Wykryte przez niezgodnosc z DST. Stemple AAPL przesuwaja sie 20:30Z latem /
21:30Z zima, czyli trzymaja stala godzinę scienna 16:30 ET — to sygnatura
prawdziwego UTC. Stemple MSFT stoja na 16:0xZ przez caly rok, wiec godzina ET
"przesuwalaby sie" wraz ze zmiana czasu, co dla publikacji wynikow nie ma sensu.
Potwierdzone niezaleznie danymi rynkowymi: 29.01.2020 MSFT nie drgnal o 12:03 ET
(+0.16% w oknie 11:56-12:20), a ruszyl o 16:00-16:20 (+1.98%).

DLATEGO ZNACZNIK BIERZEMY ZE STRONY INDEKSU ZLOZENIA, nie z API `submissions`.
Pole "Accepted" na `...-index.htm` jest **zawsze czasem wschodnim** i zgadza sie
co do sekundy z naglowkiem ACCEPTANCE-DATETIME pelnego zlozenia — sprawdzone dla
obu spolek. Kosztuje to jedno zapytanie na publikacje (strona ma ~9 KB), i jest
to cena, ktora warto zaplacic za etykiety czasowe, na ktorych stoi cala karta.

API `submissions` zostaje zrodlem tego, KTORE zlozenia istnieja; nie jest
zrodlem tego, KIEDY zostaly przyjete.

BMO / AMC / SRODSESYJNE. Klasyfikacja wzgledem **zaobserwowanych granic sesji RTH
tego konkretnego dnia**, nie wzgledem stalych 09:30-16:00. Powod jest praktyczny:
dni skrocone (wigilia, dzien po Swiecie Dziekczynienia) koncza sie o 13:00 ET,
a publikacja o 13:30 jest wtedy AMC, nie srodsesyjna. Granice bierzemy z danych,
wiec swieta, dni skrocone i DST obsluguja sie same, bez tablicy wyjatkow.

SESJA REAKCJI to nie to samo co data publikacji:

    BMO         -> reakcja tego samego dnia (publikacja przed otwarciem)
    AMC         -> reakcja NASTEPNEJ sesji
    poza sesja  -> (weekend, swieto) reakcja najblizszej sesji
    srodsesyjne -> oznaczone i WYKLUCZONE z proby podstawowej

Wykluczenie srodsesyjnych nie jest wygoda. Karta H013 mierzy rezyduum z okna
after-hours wzgledem otwarcia RTH; publikacja w srodku sesji nie ma takiego okna
i pomiar bylby dla niej czyms innym niz dla reszty proby.

CZEGO TEN MODUL NIE ROZSTRZYGA. Komunikat prasowy i konferencja wynikowa to dwa
rozne zdarzenia, zwykle w odstepie okolo godziny, i EDGAR datuje tylko pierwsze.
Reakcja na konferencje potrafi odwrocic reakcje na sam komunikat. Kalendarz tego
nie rozdziela i **nie udaje, ze rozdziela** — to znane ograniczenie proby.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

#: Symbol -> CIK, rozwiazane z oficjalnego `www.sec.gov/files/company_tickers.json`
#: (pobrane 2026-08-02), a nie wpisane z pamieci. AVGO wystepuje pod CIK spolki
#: Broadcom Inc. (1730168) utworzonej przy redomicylacji w 2018 — obejmuje caly
#: nasz zakres 2019-2026; starsze filingi Broadcom Ltd sa pod innym CIK i nie sa
#: nam potrzebne.
CIK: dict[str, int] = {
    "AAPL": 320193,
    "MSFT": 789019,
    "NVDA": 1045810,
    "AMZN": 1018724,
    "GOOGL": 1652044,
    "META": 1326801,
    "AVGO": 1730168,
    "TSLA": 1318605,
}

POZYCJA_WYNIKOW = "2.02"
FORMULARZ = "8-K"

BMO, AMC, SRODSESYJNE, POZA_SESJA = "BMO", "AMC", "SRODSESYJNE", "POZA_SESJA"


@dataclass(frozen=True)
class Publikacja:
    """Jedno zlozenie 8-K item 2.02 wraz z przypisana sesja reakcji."""

    symbol: str
    cik: int
    accession: str
    data_zlozenia: date          # filingDate wg EDGAR
    okres: str                   # reportDate — okres, ktorego dotycza wyniki
    #: Znacznik z pola `acceptanceDateTime` API `submissions`, TAK JAK PRZYSZEDL.
    #: Trzymany wylacznie po to, zeby raport mogl pokazac, dla ktorych spolek
    #: jest niezgodny z prawda. Nigdy nie sluzy do klasyfikacji.
    znacznik_json: str = ""
    #: Autorytatywny czas przyjecia w ET, ze strony indeksu zlozenia.
    akceptacja_et: datetime | None = None
    klasa: str = ""              # BMO / AMC / SRODSESYJNE / POZA_SESJA
    sesja_reakcji: date | None = None

    @property
    def json_zgodny(self) -> bool | None:
        """Czy `acceptanceDateTime` z API dalo sie czytac jako prawdziwy UTC.

        None, gdy nie mamy jeszcze autorytatywnego znacznika. Sluzy raportowi
        jakosci danych, nie logice — patrz docstring modulu.
        """
        if self.akceptacja_et is None or not self.znacznik_json:
            return None
        z_json = datetime.fromisoformat(self.znacznik_json.replace("Z", "+00:00"))
        return z_json.astimezone(ET).replace(tzinfo=None) == \
            self.akceptacja_et.replace(tzinfo=None)


def parsuj_akceptacje(html: str) -> datetime | None:
    """Czas przyjecia (ET) ze strony `...-index.htm` zlozenia.

    Funkcja czysta — przyjmuje tekst strony, nie adres. Daje sie przetestowac
    na fragmencie HTML bez sieci.

    Zwraca `None`, gdy pola nie ma. Jawnie, bo cicha wartosc domyslna oznaczalaby
    zdarzenie z bledna godzina, a nie brakujace — a to sa dwie rozne rzeczy.
    """
    m = re.search(
        r"Accepted\s*</div>\s*<div[^>]*>\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})",
        html,
    )
    if m is None:
        return None
    return datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}").replace(tzinfo=ET)


def url_indeksu(cik: int, accession: str) -> str:
    """Adres strony indeksu zlozenia — jedyne zrodlo wiarygodnego czasu ET."""
    return (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
            f"{accession.replace('-', '')}/{accession}-index.htm")


def klasyfikuj(
    akceptacja_et: datetime,
    otwarcie: datetime | None,
    zamkniecie: datetime | None,
) -> str:
    """BMO / AMC / SRODSESYJNE / POZA_SESJA wzgledem granic sesji TEGO dnia.

    `otwarcie` i `zamkniecie` to zaobserwowane w danych znaczniki pierwszego
    i ostatniego bara RTH. `None` oznacza, ze dzien nie byl sesja (weekend,
    swieto) — wtedy klasa jest POZA_SESJA niezaleznie od godziny.
    """
    if otwarcie is None or zamkniecie is None:
        return POZA_SESJA
    if akceptacja_et < otwarcie:
        return BMO
    if akceptacja_et > zamkniecie:
        return AMC
    return SRODSESYJNE


def sesja_reakcji(
    dzien: date, klasa: str, sesje: frozenset[date] | set[date],
) -> date | None:
    """Sesja, w ktorej rynek moze zareagowac na publikacje z dnia `dzien`.

    BMO reaguje tego samego dnia; wszystko inne — najblizszej kolejnej sesji.
    Zwraca None, gdy kolejnej sesji nie ma w naszych danych (koniec probki):
    jawnie, zeby wywolujacy musial takie zdarzenie odrzucic, zamiast dostac
    ciche przypisanie do zlej daty.
    """
    if klasa == SRODSESYJNE:
        return dzien if dzien in sesje else None
    if klasa == BMO:
        return dzien if dzien in sesje else None
    kandydat = dzien + timedelta(days=1)
    for _ in range(10):          # najdluzsza realna przerwa to weekend + swieta
        if kandydat in sesje:
            return kandydat
        kandydat += timedelta(days=1)
    return None


def parsuj_submissions(payload: dict, symbol: str) -> list[Publikacja]:
    """Wyluskuje 8-K item 2.02 z jednego bloku `filings` API `submissions`.

    Funkcja jest czysta — przyjmuje slownik, nie adres URL. Dzieki temu daje sie
    przetestowac na recznie zbudowanym rekordzie, bez sieci i bez udawania,
    ze odpowiedz EDGAR jest danymi rynkowymi.
    """
    if "form" not in payload:
        return []
    n = len(payload["form"])
    wynik: list[Publikacja] = []
    for i in range(n):
        if payload["form"][i] != FORMULARZ:
            continue
        pozycje = payload.get("items", [""] * n)[i] or ""
        # rozbicie po przecinku, a nie test podciagu: "12.02" zawiera "2.02"
        if POZYCJA_WYNIKOW not in [c.strip() for c in pozycje.split(",")]:
            continue
        wynik.append(
            Publikacja(
                symbol=symbol,
                cik=CIK[symbol],
                accession=payload["accessionNumber"][i],
                data_zlozenia=date.fromisoformat(payload["filingDate"][i]),
                okres=payload.get("reportDate", [""] * n)[i] or "",
                znacznik_json=payload["acceptanceDateTime"][i],
            )
        )
    return wynik
