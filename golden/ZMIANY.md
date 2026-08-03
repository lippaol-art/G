# Historia golden baseline

Każda zmiana `hash_wynikow` albo `hash_danych` ma tu wpis. Wpis powstaje
**przed** regeneracją baseline'u, nie po.

Wymagane pola: poprzedni hash, nowy hash, dokładne zmienione klucze, powód,
potwierdzenie wpływu (lub jego braku) na wnioski W001–W013.

Regeneracja bez wpisu jest zniszczeniem jedynego zabezpieczenia, jakie ma
refaktor.

---

## v1 — baseline Gen1 (commit `a1aba1c0c47fce2e958374e2614e5744b6882027`)

Punkt odniesienia. Tag `gen1-baseline`.

```
hash_danych  = cf16e23b8521192448902eaf2bc61498ad8b4f13b375d65de1305e7909d5a2c5
hash_wynikow = 6a082749e0a5128b996907d630a3c4001f856223e9b9a00ed5ec024c43da11c7
```

Odtworzony trzykrotnie z czystego stanu, bajt w bajt. Stan: 430 testów, licznik
prób 0, 8 kart odrzuconych w pre-flightach, 18 raportów.

**Commit `a1aba1c` pozostaje niezmiennym punktem odniesienia Gen1** niezależnie
od tego, czy zdalny tag istnieje (push tagu odmówiony przez proxy git, 403).

---

## v2 — R1: naprawa znaku w `validation/spa.py`

```
hash_danych  = cf16e23b…909d5a2c5   (BEZ ZMIAN)
hash_wynikow = 6a082749…3da11c7  ->  64c8bae33d3d446ebbdac67ccfc419cf536bab0b96729418cdbfbf05c86de4e4
```

### Zmienione klucze — dwa z poprawki, jeden z nowego raportu

| Klucz | Przed | Po | Przyczyna |
|---|---|---|---|
| `walidacja.spa.szum_arch.p` | 0,898 | 0,248 | poprawka znaku |
| `walidacja.spa.z_przewaga_arch.p` | 0,898 | 0,000 | poprawka znaku |
| `raporty.hashe.R1_regresja_spa.md` | — | nowy wpis | dołożony raport regresyjny |

Trzeci wiersz to **nowy plik, nie zmiana istniejącego**. Warstwa `raporty`
skanuje katalog, więc dołożenie raportu regresyjnego dokłada wpis. Żaden
z 18 wcześniejszych hashy się nie zmienił, żadna z 8 wyciągniętych metryk
również — sprawdzone kluczem po kluczu.

Uwaga metodologiczna: sam pomiar `--sprawdz` wykonany **przed** dopisaniem
raportu dawał `hash_wynikow = e64e128f…` i pokazywał dokładnie dwie
rozbieżności. Różnica względem wartości powyżej to wyłącznie dołożony plik.

### Klucze, które MUSIAŁY zostać bez zmian — i zostały

| Klucz | Wartość |
|---|---|
| `walidacja.spa.szum_fallback.p` | 0,3033932136 |
| `walidacja.spa.z_przewaga_fallback.p` | 0,001996008 |
| `best_variant`, `sredni_wynik`, `implementacja` (4 wpisy) | bez zmian |
| warstwy `silnik`, `metryki`, `raporty`, `rejestr` | bez zmian |
| reszta warstwy `walidacja` (DSR, moc, CPCV, WF, PBO, MC) | bez zmian |
| `hash_danych` | bez zmian |

Nietknięty fallback jest tu dowodem, nie formalnością: gdyby zmieniły się obie
ścieżki, nie dałoby się odróżnić naprawy znaku od przepisania testu.

### Powód

`arch.bootstrap.SPA` operuje na stratach (mniej = lepiej), moduł podawał mu
zwroty. Testowana była hipoteza przeciwna do zamierzonej: pula z przewagą 1σ
(t ≈ 20) dawała p = 0,898, a pula, w której **każdy** wariant traci — p = 0,000.

Pełny raport regresyjny z dowodem czerwieni przed poprawką:
`reports/R1_regresja_spa.md`.

### Wpływ na wnioski W001–W013

**Żaden.** SPA nie zostało użyte w żadnym badaniu Gen1 ani w B00. Licznik prób
wynosi 0, żadna karta nie doszła do bramki, na której SPA działa. Osiem
werdyktów odrzucenia i wszystkie liczby w raportach pozostają identyczne.

Potwierdzenie maszynowe: warstwa `raporty` (18 znormalizowanych hashy
i 8 wyciągniętych metryk) oraz warstwa `rejestr` są w baseline bez zmian.

---

## v3 — R2: podpięcie kontroli ciągłości po rolowaniu

```
hash_danych  = cf16e23b…909d5a2c5   (BEZ ZMIAN)
hash_wynikow = 64c8bae3…c86de4e4  ->  eea80e16f7eee82397c20a178d5f8cd2dad2c67429249a82687ac2c4c56237ec
```

