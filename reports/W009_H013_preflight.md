# W009 — pre-flight H013 (rezydualny repricing po wynikach megacapow)

*Wygenerowane przez `research/W009_H013_preflight.py`, 2026-08-02. 185 sesji zdarzen z 1690 sesji z policzonym rezyduum.*

**Status licznika prob: 0 zuzytych.** Zadnych stopow, progow ani optymalizacji.

Szesc przewidywan mechanizmu, zadeklarowanych z gory. Raportowane sa
**wszystkie**, takze niekorzystne.

## 0. Konstrukcja

| Element | Wybor | Uzasadnienie |
|---|---|---|
| Okno pomiaru | zamkniecie RTH → ostatnie notowanie przed 09:30 | obejmuje AMC i BMO jednym oknem; opisuje stan w momencie wejscia (W008) |
| Wrazliwosci | estymowane na zwrotach **nocnych** | stosowanie wspolczynnikow z sesji dziennej zakladaloby identyczna transmisje w obu rezimach |
| Okno regresji | 250 sesji, konczace sie **przed** sesja zdarzenia | zakaz lookaheadu |
| Kontrole | ES i SOXX **w tym samym rownaniu** | odejmowanie sekwencyjne kazaloby ES pochlonac czesc wplywu skladnikow |
| Wejscie | otwarcie bara 09:31 sesji reakcji | zasada 2 silnika |
| Wyjscie | koniec segmentu `rth_open` (10:30) | bez stopa — to nie backtest |

## 1. Przewidywanie 1 — rezyduum istnieje i ma sensowna skale

| Wielkosc | Sesje zdarzen | Pozostale sesje |
|---|---|---|
| sd ruchu nocnego NQ | 0.858% | 0.753% |
| sd rezyduum | 0.153% | 0.115% |
| redukcja szumu przez model | **82%** | 85% |

Rezyduum istnieje i jest wyraznie wezsze niz sam ruch nocny — model tlumaczy
82% zmiennosci w sesje zdarzen. Warunek 1 z sekcji 2 karty **spelniony**,
co bylo spodziewane; karta nigdy na nim nie stala.

## 2. Przewidywanie 2 — rezyduum ma strukture (NA TYM KARTA STOI)

Jesli kontrakt nie doszacowal ruchu skladnikow, roznica powinna domykac sie
po otwarciu. Znak: **dodatnie rezyduum = NQ za wysoko wzgledem skladnikow**,
wiec mechanizm przewiduje **ujemny** zwrot po otwarciu.

| Miara | Wartosc |
|---|---|
| korelacja(rezyduum, zwrot 09:31→10:30) | **+0.0808** |
| korelacja(rezyduum, zwrot 09:31→koniec) | -0.0746 |
| sredni wynik fade'u (09:31→10:30) | -0.0363% |
| **t** | **-0.79** |
| sredni wynik fade'u (09:31→koniec) | +0.0559% |
| t | +0.69 |

## 3. Przewidywanie 3 — efekt rosnie z wielkoscia rezyduum

Jesli nie rosnie, mierzymy cos innego niz niedowycenienie. **Tak uplo H014.**

| Warunek | *f* wsrod zdarzen | N | Sredni wynik | t | pkt MNQ |
|---|---|---|---|---|---|
| wszystkie zdarzenia | 1.00 | 185 | -0.0363% | **-0.79** | -6.5 |
| gorne 2/3 | 0.66 | 123 | -0.0380% | **-0.64** | -6.8 |
| gorny tercyl | 0.34 | 62 | -0.0892% | **-1.17** | -16.0 |
| gorny decyl | 0.10 | 19 | -0.1705% | **-1.42** | -30.6 |

## 4. Przewidywanie 4 — symetria stron

Mechanizm arytmetyczny nie ma powodu dzialac tylko w jedna strone.
**Asymetria bez wyjasnienia zabila H005.**

| Strona rezyduum | N | Sredni wynik | t |
|---|---|---|---|
| dodatnie (NQ za wysoko) | 79 | +0.0314% | **+0.47** |
| ujemne (NQ za nisko) | 106 | -0.0868% | **-1.40** |

