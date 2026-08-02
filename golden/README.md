# Golden baseline Gen1

Zamrożone zachowanie systemu **przed** konsolidacyjnym refaktorem. Jedyna rzecz,
która po porządkach pozwoli stwierdzić, że system liczy **to samo**.

Plik: `golden/baseline.json` (schemat v1). Generator: `scripts/golden_baseline.py`.

```bash
python3 scripts/golden_baseline.py            # zapis baseline'u
python3 scripts/golden_baseline.py --sprawdz  # bramka: porównanie z zapisanym
```

`--sprawdz` kończy się kodem 0 przy pełnej zgodności, 1 przy jakiejkolwiek
rozbieżności. Wypisuje **konkretną ścieżkę** różniącej się wartości
(`walidacja.pbo.szum: 0.7285714286 -> 0.51`), nie samą informację, że gałąź
się zmieniła — inaczej raport byłby bezużyteczny przy 20 kB JSON-a.

## Co jest zamrożone — pięć warstw

| Warstwa | Zawartość | Po co |
|---|---|---|
| `dane` | 13 parquet + 3 CSV + 2 manifesty: schemat, liczba wierszy, zakres sesji, SHA-256 | odróżnić zmianę danych od zmiany kodu |
| `silnik` | 8 przypadków na ręcznych barach z **pełnym detalem transakcji** (ceny, powód wyjścia, prowizja, R) + 6 punktów granicznych sesji, w tym obie zmiany czasu | tabela rozstrzygnięć 5.4 i kalendarz to najbardziej krytyczna logika w repo |
| `metryki` | PF, Sharpe (+Lo), Sortino, MDD, MAR, SQN, koncentracja na stałym wektorze R | z tych liczb biorą się progi bramki 1.3 |
| `walidacja` | DSR, moc testu, CPCV, walk-forward, PBO, SPA (obie ścieżki), Monte Carlo | aparat, który decyduje o odrzuceniu lub certyfikacji karty |
| `raporty` + `rejestr` | znormalizowany hash 18 raportów, 8 wyciągniętych metryk, licznik prób, statusy kart | wnioski badawcze Gen1 |

## Dwa hashe, nie jeden

```
hash_danych  = SHA-256(warstwa `dane`)
hash_wynikow = SHA-256(silnik + metryki + walidacja + raporty + rejestr)
```

Przy jednym hashu każde odświeżenie kalendarza makro wyglądałoby jak regresja
silnika. Rozdzielenie jest wymogiem, nie ozdobą.

## Normalizacja przed hashowaniem

Hash surowego Markdown byłby bezużyteczny — raporty zawierają datę generacji,
więc zmieniałyby hash przy identycznych obliczeniach. Przed hashowaniem usuwane
są: linie `*Wygenerowane...` / `*Pobrane...`, ścieżki `/home/...`, białe znaki
na końcach linii i linie puste. Liczby zaokrąglane do 10 miejsc (`PREC`), bo
ostatni bit float potrafi zmienić hash mimo identycznego rachunku.

## Odtwarzalność — potwierdzona trzykrotnie

Wymóg brzmiał: dwa pełne przebiegi z czystego stanu muszą być identyczne, inaczej
refaktor startuje na niestabilnym baseline.

| Przebieg | `hash_wynikow` | Wynik |
|---|---|---|
| 1 (po `rm -rf golden` + czyszczeniu `__pycache__`) | `6a082749…3da11c7` | — |
| 2 (jw., niezależnie) | `6a082749…3da11c7` | **bajt w bajt identyczny** |
| 3 (`--sprawdz`, inna ścieżka kodu) | `6a082749…3da11c7` | BASELINE ZGODNY |

`hash_danych` = `cf16e23b…909d5a2c5` we wszystkich trzech.

Determinizm nie jest przypadkiem: każde ziarno w warstwie walidacji jest stałe
(`seed=`), a warstwa silnika nie dotyka zegara — znaczniki barów są wpisane
na sztywno.

## Wejścia losowe w warstwie walidacji a reguła „zero danych syntetycznych"

Macierze wariantów podawane do PBO i SPA oraz szereg AR(1) do Monte Carlo są
generowane z **ustalonego ziarna**. To nie są dane badawcze i nie wynika z nich
żaden wniosek o rynku — to fixture'y aparatu statystycznego, dokładnie w tej
samej roli, co ręcznie skonstruowane bary w testach silnika. Rozróżnienie jest
identyczne jak zapisane w PLAN i obowiązuje bez zmian: **każdy wniosek o rynku
pochodzi wyłącznie z danych realnych.**