### Zmienione klucze — dokładnie trzy

| Klucz | Przyczyna |
|---|---|
| `raporty.hashe.data_quality_mnq.md` | nowa sekcja „Ciągłość serii po rolowaniu" |
| `raporty.hashe.data_quality_nq.md` | jw. |
| `raporty.hashe.data_quality_es.md` | jw. |

Warstwy `dane`, `silnik`, `metryki`, `walidacja` i `rejestr` — **identyczne**,
sprawdzone porównaniem struktur, nie tylko hasha. Osiem wyciągniętych metryk
raportowych bez zmian. Żaden inny raport nie zmienił hasha. `hash_danych`
bez zmian.

### Powód

`engine.roll.verify_continuity` i `engine.loader.describe` były napisane pod
PLAN 4.6 i **nigdy niewywołane** (audyt kodu, poz. R2). Podpięte do
`scripts/data_quality.py`. Dodano 8 testów `verify_continuity`
(`tests/test_roll_metrics.py::TestCiaglosc`).

### Wynik kontroli na trzech instrumentach

**Kontrola rozstrzygająca — niezmiennik arytmetyczny.** Offset back-adjustu
musi być stały w obrębie kontraktu; zmienny oznaczałby korektę liczoną per bar,
czyli że seria ciągła jest fikcją.

| Instrument | Kontraktów | Największy rozrzut offsetu | Kontraktów z niestałym offsetem | Werdykt |
|---|---|---|---|---|
| MNQ | 30 | 0,0000000000 | 0 | **PASS** |
| NQ | 30 | 0,0000000000 | 0 | **PASS** |
| ES | 30 | 0,0000000000 | 0 | **PASS** |

Odpowiedź jest **dokładnie zerowa** we wszystkich 90 kontraktach. Próg 1e−6 nie
został nawet napoczęty.

**Skok serii skorygowanej na granicach rolowania** (29 granic na instrument):

| Instrument | Największa nieciągłość | Data | Kontrakty | Skoków dodatnich | Średnia ze znakiem | t |
|---|---|---|---|---|---|---|
| MNQ | 354,25 pkt | 2026-06-15 | MNQM6 → MNQU6 | 15/29 | +4,17 pkt | +0,28 |
| NQ | 349,25 pkt | 2026-06-15 | NQM6 → NQU6 | 17/29 | +5,25 pkt | +0,34 |
| ES | 70,25 pkt | 2020-03-16 | ESH0 → ESM0 | 17/29 | −2,37 pkt | −0,63 |

Kontrola znaku jest tu kluczowa: rezyduum back-adjustu byłoby **systematyczne** —
miałoby jeden znak i średnią bliską pominiętemu spreadowi. Rozkład jest
symetryczny (15/29, 17/29, 17/29), a |t| ≤ 0,63 we wszystkich trzech
instrumentach. To wyklucza systematyczne rezyduum korekty.

### Ustalenie wymagające odnotowania: `verify_continuity` nie nadaje się na miarę

Funkcja zgłasza **17 z 29** granic dla MNQ, 18/29 dla NQ, 12/29 dla ES. To nie
jest wynik o danych, tylko o kryterium funkcji: warunek brzmi „skok ≥ |spread|",
a spread rolowania to kilkanaście–kilkadziesiąt punktów, więc każdy zwykły dzień
o ruchu 50+ punktów zostaje zgłoszony.

Skrajny przykład z tych danych: **2020-03-13, ruch 659 pkt w szczycie krachu
covidowego, opisany jako „back-adjust nie zadziałał" przy spreadzie −13,50 pkt.**

**Kryterium nie zostało zmienione**, żeby raport przeszedł — to byłoby
dostrajanie progu pod wynik. Ograniczenie jest jawne w raporcie, zabezpieczone
testem regresyjnym
(`test_ZNANE_OGRANICZENIE_duzy_ruch_rynku_daje_falszywy_alarm`) i pozostaje
otwartą pozycją do osobnej decyzji.

**Żadnych danych nie poprawiano.**

### Wpływ na wnioski W001–W013

**Żaden.** Kontrola jest kodem raportującym; nie dotyka danych, silnika ani
aparatu walidacyjnego.

---

## v4 — Etap 2.5: `verify_continuity` z bramki na diagnostykę

```
hash_danych  = cf16e23b…909d5a2c5   (BEZ ZMIAN)
hash_wynikow = eea80e16…c4c56237ec  ->  ae7b5c50bc9c2fc8733261127445ffe87912d51a378b1960a2f7c6e8bb4f59f6
```

### Zmienione klucze — dokładnie trzy

`raporty.hashe.data_quality_{mnq,nq,es}.md`.

