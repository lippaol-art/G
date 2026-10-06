# Partia 0 — benchmarki B01-B05

*Wygenerowane przez `research/B00_benchmarks.py`, 2026-08-01. Instrument: MNQ, 2,551,265 barow M1, 1873 dni sesyjnych.*

**Status licznika prob: 0 zuzytych.** Benchmarki nie sa proba znalezienia
przewagi — sa linia odniesienia, wzgledem ktorej mierzy sie przyrost kart
wlasnych (rozdz. 8.4 krok 3). Parametry pochodza wprost z literatury i **nie
byly dobierane**; kazde podkrecenie zanizaloby poprzeczke dla naszych hipotez.

Koszty pelne (2.20 USD RT z poslizgiem segmentowym), limity ryzyka wylaczone.
Karty wlasne beda testowane z limitami wlaczonymi — poprzeczka jest wiec
ustawiona na ich niekorzysc, i tak ma byc.

---

## Wyniki zbiorcze

| ID | Setup | Transakcji | Dni czynnych | Netto [USD] | Netto przy x2 kosztach | Sharpe | PF | Win% | MaxDD [USD] |
|---|---|---|---|---|---|---|---|---|---|
| B01 | Domykanie luki otwarcia | 1,551 | 82% | -5,786 | -10,166 | -0.25 | 0.95 | 48% | 12,776 |
| B02 | Wybicie po NR7 (Crabel ~1990) | 279 | 15% | +1,611 | +652 | +0.13 | 1.06 | 48% | 5,911 |
| B03 | Efekt weekendu (Cross 1973 / French 1980) | 355 | 19% | -16,098 | -16,879 | -0.73 | 0.74 | 42% | 20,100 |
| B04 | Momentum wewnatrzdzienne (Gao i in. JFE 2018) | 1,799 | 96% | -10,658 | -16,415 | -0.91 | 0.84 | 46% | 11,580 |
| B05 | Dryf nocny, bezwarunkowo | 1 438 | 100% | — | — | **+0.47** | — | — | — |

*(B05 zmierzony osobno w badaniu W001 — patrz `reports/W001_overnight_drift.md`.)*

Prog projektu: Sharpe >= 0.8 i PF >= 1.15 (rozdz. 1.3). **Zaden z benchmarkow go nie osiaga** — i tak byc powinno: to setupy opisane publicznie kilkadziesiat lat temu, na instrumencie, ktorego wtedy nie bylo.

## Wynik per rok [USD netto]

| ID | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| B01 | -1,514 | -4,064 | -260 | -4,731 | -58 | -1,957 | +5,723 | +1,075 |
| B02 | +527 | -335 | +1,439 | +335 | +725 | +2,462 | -3,853 | +310 |
| B03 | +547 | -2,791 | +36 | +3,470 | -4,758 | +169 | -7,877 | -4,892 |
| B04 | -880 | -353 | -2,317 | -1,764 | -1,426 | -2,008 | +640 | -2,550 |

> **PF i win rate liczone z P&L w dolarach, nie w R.** Reguly B03 i B04 nie
> przewiduja stopa, wiec ich `r_multiple` jest niezdefiniowane. Wersja R-owa
> zwrocilaby dla nich zera wygladajace jak pomiar — silnik sygnalizuje to
> teraz jawnie jako NaN (`r_metrics_valid=false` w JSON-ie).

---

## Komentarz do poszczegolnych benchmarkow

### B01 — Domykanie luki otwarcia

- transakcji: **1,551**, czynny w 82% dni sesyjnych
- brutto -3,925 USD, prowizje 1,861 USD, **netto -5,786 USD**
- Sharpe -0.25 (z poprawka Lo -0.27), PF 0.95, expectancy -3.73 USD/transakcje, +0.003 R
- max DD 12,776 USD przez 1872 dni, koncentracja top-5 *(niezdefiniowana — setup stratny)*

### B02 — Wybicie po NR7 (Crabel ~1990)

- transakcji: **279**, czynny w 15% dni sesyjnych
- brutto +1,946 USD, prowizje 335 USD, **netto +1,611 USD**
- Sharpe +0.13 (z poprawka Lo +0.13), PF 1.06, expectancy +5.77 USD/transakcje, -0.018 R
- max DD 5,911 USD przez 485 dni, koncentracja top-5 256%

> **Koncentracja 256% przy progu 40% (rozdz. 1.3).** Piec najlepszych dni daje 2.6x calego wyniku — reszta historii jest netto ujemna. Setup dodatni w sumie, ale nie majacy przewagi: to loteria z dodatnim losem, nie edge. Karta wlasna z takim profilem zostalaby odrzucona przez bramke, i ten benchmark tez nie jest poprzeczka do przeskoczenia — jest ostrzezeniem, jak wyglada szum udajacy wynik.

### B03 — Efekt weekendu (Cross 1973 / French 1980)

- transakcji: **355**, czynny w 19% dni sesyjnych
- brutto -15,672 USD, prowizje 426 USD, **netto -16,098 USD**
- Sharpe -0.73 (z poprawka Lo -0.74), PF 0.74, expectancy -45.35 USD/transakcje *(R niezdefiniowane — regula bez stopa)*
- max DD 20,100 USD przez 1640 dni, koncentracja top-5 *(niezdefiniowana — setup stratny)*

### B04 — Momentum wewnatrzdzienne (Gao i in. JFE 2018)

- transakcji: **1,799**, czynny w 96% dni sesyjnych
- brutto -8,499 USD, prowizje 2,159 USD, **netto -10,658 USD**
- Sharpe -0.91 (z poprawka Lo -0.92), PF 0.84, expectancy -5.92 USD/transakcje *(R niezdefiniowane — regula bez stopa)*
- max DD 11,580 USD przez 1872 dni, koncentracja top-5 *(niezdefiniowana — setup stratny)*

---

## Jak uzywac tych liczb

Krok 3 testu oryginalnosci (rozdz. 8.4) wymaga, by karta wlasna wykazala
**przyrost ponad najblizszy benchmark po kosztach**. Liczby maszynowe leza
w `reports/benchmarks.json` — porownanie ma byc automatyczne, nie z pamieci.

| Karta warunkujaca na... | Musi pobic |
|---|---|
| luce otwarcia | B01 |
| kontrakcji zakresu / wybiciu | B02 |
| dniu tygodnia | B03 |
| porze dnia, momentum sesyjnym | B04 |
| trzymaniu przez noc | B05 |

**Pobicie benchmarku jest warunkiem koniecznym, nie wystarczajacym.** Karta
musi dodatkowo przejsc krok 4 — ablacje pokazujace, ze jej wlasne warunki
cokolwiek wnosza, a nie sa dekoracja wokol setupu publicznego.

Odtworzenie: `python3 research/B00_benchmarks.py`