Szereg do bootstrapu jest celowo autokorelowany (AR(1), φ=0,85). Na szeregu iid
bootstrap blokowy i iid są równoważne, więc zapisany niezmiennik
`blokowy_szerszy_niz_iid` nie miałby treści. Przy zależności ma: 0,0361 vs
0,0137 — bootstrap iid zawęża przedział o **62%**, czyli daje fałszywą pewność.
Po to ten moduł istnieje.

## Weryfikacja krzyżowa z dokumentem założycielskim

Warstwa walidacji odtwarza liczby opublikowane w `docs/PLAN.pdf` rozdz. 6.5 i A.1:

| Wielkość | PLAN | Baseline |
|---|---|---|
| DSR, SR 0,8 / T=1500 / N_eff=1 | 0,974 | 0,9744 |
| DSR, SR 0,8 / N_eff=5 / 10 / 30 | 0,776 / 0,647 / 0,452 | 0,7759 / 0,6469 / 0,4517 |
| DSR, SR 1,5 / N_eff=30 | 0,943 | 0,9432 |
| dni do DSR 0,95 przy SR 0,8 | ≈1070 | 1068 |
| N przy mocy 50 / 80 / 90% | 384 / 785 / 1051 | 385 / 785 / 1051 |
| ścieżek CPCV, C(6,2) | 15 | 15 |

Różnice (1068 vs 1070, 385 vs 384) to zaokrąglenia w dokumencie, nie rozbieżność
rachunku.

## ⚠ Znana wada zamrożona świadomie: ścieżka `arch` w `validation/spa.py`

Baseline utrwala **błędne** zachowanie, bo taka jest jego rola — zapisuje stan
faktyczny, a nie pożądany.

`arch.bootstrap.SPA` przyjmuje **straty** (mniej = lepiej). Moduł podaje mu
**zwroty**, więc znak jest odwrócony i testowana jest hipoteza przeciwna do
zamierzonej. Widać to wprost w baseline:

| Wejście (400 obs, 6 wariantów) | ścieżka `arch` | własny fallback |
|---|---|---|
| sam szum | p = 0,898 | p = 0,303 |
| wariant z przewagą +0,30σ | p = **0,898** | p = **0,002** |

Identyczna p-wartość w obu przypadkach jest rozstrzygająca — test nie reaguje na
sygnał, którego szuka. Sprawdzenie bezpośrednie potwierdza przyczynę: przy tej
samej macierzy `SPA(zera, M)` daje `consistent = 0,898`, a `SPA(zera, −M)` daje
`0,000`.

**Wpływ na dotychczasowe wnioski: żaden.** SPA nie było użyte w W001–W013 —
licznik prób wynosi 0, żadna karta nie doszła do bramki, na której SPA działa.

**Naprawa jest pozycją nr 1 planu refaktoru** i **świadomie zmieni
`hash_wynikow`.** Dlatego baseline rejestruje też ścieżkę `fallback`, która po
naprawie ma zostać bez zmian — to ona będzie dowodem, że naprawiono znak, a nie
przepisano test.

## Środowisko

`golden/srodowisko.txt` zapisuje **konkretne** wersje, które wyprodukowały te
hashe (Python 3.11.15, polars 1.43.1, numpy 2.4.6, scipy 1.17.1, arch 8.0.0…).
`pyproject.toml` celowo trzyma dolne ograniczenia — to plik instalacyjny, nie
rejestr. Przy niezgodnym `--sprawdz` różnica wersji jest **pierwszą** rzeczą do
sprawdzenia, zanim uzna się rozbieżność za regresję kodu: zmiana generatora
losowego w numpy albo algorytmu bootstrapu w `arch` przesunie warstwę walidacji
bez jednej linijki zmiany w tym repo.

## Stan Gen1 utrwalony w baseline

- licznik prób: **0**
- kart odrzuconych w pre-flightach: **8** (H001, H002, H003, H005, H010, H011, H013, H014)
- karty warunkowe: H004, H016
- raportów badawczych: 18
- zbiory: 13 parquet (MNQ/NQ/ES 1m + 10 instrumentów K6), 3 CSV kalendarzy

## Kiedy baseline wolno zaktualizować

Tylko wtedy, gdy zmiana wyniku jest **zamierzona i opisana**. Procedura:

1. `--sprawdz` pokazuje rozbieżności,
2. każda rozbieżność zostaje wyjaśniona w commicie (co i dlaczego się zmieniło),
3. dopiero wtedy regeneracja baseline'u.

Regeneracja „bo nie przechodziło" jest zniszczeniem jedynego zabezpieczenia,
jakie ma refaktor.
