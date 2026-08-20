# W013 — pre-flight H003 (impuls wobec rownowagi przedpublikacyjnej)

*Wygenerowane przez `research/W013_H003_preflight.py`, 2026-08-02. 232 zdarzen w tescie glownym, 80 w warm-upie.*

**Status licznika prob: 0 zuzytych.**

Specyfikacja **zamrozona przed tym pomiarem** (commity `ae0f9f8` i `d03337c`,
karta `hypotheses/H003.md` sekcja 0). Ten skrypt jej nie zmienia i nie dobiera
zadnego progu.

## 0. Proba

| Typ | Test glowny | Warm-up | Razem |
|---|---|---|---|
| CPI | 65 | 20 | 85 |
| PPI | 65 | 20 | 85 |
| NFP | 65 | 20 | 85 |
| FOMC | 37 | 20 | 57 |

Warm-up to pierwsze **20** zdarzen kazdego typu — nie maja
wystarczajacej historii, zeby policzyc range bez lookaheadu. Sa raportowane,
nie usuwane.

## 1. Czy iloraz w ogole rozroznia zdarzenia

| Typ | mediana R (pkt) | mediana \|I\| (pkt) | mediana ilorazu | mediana ER impulsu |
|---|---|---|---|---|
| CPI | 46.0 | 77.5 | 1.68 | 0.69 |
| PPI | 40.5 | 34.5 | 0.63 | 0.55 |
| NFP | 40.8 | 51.2 | 1.19 | 0.50 |
| FOMC | 62.0 | 52.0 | 0.78 | 0.47 |

Kolumny R i ilorazu pokazuja, **dlaczego tercyle musza byc liczone wewnatrz
typu**: zakres rownowagi przed FOMC (13:00-14:00, plynnosc gruba) i przed
publikacja BLS (07:30-08:30, plynnosc cienka) to inne swiaty.

Efficiency ratio impulsu mowi, jaka czesc zakresu pierwszych pieciu minut jest
przemieszczeniem. Wartosc znaczaco ponizej 1 znaczy, ze impuls **zawraca juz
w oknie pomiaru** — i to jest powod, dla ktorego zmienna kierunkowa jest
przemieszczeniem, a nie zakresem ze znakiem.

## 2. TEST MECHANIZMU — czy relacja istnieje ponad roznicami skali

`y_std = α_typ + β · ranga(|I|/R) + ε`, odporny blad standardowy HC3.
Zwrot standaryzowany **wewnatrz typu**, efekty stale typu.

Rozstrzyga **β**. Dodatnie β znaczy, ze im wiekszy impuls wobec rownowagi,
tym lepszy wynik fade'u — czyli dokladnie to, co twierdzi karta.

| Wspolczynnik | Wartosc | t (HC3) |
|---|---|---|
| α CPI | +0.0932 | +0.44 |
| α PPI | +0.0910 | +0.43 |
| α NFP | +0.0815 | +0.45 |
| α FOMC | +0.0666 | +0.35 |
| **β ranga ilorazu** | **-0.1397** | **-0.60** |

## 3. Wynik per typ — obowiazkowy

Jesli jeden typ niesie caly efekt, **karta laczna nie przechodzi**.

| Typ | N | Gorny tercyl: N | Sredni wynik (pkt) | t | Wszystkie: sredni | t |
|---|---|---|---|---|---|---|
| CPI | 65 | 36 | -11.7 | -1.51 | -4.7 | -0.75 |
| PPI | 65 | 37 | +0.0 | +0.00 | +3.3 | +0.81 |
| NFP | 65 | 27 | +1.2 | +0.11 | +3.9 | +0.56 |
| FOMC | 37 | 11 | +5.3 | +0.26 | +15.5 | +1.95 |

## 4. Monotonicznosc w tercylach ilorazu

Mechanizm wymaga, zeby wynik **rosl** z ilorazem. Skok w jednym kubelku
oznacza trafienie w kubelek, nie w mechanizm — tak zginelo H005.

| Tercyl rangi | N | Sredni wynik (pkt) | t | y_std |
|---|---|---|---|---|
| dolny | 43 | -0.5 | -0.06 | -0.111 |
| srodkowy | 78 | +13.8 | +2.61 | +0.217 |
| gorny | 111 | -3.0 | -0.69 | -0.110 |

## 5. Ablacja rozstrzygajaca — iloraz przeciw samej wielkosci impulsu

**To jest test, ktory decyduje o istnieniu tej karty.** H014 zginelo na
warunkowaniu sama wielkoscia szoku. H003 twierdzi, ze wlasciwa zmienna jest
iloraz do rownowagi. Jesli sama wielkosc dziala tak samo, karta dziedziczy
werdykt H014.

| Zmienna warunkujaca | Gorny tercyl: N | Sredni wynik (pkt) | t |
|---|---|---|---|
| **iloraz \|I\|/R** (karta) | 111 | -3.0 | -0.69 |
| sama wielkosc \|I\| (odpowiednik H014) | 53 | +5.1 | +0.70 |

## 6. Stabilnosc roczna (gorny tercyl ilorazu)

| Rok | N | Suma (pkt) | Sredni wynik | t | Znak |
|---|---|---|---|---|---|
| 2021 | 20 | +10 | +0.5 | +0.07 | + |
| 2022 | 28 | -369 | -13.2 | -1.09 | − |
| 2023 | 20 | -126 | -6.3 | -0.70 | − |
| 2024 | 23 | +40 | +1.8 | +0.26 | + |
| 2025 | 16 | +113 | +7.1 | +0.78 | + |
| 2026 | 4 | +2 | +0.5 | +0.02 | + |

## 7. TEST EKONOMICZNY

