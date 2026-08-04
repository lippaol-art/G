# D5-B2 — jednodniowy dry run rekonstrukcji

**Specyfikacja jednostki zamrożona przed zakupem:** `docs/D5_ETAP4_SPEC.md` §1.
**Sesja:** 2026-07-30 (posiadana od Etapu 3, już w development secie).
**Data wykonania:** 2026-08-04.

**Czego ten test NIE liczy:** VIF, przyszłego przepływu, przyszłych zwrotów,
P&L, trwałości znaku, żadnego progu ani metryki wynikowej.
**Licznik prób: 0.**

---

## 1. Wynik

```
WSZYSTKIE OSIEM NIEZMIENNIKÓW SPEŁNIONE
```

| # | Niezmiennik | Wynik |
|---|---|---|
| **N1** | rekordy `Trade` rozliczone bez zgubienia i podwójnego przypisania | **984 113 == 984 113** |
| **N2** | każda akcja w dokładnie jednym oknie | 903 116 == 903 116 |
| **N3** | strona akcji jednoznaczna | 0 akcji spoza `{B, A}` |
| **N4** | suma pasywnych `Fill` == rozmiar akcji | **0 niezgodności z 903 116** |
| **N5** | akcja przecinająca minutę w całości do minuty ostatniego `ts_recv` | 0 przecinających, 0 źle przypisanych |
| **N6** | akcja nie przekracza koperty `F_LAST` | 842 757 kopert z akcją |
| **N7** | kompletność okien minutowych | **390 okien, 0 pustych, 0 poza RTH** |
| **N8** | determinizm | dwa przebiegi identyczne |

---

## 2. Statystyki opisowe

*(opis próbki, nie metryki wynikowe)*

| | |
|---|---|
| Rekordów w RTH | 38 306 877 |
| w tym `Trade` / `Fill` | 984 113 / 1 649 924 |
| Kopert `F_LAST` | 34 810 512 |
| **Akcji agresywnych** | **903 116** |
| Strony | 449 661 kupna / 453 455 sprzedaży |
| Akcji na okno | min 408, mediana 1 689, max 7 718 |

Rekordów `Trade` w jednej akcji: 838 701 pojedynczych, 54 698 po dwa, 6 817 po
trzy, 1 581 po cztery, 1 319 po pięć lub więcej.

---

## 3. Dwie reguły, które na tym dniu nie mają skutku

Zapisuję to jawnie, bo łatwo byłoby ogłosić, że „reguły zostały zweryfikowane
na realnych danych". **Nie zostały — dwie z czterech nie miały czego rozstrzygać.**

### N5 wyszło zerowe: żadna akcja nie przecina granicy minuty

Akcje trwają ułamki milisekundy, więc reguła przypisania do minuty ostatniego
`ts_recv` (§2.1) jest na tej sesji **bez praktycznego skutku**. Zostaje jako
zabezpieczenie poprawności i jest pokryta testem syntetycznym, ale nie udaję,
że cokolwiek zmieniła.

### Reguła 3 nie zadziałała ani razu

Akcji jest **903 116**, a unikalnych `order_id` agresora **903 107** —
9 akcji nadmiarowych, pochodzących od **8 identyfikatorów** (jeden dał trzy
akcje, siedem po dwie). Zmierzyłem przyczynę zamiast ją założyć:

| Przyczyna podziału | Przypadków |
|---|---|
| **reguła 2** — ten sam agresor w dwóch różnych kopertach `F_LAST` | **8** |
| **reguła 3** — powrót `order_id` po innym agresorze w tej samej kopercie | **0** |

Moje pierwsze przypuszczenie wskazywało na regułę 3. **Było błędne.**
Wszystkie osiem podziałów pochodzi z granicy koperty.

Reguła 3 pozostaje w specyfikacji, bo opisuje sytuację logicznie możliwą
i pokrytą testem syntetycznym — ale **na jedynym dniu, jaki mamy, nie wystąpiła
ani razu**. To znaczy, że jej wpływ na wynik miesięczny jest nieznany i może
być zerowy.

---

## 4. Co ten test faktycznie potwierdza, a czego nie

**Potwierdza:** implementacja zamrożonej definicji jest wewnętrznie spójna,
deterministyczna, nie gubi ani nie dubluje rekordów, produkuje kompletny zbiór
390 okien i utrzymuje niezmiennik sumy pasywnych wypełnień na 903 116 akcjach
bez wyjątku.

**Nie potwierdza:** że definicja jest *właściwa* dla mechanizmu. To rozstrzyga
dopiero test identyfikowalności na pełnym miesiącu, przy niezmienionych progach
z §8. Dry run sprawdza, czy narzędzie działa — nie czy mierzy coś użytecznego.

**Nie zastępuje** uruchomienia na maszynie właściciela projektu (Test 1).

---

## 5. Reprodukcja

| | |
|---|---|
| Moduł | `engine/mbo_events.py` |
| Testy syntetyczne | `tests/test_mbo_events.py` — 21 przypadków, siedem klas brzegowych |
| Dry run | `scripts/dry_run_d5b2.py` → `reports/D5_b2_dry_run.json` |

Fixture'y w testach są budowane ręcznie. To **nie są dane rynkowe** — bez nich
nie da się udowodnić poprawności reguł brzegowych, bo w danych występują rzadko
albo, jak reguła 3, wcale.