Warstwy `dane`, `silnik`, `metryki`, `walidacja` i `rejestr` — **identyczne**,
sprawdzone porównaniem struktur. Osiem metryk raportowych bez zmian. Żaden inny
raport nie zmienił hasha. `hash_danych` bez zmian.

### Powód

Kryterium „skok ≥ |spread|" nie może pełnić funkcji bramki PASS/FAIL dla
poprawności back-adjustu, bo jest **nieidentyfikowalne**: zwykły ruch rynku
między sąsiednimi sesjami bywa wielokrotnie większy od spreadu kontraktowego.
Rozstrzygnięte empirycznie — heurystyka zgłasza 17/29 granic MNQ, 18/29 NQ,
12/29 ES przy **dokładnie zerowym** rozrzucie offsetu we wszystkich
90 kontraktach.

Problem leży w konstrukcji kryterium, nie w wartości progu, więc **progu nie
zmieniono**. Zmieniono wyłącznie **etykietę i rolę wyniku**:

| | Rola | Status |
|---|---|---|
| niezmiennik stałości offsetu | **autorytatywna** | PASS / FAIL |
| heurystyka skoków na granicach | **diagnostyczna** | DIAGNOSTIC / WARNING / INCONCLUSIVE — nigdy automatyczny FAIL |

Komunikat funkcji nie twierdzi już, że „back-adjust nie zadziałał"; mówi
o dużym skoku i wprost zaznacza, że heurystyka nie rozróżnia ruchu rynku od
błędu korekty.

Bieżący odczyt: **PASS** (z niezmiennika) · diagnostyka **INCONCLUSIVE** na
wszystkich trzech instrumentach.

### Zabezpieczenie przed zmianą kryterium przy okazji zmiany etykiety

Nowy test `test_wartosci_diagnostyczne_nie_zmienily_sie_po_przeetykietowaniu`
sprawdza na czterech rolowaniach o znanym z góry werdykcie (ruch 10 / 50 / 150 /
0 przy spreadzie 50), że zgłaszany jest **dokładnie ten sam zbiór granic** co
przed przeetykietowaniem. Wartości diagnostyczne zachowane, zmieniło się
wyłącznie nazewnictwo.

### Wpływ na wnioski W001–W013

**Żaden.** Zmiana dotyczy etykiety w kodzie raportującym.

---

## v5 — Etap 2.5: empiryczna weryfikacja założenia A3

```
hash_danych  = cf16e23b…909d5a2c5   (BEZ ZMIAN)
hash_wynikow = ae7b5c50…bb4f59f6  ->  e599c0b70d289b009a97bf36dfdae219f2baa0c659c1a4cf3f0be58712e16930
```

### Zmienione klucze — jeden, i jest to NOWY plik

`raporty.hashe.A3_halt_weryfikacja.md` — nowy wpis. **Żaden z 19
wcześniejszych hashy raportów się nie zmienił**, żadna z 8 metryk również.
Warstwy `dane`, `silnik`, `metryki`, `walidacja` i `rejestr` — identyczne,
sprawdzone porównaniem struktur.

### Powód

A3 (halt CME 15:15–15:30 CT do 27.06.2021) było jedynym założeniem
kalendarzowym przyjętym z dokumentacji bez sprawdzenia na własnych danych.
Zweryfikowane na MNQ, NQ i ES przez `scripts/verify_a3_halt.py`.

### Wynik

Gęstość okna 16:15–16:30 ET (udział wypełnionych minut z 15 możliwych na dzień):

| Instrument | Przed 27.06.2021 | Po 27.06.2021 | Sąsiedztwo 16:00–16:15 przed |
|---|---|---|---|
| MNQ | **0,05%** | 96,21% | 96,2% |
| NQ | **0,05%** | 96,21% | 96,3% |
| ES | **0,07%** | 96,21% | 96,3% |

Kryterium to **kontrast, nie sama pustka**. Bary M1 nie odróżniają formalnego
zamknięcia od braku transakcji (założenie B4), więc puste okno samo w sobie
niczego by nie dowodziło. Rozstrzyga zestawienie z sąsiedztwem tych samych dni.

Wszystkie wyjątki przed granicą (4 dni MNQ i NQ, 6 dni ES) leżą na **krawędzi
okna** — minuta 16:15 albo 16:29, nigdy w środku. 50 dni po granicy bez barów
to święta amerykańskie.

**Ograniczenie dowodowe zachowane w raporcie:** to nie dowód formalnego
zamknięcia, tylko braku obrotu nieodróżnialnego od niego przy rozdzielczości
minutowej. Dla projektu bez różnicy — silnik i tak nie wykona zlecenia bez
wolumenu.

Granica zabezpieczona testem
`tests/test_sessions.py::test_granica_A3_zgodna_z_danymi`.

### Wpływ na wnioski W001–W013

**Żaden.** Kontrola danych, nie badanie P&L. Zero zużytych prób.