## 5. Przewidywanie 5 — stabilnosc roczna

Zaden rok nie moze dawac ponad 40% wyniku. **Tak uplo H005** (52% z jednego roku).

| Rok | N | Sredni wynik | t | Udzial w wyniku |
|---|---|---|---|---|
| 2019 | 4 | -0.2621% | -2.50 | +16% |
| 2020 | 24 | -0.1439% | -0.90 | +51% |
| 2021 | 27 | -0.1673% | -1.87 | +67% |
| 2022 | 30 | -0.2642% | -2.15 | +118% |
| 2023 | 31 | +0.0356% | +0.37 | -16% |
| 2024 | 28 | +0.1283% | +1.14 | -53% |
| 2025 | 26 | +0.1995% | +1.95 | -77% |
| 2026 | 15 | +0.0233% | +0.12 | -5% |

Lat dodatnich: **4 z 8**. Najwiekszy udzial pojedynczego roku: **+118%**.

## 6. Przewidywanie 6 — kontrola pozornosci

Czy skladniki cokolwiek wnosza? Porownanie z modelem bez nich i z sama luka NQ.
Jesli wyniki sa zblizone, karta redukuje sie do **B04** i schodzi do benchmarkow.

| Model rezyduum | Sredni wynik | t |
|---|---|---|
| **pelny (skladniki + ES + SOXX)** | -0.0363% | **-0.79** |
| tylko ES + SOXX (bez skladnikow) | +0.0377% | +0.83 |
| sama luka nocna NQ (odpowiednik B04) | +0.0295% | +0.65 |

## 7. Ekonomia — prog z sekcji 5 karty

| Wielkosc | Wartosc |
|---|---|
| Sredni wynik brutto na zdarzenie | -6.5 pkt MNQ |
| W USD (mnoznik 2.0) | -13.02 |
| Koszt round-turn | −2.20 USD |
| **Netto na zdarzenie** | **-15.22 USD** |
| Prog SR ≥ 0.8 z karty | +24.2 pkt |
| Prog DSR ≥ 0.95 z karty | +34.4 pkt |

## 8. Kontrola odpornosci — okno 16:00-17:00 z sekcji 6 karty

Raportowane, zeby bylo widac, ze wybor okna nie zostal zrobiony pod wynik.
Kryterium wyboru bylo pomiarowe i zadeklarowane przed liczeniem (W008).

| Okno | N | Sredni wynik | t |
|---|---|---|---|
| **przed otwarciem (glowne)** | 185 | -0.0363% | **-0.79** |
| 16:00-17:00 (sekcja 6 karty) | 185 | -0.0926% | -2.05 |

Oba okna daja ten sam ZNAK, a oryginalne okno z karty wypada dla karty
**gorzej** (t = -2.05 wobec -0.79). Wybor okna
nie jest wiec przyczyna negatywnego wyniku — przeciwnie, okno wybrane
kryterium pomiarowym jest dla karty **lagodniejsze** niz to, ktore karta
sama deklarowala.

## 9. Moc testu — czego ten pre-flight NIE wyklucza

| Wielkosc | Wartosc |
|---|---|
| sd wyniku na zdarzenie | 0.621% |
| 95% CI sredniego wyniku | [-0.1258%, +0.0532%] |
| Wymagany edge (SR ≥ 0.8) | +0.105% |
| N potrzebne przy mocy 80% | **274 zdarzen** |
| N dostepne | **185** |

**Uczciwie: przy tej probie nie da sie odrzucic edge'u dokladnie tej
wielkosci, ktorej karta potrzebuje** — gorny koniec przedzialu ufnosci
(+0.0532%) lezy blisko progu. Gdyby jedynym wynikiem byl brak
istotnosci, werdykt brzmialby "nierozstrzygniete", jak w W001.

