# Audyt kodu martwego i zduplikowanego

Krok 9 Etapu 2. **Dokument rozpoznawczy — nic tu nie jest usuwane.** Decyzje
zapadają dopiero w `docs/PLAN_REFAKTORU.md` i wymagają osobnej zgody.

Zakres: 44 pliki `.py`, 11 817 linii, 430 testów. Metoda: analiza AST (definicje
publiczne kontra wszystkie użycia w repo), porównanie nazw funkcji między
modułami, ręczna weryfikacja każdego trafienia.

## 0. Sześć kategorii — bo „nieużywane" znaczy sześć różnych rzeczy

Zlanie ich w jedno („usuń, czego nikt nie woła") skasowałoby kod frozen Gen1
i całą infrastrukturę badawczą. Dlatego rozdzielenie jest pierwszym krokiem
audytu, nie formalnością.

| # | Kategoria | Reguła |
|---|---|---|
| 1 | **Rdzeń produkcyjny** | `engine/` + `validation/` — kod, na którym stanie każda przyszła karta. Zmiana wymaga baseline'u i testów. |
| 2 | **Infrastruktura badawcza wspólna** | `research/benchmarks.py`, `research/W009.zbuduj` — biblioteki, choć leżą w `research/`. |
| 3 | **Zamrożone eksperymenty Gen1** | `research/W001–W013` — **NIE USUWAĆ.** To dowód każdego opublikowanego wniosku. |
| 4 | **Kod raportujący** | `scripts/*_report.py`, generatory Markdown. Ryzyko zmiany: mylący raport, nie fałszywy P&L. |
| 5 | **Kod naprawdę martwy** | zdefiniowany, nigdy nie wywołany, nieobjęty testem, bez roli w specyfikacji. |
| 6 | **Realna duplikacja** | ta sama logika w ≥2 miejscach, gdzie rozjazd zmieni wynik. |

Kategoria 3 jest tu najważniejsza i wynika z reguły projektu: **kod odrzuconej
hipotezy nie jest kodem martwym.** Osiem kart upadło w pre-flightach; gdyby
skrypty zniknęły, żaden z tych werdyktów nie byłby odtwarzalny, a REGISTRY
zamieniłby się w zbiór twierdzeń bez dowodu.

## 1. Kod naprawdę martwy — cztery symbole

Skan AST: symbol publiczny bez **ani jednego** użycia poza własną definicją,
zweryfikowany następnie ręcznie (`grep` po całym repo, łącznie z raportami).

| Symbol | Plik | Linii | Test | Ocena |
|---|---|---|---|---|
| `verify_continuity` | `engine/roll.py` | 43 | ✅ 8 testów (R2) | **Luka w wykonaniu specyfikacji, nie śmieć.** PLAN 4.6 wymaga kontroli ciągłości po rolowaniu; funkcja istnieje, ale nigdy nie została podpięta do `scripts/data_quality.py`. Odpowiedź to **wywołać ją**, nie usunąć. |
| `describe` | `engine/loader.py` | 20 | ✅ podpięte (R2) | Opis zbioru. Nadaje się na wywołanie w sanity-report zamiast ręcznego liczenia. Ta sama diagnoza. |
| `ticks_to_usd` | `engine/costs.py` | 4 | **brak** | Konwersja tick→USD. Jednolinijkowiec, ale należy do publicznego API modelu kosztów. Nieszkodliwy. |
| `effective_trials_simple` | `validation/dsr.py` | 12 | **brak** | Uproszczony N_eff przez odcięcie 0,7. Audyt 2 **zastąpił** tę metodę algorytmem ONC (poprawka A2-3), więc jest to jedyny w repo przypadek kodu, który został metodologicznie unieważniony. Kandydat do usunięcia z odnotowaniem powodu. |

**Łącznie 79 linii, czyli 0,7% repo.** To jest wynik, którego się nie spodziewałem
po 11,8 tys. linii i który wart jest wypowiedzenia wprost: **repozytorium nie ma
problemu z kodem martwym.** Trzy z czterech trafień to nie śmieci, tylko funkcje
napisane pod specyfikację i nigdy nie podpięte — brak wykonania, nie nadmiar.

## 2. Realna duplikacja — jedno trafienie poważne, dwa drobne

### 2.1 `t_stat` — siedem kopii, cztery różne semantyki 🔴

Najpoważniejsze ustalenie całego audytu.

| Plik | NaN | Próg N | Zerowa wariancja |
|---|---|---|---|
| `W001_overnight_drift.py` | propaguje | brak | dzieli przez zero |
| `W006_H014_preflight.py` | propaguje | brak | dzieli przez zero |
| `W009_H013_preflight.py` | propaguje | `> 1` | dzieli przez zero |
| `W012_H013_przekroje.py` | propaguje | `> 2` | dzieli przez zero |
| `W004_partia1_preflight.py` | propaguje | `>= 2` | **zwraca nan** |
| `W010_partia3_preflight.py` | **odfiltrowuje** | `> 2` | dzieli przez zero |
| `W013_H003_preflight.py` | **odfiltrowuje** | `> 2` | dzieli przez zero |

Sam wzór (`mean / std(ddof=1) · √n`) jest we wszystkich siedmiu identyczny, więc
**żadna opublikowana liczba nie jest przez to błędna**. Rozjazd dotyczy obsługi
przypadków brzegowych.

I tu jest pułapka, przez którą to nie jest zwykłe „wyciągnij do wspólnego
modułu": **wybór semantyki zmienia wyniki.** Wariant z `np.isfinite` po cichu
odrzuca obserwacje z NaN i liczy statystykę z mniejszej próby; wariant bez
niego zwraca `nan` i głośno psuje raport. Drugi jest bezpieczniejszy —
milczące zmniejszenie próby to dokładnie ta klasa błędu, którą pre-flighty mają
łapać. Konsolidacja musi więc **zadeklarować semantykę**, a potem sprawdzić, czy
przy tej semantyce raporty W010 i W013 dają te same liczby. Baseline to wykryje:
`W010_h001_beta_wolumen_t`, `W010_h002_pochodzenie_t` i `W013_beta_ranga_t` są
w nim zamrożone.

### 2.2 Minuty od północy ET (`hm`) — trzy implementacje 🟠

`research/W009`, `research/W010` i pośrednio `scripts/make_k6_clean.py` liczą to
samo. Dwa pierwsze niosą **osobno wpisany komentarz** o tej samej pułapce:
`polars.dt.hour()` zwraca `Int8`, więc `hour * 60` przepełnia się cicho do
zakresu [−128, 127] i wszystkie filtry godzinowe zaczynają działać na śmieciach,
nie rzucając błędu. Kosztowało to jeden pusty przebieg W009.

To jest podręcznikowy argument za wyciągnięciem do `engine/sessions.py`: pułapka
udokumentowana dwa razy w dwóch plikach to pułapka, która przy trzecim użyciu
zostanie przeoczona. `make_k6_clean.py` trzyma `et_h` i `et_m` osobno i nie
mnoży — dziś bezpieczny, ale bez ochrony przed czyjąś przyszłą optymalizacją.

### 2.3 `pobierz` / `wczytaj_cache` — trzy i dwa warianty 🟠

`scripts/build_earnings.py` (29 l), `scripts/classify_earnings.py` (24 l),
`scripts/build_macro.py` (6 l) — pobieranie HTTP z nagłówkiem User-Agent
wymaganym przez SEC, obsługą gzip i cache na dysku. Rozjazd rozmiarów pokazuje,
że najuboższa wersja nie ma obsługi gzip — dokładnie tego braku kosztował
`UnicodeDecodeError` przy pierwszym pobraniu EDGAR.

Ryzyko przy rozjeździe: **cichy błąd pobierania danych źródłowych**, więc mimo
że to `scripts/`, klasyfikacja jest wyższa niż „raportujące".

### 2.4 `_ridge` — dwie kopie 🟢

`engine/ndx_sensitivity.py` i `research/W009`. Cztery i sześć linii. W009 celowo
trzyma własną, żeby pre-flight nie zależał od zmian w module produkcyjnym.
**Uzasadniona**, do zostawienia z komentarzem.

## 3. Fałszywe trafienia — sprawdzone i odrzucone

Zapisane, żeby nikt nie „naprawiał" ich w przyszłości.

| Podejrzenie | Werdykt |
|---|---|
| `research/benchmarks.py` (280 l) **i** `research/B00_benchmarks.py` (262 l) — dwa moduły benchmarków | **NIE duplikacja.** Poprawny podział biblioteka/uruchamiacz: pierwszy definiuje klasy B01–B04, drugi je uruchamia przez `from research.benchmarks import BENCHMARKI`. |
| `klasyfikuj` w `engine/earnings.py` i `scripts/classify_earnings.py` | **NIE duplikacja.** Różne rzeczy: pierwsza klasyfikuje **porę** publikacji (BMO/AMC), druga **rodzaj** komunikatu z nagłówka. Zbieżność nazw jest myląca i to jedyny zarzut. |
| `sesja_reakcji` w `earnings.py` i `macro.py` | **NIE duplikacja.** Wyniki reagują w następnej sesji RTH, dane makro — w bieżącej. Różna reguła, ta sama nazwa. |
| `main` w 21 plikach | Punkt wejścia skryptu. Nie ma tu nic do zrobienia. |
| `sesje` w `W001` i `W010` | Różne agregaty (dryf nocny kontra charakterystyka nocy i RTH). Zbieżność nazw. |

Trzy z pięciu to **kolizje nazw, nie kodu**. To osobny, drobniejszy problem
i jedyne, czego wymaga, to precyzyjniejsze nazwy przy okazji dotykania tych
plików.

## 4. Czego audyt NIE znalazł

Równie ważne, jak lista trafień:

- **zero** kodu duplikującego logikę silnika poza `engine/`,
- **zero** własnych implementacji rozstrzygania SL/TP w skryptach badawczych,
- **zero** obejść `engine.sessions` przy liczeniu `trade_date`,
- **zero** miejsc, w których poziom międzysesyjny liczono by na `px_adj`
  (zakaz z PLAN 4.3 pilnowany przez `assert_raw_series`).

Czyli: dyscyplina, która najbardziej groziła fałszywym P&L, została utrzymana.

## 5. Wnioski dla planu refaktoru

1. **Skala problemu jest mała.** 79 linii martwych i cztery ogniska duplikacji
   w 11,8 tys. linii. Refaktor „na wielkie porządki" byłby nieproporcjonalny do
   znaleziska i wprowadziłby ryzyko większe niż to, które usuwa.
2. **Najpilniejsza pozycja nie pochodzi z tego audytu**, tylko z golden
   baseline: odwrócony znak w ścieżce `arch` w `validation/spa.py`. Jeden błąd
   semantyczny w module bramkowym waży więcej niż wszystkie cztery ogniska
   duplikacji razem.
3. **Trzy z czterech symboli martwych to brak wykonania specyfikacji**, więc
   właściwą reakcją jest podpięcie, nie usunięcie.
4. **Konsolidacja `t_stat` wymaga decyzji semantycznej**, nie mechanicznego
   scalenia — i musi przejść przez `--sprawdz` z zamrożonymi metrykami W010/W013.

---

## 6. Stan wykonania (03.08.2026)

| Poz. | Decyzja | Stan |
|---|---|---|
| R1 — znak w SPA | wykonać teraz | ✅ commit `7f681ef`, `golden/ZMIANY.md` v2 |
| R2 — podpięcie kontroli ciągłości | wykonać teraz | ✅ `golden/ZMIANY.md` v3 |
| R3 — wspólne `t_stat` | **nie migrować Gen1**, kanoniczna wersja przy pierwszym użyciu w Gen2 | odłożone |
| N1–N6 | żadna nie wchodzi | odłożone |

**R2 ujawnił rzecz, której audyt statyczny nie mógł zobaczyć:**
`verify_continuity` po podpięciu zgłasza 17 z 29 granic MNQ — nie dlatego, że
dane są złe, tylko dlatego, że jego kryterium („skok ≥ |spread|") jest na
realnych danych futures prawie zawsze spełnione. Ruch 659 pkt z krachu
covidowego opisywany jako „back-adjust nie zadziałał" jest tego dowodem.

Kryterium **nie zostało zmienione** — to byłoby dostrajanie progu pod wynik.
Ograniczenie jest jawne w raporcie i zabezpieczone testem regresyjnym.
Rozstrzygająca jest kontrola niezmiennika arytmetycznego: offset stały
w 90 z 90 kontraktów, rozrzut dokładnie 0.

To jest ilustracja tezy z sekcji 1: trzy z czterech symboli „martwych" były
brakiem wykonania specyfikacji. Po wykonaniu jeden z nich okazał się także
wadliwy — czego nie dało się stwierdzić, dopóki nikt go nie wołał.
