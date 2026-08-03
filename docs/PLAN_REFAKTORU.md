# Plan refaktoru — do decyzji, nie do wykonania

Krok 13 Etapu 2, ostatni. **Nic z tego dokumentu nie jest wdrożone i nie
zostanie wdrożone bez osobnej zgody.**

Podstawa: `docs/ARCHITEKTURA.md` (mapa), `docs/AUDYT_KODU.md` (co znaleziono),
`docs/ZALOZENIA.md` (co wolno ruszyć), `golden/baseline.json` (czym mierzymy,
że nic się nie zepsuło).

---

## 0. Rekomendacja, zanim przejdę do listy

**Proponuję refaktor minimalny — trzy pozycje zamiast dziewięciu.**

Audyt znalazł 79 linii martwego kodu i cztery ogniska duplikacji w 11 817
liniach. To jest 0,7%. Repozytorium nie ma problemu, który uzasadniałby duże
porządki, a każda zmiana w kodzie krytycznym finansowo niesie ryzyko błędu
gorszego niż to, co usuwa.

Jednocześnie golden baseline ujawnił **jeden realny błąd semantyczny**
w module bramkowym. To on jest właściwym powodem, żeby w ogóle otwierać ten
etap — nie duplikacja.

Jeśli miałbym wybrać jedną rzecz: **napraw SPA, zostaw resztę.** Poniżej pełna
lista z ryzykiem każdej pozycji, żeby decyzja była świadoma, a nie oparta na
moim streszczeniu.

---

## 1. Pozycje rekomendowane

### R1 — Naprawa znaku w `validation/spa.py` 🔴 KRYTYCZNE

**Co:** `arch.bootstrap.SPA` przyjmuje straty (mniej = lepiej), moduł podaje mu
zwroty. Przekazać `-M` zamiast `M`.

**Dowód, że to błąd, a nie moja interpretacja:**

| Wejście (400 obs, 6 wariantów) | ścieżka `arch` | własny fallback |
|---|---|---|
| sam szum | p = 0,898 | p = 0,303 |
| wariant z przewagą +0,30σ | p = **0,898** | p = **0,002** |
| wariant z przewagą +1,00σ (t ≈ 20) | p = 0,120 | p = 0,002 |

Identyczna p-wartość dla szumu i dla przewagi jest rozstrzygająca: test nie
reaguje na sygnał, którego szuka. Sprawdzenie bezpośrednie: przy tej samej
macierzy `SPA(zera, M)` daje `consistent = 0,898`, a `SPA(zera, −M)` daje
`0,000`.

**Wpływ na dotychczasowe wnioski: żaden.** SPA nie było użyte w W001–W013,
licznik prób wynosi 0.

**Ryzyko zmiany:** niskie. Jedna linia, moduł nieużywany produkcyjnie.
Ryzyko **niezmienienia** jest wysokie: pierwsza karta, która dojdzie do bramki
SPA, dostanie odwrotny werdykt.

**Test zabezpieczający — do napisania PRZED zmianą:**
```python
def test_spa_wykrywa_przewage_ktorej_szuka():
    """ZNANA ODPOWIEDZ: wariant z przewaga 1σ na 400 obserwacjach ma t≈20.
    Test, ktory tego nie odrzuca, testuje hipoteze przeciwna."""
    M = szum(400, 6); M[:, 0] += 1.0
    assert superior_predictive_ability(M).pvalue < 0.01
    assert superior_predictive_ability(szum(400, 6)).pvalue > 0.10
```
Ten test **musi być czerwony przed poprawką i zielony po niej**. Napisanie go po
zmianie nie dowodzi niczego.

**Wpływ na baseline:** `hash_wynikow` **zmieni się świadomie**. Wolno zmienić
się wyłącznie kluczom `walidacja.spa.*_arch`. Klucze `*_fallback` muszą zostać
bit w bit — to one dowodzą, że naprawiono znak, a nie przepisano test.

### R2 — Podpięcie `verify_continuity` i `describe` 🟠

**Co:** dwie funkcje napisane pod PLAN 4.6 i nigdy niewywołane. Wywołać je
w `scripts/data_quality.py` i pokryć testami.

**Dlaczego to nie jest usunięcie:** kontrola ciągłości po rolowaniu jest
wymogiem specyfikacji. Dziś jej po prostu nie ma — brak wykonania, nie nadmiar
kodu. Usunięcie zamiotłoby lukę pod dywan.