**Ale to nie jest jedyny wynik.** Karta upada nie na braku istotnosci, tylko
na tym, ze **wlasne przewidywania jej mechanizmu sa lamane co do znaku**:
warunkowanie na wielkosci rezyduum pogarsza wynik, strony sa asymetryczne,
a znak efektu odwraca sie w polowie probki. Zadna z tych rzeczy nie jest
kwestia mocy testu — to sa sprzecznosci wewnetrzne.

**Ta sama lekcja co W004: kontrole z mechanizmu odrzucaja wczesniej
i pewniej niz kontrole statystyczne.**

## 10. Werdykt: **NO-GO**

| # | Przewidywanie | Wynik | Ocena |
|---|---|---|---|
| 1 | Rezyduum istnieje i ma skale | redukcja szumu 82%, sd 0.153% | **spelnione** |
| 2 | Rezyduum sie domyka | korelacja +0.0808 (10:30), -0.0746 (koniec); t = -0.79 | **zawiedzione** |
| 3 | Efekt rosnie z wielkoscia rezyduum | t: -0.79 → -1.42 w gornym decylu — **pogorszenie** | **zawiedzione** |
| 4 | Symetria stron | dodatnie t = +0.47, ujemne t = -1.40 — przeciwne znaki | **zawiedzione** |
| 5 | Stabilnosc roczna | 4/8 lat dodatnich, jeden rok +118% wyniku | **zawiedzione** |
| 6 | Skladniki cos wnosza | pelny model t = -0.79, sama luka NQ t = +0.65 | **zawiedzione** |

**Piec z szesciu przewidywan zawiedzionych. Jedyne spelnione to warunek 1,
o ktorym karta sama pisala, ze nigdy na nim nie stala** — sekcja 2 karty
mowi wprost: warunek 3 jest tym, na czym karta stoi lub upada.

### Co jest tu rozstrzygajace

Nie sam brak istotnosci — ten bylby kwestia mocy. Rozstrzygajace sa **trzy
sprzecznosci wewnetrzne**, kazda niezalezna od pozostalych:

1. **Warunkowanie dziala na opak.** Im wieksze rezyduum, tym gorszy wynik
   (-0.79 → -1.42). Gdyby mechanizm mowil prawde, byloby
   odwrotnie: wieksze niedowycenienie to wieksza okazja. Dokladnie tak upadlo
   H014 i ten punkt jest tam opisany jako rozstrzygajacy.

2. **Znak odwraca sie w polowie probki.** Lata 2019-2022 daja srednio
   ujemny wynik fade'u, lata 2023-2026 dodatni. To nie jest koncentracja
   (jak w H005), tylko **zmiana kierunku** — najmocniejszy dowod, ze stalego
   mechanizmu nie ma.

3. **Skladniki nie wnosza nic.** Model bez nich i sama luka nocna NQ daja
   wyniki tego samego rzedu, tyle ze z przeciwnym znakiem. Czlon Σsᵢrᵢ —
   caly powod istnienia tej karty — nie jest zrodlem zadnej informacji
   ponad to, co widac w samej luce.

### Konsekwencje

| Co | Decyzja |
|---|---|
| **H013** | **REJECTED (pre-flight)**, 0 z 8 prob zuzytych |
| **H016** | traci nosiciela — pozostaje w stanie oczekiwania (sekcja 7 karty) |
| Kalendarz EDGAR | zostaje w repo, jest poprawny i darmowy |
| `engine/ndx_sensitivity` | zostaje, model jest zwalidowany OOS (W007) |
| Dane K6 za $7.82 | wydane; kupione **przed** pre-flightem, bo bez nich pre-flight bylby niewykonalny |

Ostatni wiersz wart jest odnotowania bez owijania: to pierwszy raz w tym
projekcie, gdy pre-flight kosztowal pieniadze, a nie tylko czas. Kwota jest
mala, ale zasada z reguly R1 zadziala tak samo przy wiekszej — **zakup danych
nie jest inwestycja w karte, tylko w mozliwosc jej sprawdzenia.**

---

Odtworzenie: `python3 research/W009_H013_preflight.py`
