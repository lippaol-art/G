# R1 — naprawa znaku w `validation/spa.py`

Raport regresyjny. Dowód, że test był czerwony **przed** poprawką i zielony po
niej, wraz z pełnym pomiarem obu implementacji.

**Baseline odniesienia:** commit `a1aba1c0c47fce2e958374e2614e5744b6882027`
(tag `gen1-baseline`).

---

## 1. Błąd

`arch.bootstrap.SPA` operuje na **stratach** — mniej znaczy lepiej — a jego
hipoteza zerowa brzmi „benchmark nie jest gorszy od żadnego modelu". Moduł
podawał mu `returns_matrix`, czyli **zwroty**. Testowana była hipoteza
przeciwna do zamierzonej.

Błąd przeżył 233 testy, bo **każdy z nich wołał tę funkcję
z `force_fallback=True`**. Ścieżka domyślna — ta, która zadziała w każdym
uruchomieniu produkcyjnym — nie była testowana w ogóle. Wykrył go dopiero
golden baseline, który zapisał obie ścieżki obok siebie.

## 2. Test przed poprawką — CZERWONY

`pytest tests/test_montecarlo_spa.py::TestSPASciezkaArch` na niezmienionej
implementacji:

```
tests/test_montecarlo_spa.py F.F.FFF                                    [100%]
5 failed, 2 passed
```

| Test | Wynik przed poprawką |
|---|---|
| `test_arch_wykrywa_przewage_ktorej_szuka` | **FAIL** — `p=0.8980` przy przewadze 1σ na 400 obs (t ≈ 20) |
| `test_arch_rozroznia_szum_od_przewagi` | **FAIL** — `p=0.8980` **identycznie** dla szumu i dla przewagi |
| `test_sama_strategia_ujemna_nie_daje_istotnosci` | **FAIL** — `p=0.0000` dla puli, w której **każdy** wariant traci |
| `test_warianty_identyczne_zachowuja_sie_jak_jeden` | **FAIL** — `p=0.4633` przy przewadze 0,60σ |
| `test_obie_sciezki_zgodne_co_do_werdyktu` | **FAIL** — `[silna_przewaga] arch: p=0.8100` |
| `test_arch_nie_odrzuca_na_samym_szumie` | pass — **trywialnie**, bo zepsuty test nie odrzuca niczego |
| `test_best_variant_i_best_mean_w_konwencji_zwrotow` | pass — raportowanie liczone z `M`, nie z `-M`; ta część była poprawna |

Najmocniejszy pojedynczy dowód to trzeci wiersz: **pula, w której każdy wariant
traci, dostawała p = 0,0000**. Odwrócenie widać w obie strony, nie tylko jako
brak czułości.

Dwa testy, które przeszły, są tu równie pouczające: test „szum nie odrzuca H0"
przechodzi na zepsutej implementacji **trywialnie**, bo ta nie odrzuca niczego.
Sam by błędu nigdy nie wykrył.

## 3. Poprawka

Jedna linia w ścieżce `arch`:

```python
straty = -M
spa = SPA(benchmark, straty, reps=n_bootstrap, block_size=int(block_size), seed=seed)
```

`best_variant` i `best_mean` pozostają liczone z `M`, czyli **w konwencji
zwrotów** — wynik raportujemy jako zwrot, nawet gdy implementacja wewnętrznie
operuje na stratach.

## 4. Test po poprawce — ZIELONY

```
tests/test_montecarlo_spa.py .............................              [100%]
29 passed
```

## 5. Obie implementacje na pięciu przypadkach o znanej odpowiedzi

500 replikacji bootstrapu, ziarno 9.

| Przypadek | `arch` p | fallback p | zgodny werdykt | `best_variant` | `best_mean` |
|---|---|---|---|---|---|
| sam szum | 0,6320 | 0,6926 | ✅ brak odrzucenia | 2 | +0,0456 |
| silna przewaga (+1,0σ) | 0,0000 | 0,0020 | ✅ odrzucenie | 0 | +0,9240 |
| wszystkie warianty ujemne (−0,5σ) | 0,7920 | 0,6547 | ✅ brak odrzucenia | 1 | **−0,4973** |
| jeden z 8 ma przewagę | 0,0000 | 0,0020 | ✅ odrzucenie | 0 | +0,5714 |
| 5 wariantów identycznych | 0,0000 | 0,0020 | ✅ odrzucenie | 0 | +0,6724 |

`best_variant` i `best_mean` są **identyczne** w obu ścieżkach we wszystkich
pięciu przypadkach. Wiersz trzeci potwierdza konwencję: przy samych stratnych
wariantach `best_mean` wynosi −0,4973, czyli jest **ujemnym zwrotem** — nie
dodatnią stratą i nie liczbą ze zmienionym znakiem.

Różnice p-wartości między ścieżkami (0,0000 vs 0,0020) są oczekiwane: to dwie
różne implementacje bootstrapu, a fallback ma podłogę `1/(1+n_bootstrap)`.
Werdykt jest zgodny w każdym przypadku i to jest właściwe kryterium.

## 6. Kontrolowana zmiana golden baseline

`python3 scripts/golden_baseline.py --sprawdz`:

```
ROZNICA   hash_wynikow: 6a082749… -> e64e128f…
ROZNICA   walidacja.spa.szum_arch.p:        0.898 -> 0.248
ROZNICA   walidacja.spa.z_przewaga_arch.p:  0.898 -> 0.0

dane   : OK
ROZBIEZNOSCI: 3 zmian, 0 usunietych, 0 nowych
```

Zmieniły się **wyłącznie** dwa klucze `walidacja.spa.*_arch.p` oraz hash
zbiorczy, który je obejmuje. Bez zmian pozostały:

- **oba klucze fallbacku** (`szum_fallback.p = 0.3033932136`,
  `z_przewaga_fallback.p = 0.001996008`) — to one dowodzą, że naprawiono znak,
  a nie przepisano test,
- `best_variant`, `sredni_wynik` i `implementacja` we wszystkich czterech
  wpisach SPA,
- warstwy `silnik`, `metryki`, `raporty`, `rejestr` oraz cała reszta warstwy
  `walidacja`,
- `hash_danych` = `cf16e23b…`.

## 7. Wpływ na wnioski Gen1

**Żaden.** SPA nie zostało użyte w żadnym z badań W001–W013 ani w B00. Licznik
prób wynosi 0, żadna karta nie doszła do bramki, na której SPA działa. Wszystkie
osiem werdyktów odrzucenia pozostaje bez zmian, tak samo wszystkie liczby
w raportach.

Wartość poprawki jest w całości przyszła: pierwsza karta, która dojdzie do
bramki SPA, dostałaby odwrotny werdykt.

## 8. Kontrole

| Kontrola | Wynik |
|---|---|
| `pytest` | 437 passed, 1 skipped |
| `ruff check engine validation scripts tests research` | czysty |
| `mypy engine validation --ignore-missing-imports` | brak uwag, 22 pliki |
| golden `--sprawdz` | rozbieżność wyłącznie w `spa.*_arch` |

Odtworzenie: `pytest tests/test_montecarlo_spa.py::TestSPASciezkaArch`.