**Ryzyko:** niskie dla wyników (kod raportujący), **średnie dla nerwów**:
kontrola może pokazać, że ciągłość gdzieś nie domyka. To jest cel, nie problem.

**Wpływ na baseline:** zmieni się hash `reports/data_quality.md` (nowa sekcja).
Zmiana zamierzona.

### R3 — Wspólne `t_stat` z zadeklarowaną semantyką 🟠

**Co:** siedem kopii, cztery różne semantyki obsługi NaN i progu N. Wzór
identyczny we wszystkich, więc **żadna opublikowana liczba nie jest błędna** —
rozjazd dotyczy przypadków brzegowych.

**Dlaczego to nie jest mechaniczne scalenie:** wybór semantyki **zmienia
wyniki**. Wariant z `np.isfinite` po cichu odrzuca obserwacje z NaN i liczy
statystykę z mniejszej próby; wariant bez niego zwraca `nan` i głośno psuje
raport.

**Moja rekomendacja: głośna wersja.** Milczące zmniejszenie próby to dokładnie
ta klasa błędu, którą pre-flighty mają łapać. Jeśli w danych są NaN-y, chcę
o tym wiedzieć w momencie liczenia, a nie odkryć pół roku później, że tercyl
liczono z 40 obserwacji zamiast 111.

**Ryzyko: średnie i nieoczywiste.** W010 i W013 używają dziś wersji
filtrującej. Po ujednoliceniu na wersję głośną ich liczby mogą się zmienić albo
raporty mogą przestać się generować. To jest **informacja, nie awaria** — ale
trzeba ją obsłużyć świadomie.

**Test zabezpieczający:** `--sprawdz` z zamrożonymi metrykami
`W010_h001_beta_wolumen_t`, `W010_h002_pochodzenie_t`, `W013_beta_ranga_t`.
Jeśli którakolwiek się ruszy, trzeba **przeliczyć raport i opisać różnicę**,
a nie dostroić semantykę do starej liczby.

---

## 2. Pozycje możliwe, których NIE rekomenduję teraz

Wypisane, bo decyzja należy do właściciela, ale z uzasadnieniem, czemu bym ich
nie ruszał.

### N1 — Rozbicie `engine/backtest.py` (529 linii) 🔴 ODRADZAM

Największy moduł krytyczny, naturalny kandydat na podział. **I najgorsze możliwe
miejsce na refaktor.**

Pokryty 66 testami z trzech plików, ale te testy sprawdzają **zachowanie**, nie
strukturę. Podział pętli zdarzeń na moduły może przestawić kolejność operacji
w barze — a ta kolejność **jest częścią specyfikacji**, nie detalem
implementacji (wyjścia przed wypełnieniami, limity ryzyka przed strategią).
Błąd tej klasy jest cichy i produkuje ładniejsze wyniki.

Korzyść: czytelność. Ryzyko: fałszywy P&L. Nieproporcjonalne.

### N2 — Wyciągnięcie `hm` do `engine/sessions.py` 🟠 ODKŁADAM

Trzy implementacje minut od północy ET; dwie niosą osobno wpisane ostrzeżenie
o przepełnieniu `Int8` w polars, które realnie kosztowało jeden pusty przebieg
W009.

Argument za: pułapka udokumentowana dwa razy zostanie przy trzecim użyciu
przeoczona. Argument przeciw: **wszystkie trzy użycia są w kodzie Gen1, który
jest zamrożony.** Wyciągnięcie funkcji do `engine/` znaczy dotknięcie modułu
krytycznego po to, żeby uprościć kod, który się już nie zmienia.

Właściwy moment to **pierwsze użycie w Gen2**, nie teraz.

### N3 — Ujednolicenie `pobierz` / `wczytaj_cache` 🟠 ODKŁADAM

Trzy warianty pobierania HTTP; najuboższy nie ma obsługi gzip — dokładnie tego
braku kosztował `UnicodeDecodeError` przy pierwszym pobraniu z EDGAR.

Argument przeciw ruszaniu teraz: kalendarze są **zbudowane i zahaszowane**
w manifeście. Konsolidacja klienta HTTP bez ponownego pobrania niczego nie
udowadnia, a z ponownym pobraniem — zmienia dane pod baseline'em.

Właściwy moment: przy pierwszym odświeżeniu kalendarza.

### N4 — Przeniesienie `research/W009.zbuduj` do biblioteki 🟢 ODRADZAM