Koszt i poslizg **wlasciwy dla segmentu wejscia**: publikacje BLS wchodza
o 08:35 w premarkecie, FOMC o 14:05 po poludniu.

| Wielkosc | Gorny tercyl | Wszystkie zdarzenia |
|---|---|---|
| N | 111 | 232 |
| Brutto na zdarzenie | -3.0 pkt | +3.2 pkt |
| Poslizg + prowizja | −2.1 pkt | −2.0 pkt |
| **Netto na zdarzenie** | **-5.0 pkt (-10.03 USD)** | +1.1 pkt (+2.26 USD) |
| t netto | -1.17 | +0.36 |

Faktyczny ulamek okazji *f* = **0.48** wsrod zdarzen, czyli
**15 okazji rocznie**.

## 8. Moc testu — zadeklarowana w karcie przed pomiarem

| Wielkosc | Wartosc |
|---|---|
| sd wyniku na zdarzenie (gorny tercyl) | 45.3 pkt |
| 95% CI sredniego wyniku | [-11.4, +5.5] pkt |
| N potrzebne przy mocy 80% dla efektu 20 pkt | 40 |
| N dostepne | **111** |

## 9. Grupa warm-up — raportowana, nie usuwana

**80 zdarzen** bez wystarczajacej historii do policzenia rangi
bez lookaheadu. Nie wchodza do testu glownego, ale ich rozklad jest tu
podany, zeby bylo widac, ze nie wyciecie ich zrobilo wynik.

| Wielkosc | Wartosc |
|---|---|
| N | 80 |
| Sredni wynik fade'u | -1.9 pkt |
| t | -0.72 |

## 10. Werdykt: **NO-GO**

| # | Przewidywanie karty | Wynik | Ocena |
|---|---|---|---|
| 1 | Iloraz rozdziela kontynuacje od odwrocenia | β = -0.1397, t(HC3) = **-0.60** — **znak przeciwny** do tezy | **zawiedzione** |
| 2 | Efekt rosnie z ilorazem | dolny -0.5, srodkowy **+13.8**, gorny -3.0 pkt — **niemonotonicznie** | **zawiedzione** |
| 3 | Iloraz lepszy niz sama wielkosc impulsu | iloraz -3.0, sama wielkosc +5.1 pkt — **gorszy** | **zawiedzione** |
| 4 | Efekt obecny w wiecej niz jednym typie | znaki niezgodne, zaden typ istotny | **zawiedzione** |
| 5 | Stabilnosc roczna | znak odwraca sie miedzy 2023 a 2024 | **zawiedzione** |
| 6 | Efekt przezywa koszty | netto -5.0 pkt na zdarzenie | **zawiedzione** |

### Co jest tu rozstrzygajace

**Ablacja z sekcji 5.** Karta istniala po to, zeby zastapic zla zmienna H014
(sama wielkosc szoku) zmienna wlasciwa (iloraz do rownowagi). Zmierzone:
iloraz daje -3.0 pkt, sama wielkosc +5.1 pkt.
**Iloraz jest gorszy od zmiennej, ktora mial poprawic.** To jest jedyny
powod istnienia tej karty i on nie dziala.

**Niemonotonicznosc jest tu pouczajaca i warto ja pokazac.** Srodkowy tercyl
daje +13.8 pkt przy t = +2.61 —
gdyby wybrac go po fakcie, wygladalby na znalezisko. Kryterium
monotonicznosci **zadeklarowane z gory** jest dokladnie po to, zeby tego nie
zrobic. Tak zginelo H005 i tak zginelaby ta karta, gdyby jej bronic.

### Moc testu — tym razem jej NIE brakuje

Przy sd 45 pkt wykrycie efektu 20 pkt przy mocy 80%
wymaga **40 obserwacji**, a mamy
**111**. Karta deklarowala przed pomiarem, ze werdykt
„nierozstrzygniete" bedzie dopuszczalny — i tym razem **nie jest potrzebny**.

95% CI sredniego wyniku w gornym tercylu: [-11.4, +5.5] pkt.
Prog +24.2 pkt, ktorego karta potrzebowalaby dla SR ≥ 0.8, **lezy poza tym
przedzialem**. Inaczej niz przy H013, gdzie mocy faktycznie brakowalo, tutaj
efekt tej wielkosci mozemy odrzucic.

> **Nie jest to jednak przypadek nierozstrzygniecia. Uklad wynikow jest
> niezgodny z zadeklarowanymi przewidywaniami mechanizmu w pieciu punktach
> na szesc, w tym w ablacji rozstrzygajacej — dlatego karta nie spelnia
> bramki GO.**

Nie twierdze, ze udowodniono brak jakiegokolwiek efektu wokol publikacji makro.
Twierdze, ze **ta karta, w swojej zamrozonej postaci, nie ma przeslanki**.

### Konsekwencje

| Co | Decyzja |
|---|---|
| **H003** | **REJECTED (pre-flight)**, 0 z 6 prob zuzytych |
| Oryginalny katalog H001-H016 | **zamkniety** — wszystkie karty rozstrzygniete |
| Kalendarz makro | zostaje: darmowy, urzedowy, wielokrotnego uzytku |
| Rodzina warunkowania wielkoscia szoku | **trzecia porazka** (H014, H013, H003) |

Ostatni wiersz jest wnioskiem, nie zalem. Trzy karty probowaly warunkowac
reakcje na zdarzenie wielkoscia impulsu albo jego pochodna i wszystkie trzy
zawiodly w ten sam sposob: **warunkowanie nie poprawialo wyniku, tylko go
pogarszalo albo nie zmienialo**. To jest przeslanka, zeby przestac odwiedzac
te rodzine, dopoki nie pojawi sie nowy argument mechanizmowy.

---

Odtworzenie: `python3 research/W013_H003_preflight.py`