W009 jest de facto biblioteką, bo W011 i W012 importują z niego `zbuduj()`.
Strukturalnie brzydkie.

Ale W009 to **zamrożony eksperyment Gen1**. Jego wartością jest to, że plik jest
dokładnie taki, jaki wyprodukował werdykt NO-GO dla H013. Przeniesienie funkcji
gdzie indziej rozbija ten dowód na dwa pliki dla korzyści czysto estetycznej.

Wystarczy **adnotacja w nagłówku**, że moduł pełni podwójną rolę.

### N5 — Podział `scripts/` na pobieranie i raportowanie 🟢 ODRADZAM

Czystsze, ale to przenoszenie plików bez zmiany zachowania. Zysk zerowy, ryzyko
niezerowe (ścieżki w dokumentacji, w REGISTRY, w nagłówkach raportów).

### N6 — Usunięcie `effective_trials_simple` 🟢 NEUTRALNE

Jedyny w repo przypadek kodu **metodologicznie unieważnionego** — audyt 2
zastąpił odcięcie 0,7 algorytmem ONC. Dwanaście linii.

Jeśli usuwać, to z odnotowaniem powodu w commicie. Alternatywa równie dobra:
zostawić z komentarzem „zastąpione przez ONC, poprawka A2-3" — jako ślad
decyzji metodologicznej.

---

## 3. Ryzyko zbiorcze i kolejność

| # | Pozycja | Ryzyko dla wyników | Baseline | Rekomendacja |
|---|---|---|---|---|
| R1 | znak w SPA | **niskie** (nieużywane) | zmienia `spa.*_arch` | **tak** |
| R2 | podpięcie kontroli ciągłości | niskie | zmienia hash raportu | **tak** |
| R3 | wspólne `t_stat` | **średnie** (może ruszyć 3 metryki) | musi przejść `--sprawdz` | tak, ostrożnie |
| N1 | rozbicie `backtest.py` | **wysokie** (fałszywy P&L) | — | **nie** |
| N2 | wspólne `hm` | średnie | — | odłożyć do Gen2 |
| N3 | wspólny klient HTTP | średnie | — | odłożyć do odświeżenia |
| N4 | przeniesienie `zbuduj` | niskie | — | nie, sama adnotacja |
| N5 | podział `scripts/` | niskie | — | nie |
| N6 | `effective_trials_simple` | zerowe | — | obojętne |

**Kolejność, jeśli zapadnie decyzja o R1–R3:** najpierw R1 (osobny commit, żeby
zmiana hasha miała jedną przyczynę), potem R2, na końcu R3 (jedyna, która może
ruszyć liczby badawcze).

**Po każdej pozycji osobno:**
1. `python3 scripts/golden_baseline.py --sprawdz`,
2. każda rozbieżność wyjaśniona w commicie — co, dlaczego, czy zamierzona,
3. dopiero wtedy regeneracja baseline'u.

Regeneracja baseline'u „bo nie przechodziło" jest zniszczeniem jedynego
zabezpieczenia, jakie ma refaktor. Jeśli `--sprawdz` pokazuje coś, czego nie
umiem wyjaśnić, właściwą reakcją jest **cofnięcie zmiany**, nie zaktualizowanie
odcisku.

---

## 4. Czego ten plan świadomie nie obejmuje

- **Żadnego usuwania kodu odrzuconych hipotez.** Osiem kart upadło; ich skrypty
  są jedynym dowodem tych werdyktów. REGISTRY bez nich byłby zbiorem twierdzeń
  bez pokrycia.
- **Żadnej zmiany w `engine/backtest.py`.** Patrz N1.
- **Żadnej zmiany progów, parametrów ani specyfikacji.** Refaktor zmienia
  strukturę kodu, nigdy definicję. Zmiana specyfikacji przy okazji porządków to
  reguła R2 złamana bocznymi drzwiami.

---

## 5. Co jest potrzebne od właściciela

Decyzja w trzech punktach:

1. **R1 (naprawa SPA)** — tak czy nie. To jedyna pozycja, którą uważam za
   konieczną.
2. **R2 i R3** — czy wchodzą teraz, czy czekają na Gen2.
3. **Czy którakolwiek z N1–N6** ma wejść mimo mojej rekomendacji przeciw.
   Odradzam, ale rozumiem argument za czytelnością i decyzja nie jest moja.

Do czasu odpowiedzi **nie zmieniam ani jednej linii kodu produkcyjnego.**
