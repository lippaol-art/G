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

---

## v6 — D5 Etap 1: pierwszy zakup danych `trades`

```
hash_danych  = cf16e23b…909d5a2c5  ->  e86a2ace5ec1c3a2b253b38a7763fd3ad73126be846051feba3886db24308519
hash_wynikow = e599c0b7…12e16930  ->  75b6d617de2db3862da58753b9bc8b2c59fb2f4560451bd85b3c3e9ca469e461
```

**Pierwsza zmiana `hash_danych` w historii projektu** — i dokładnie po to
istnieje osobny hash danych. Nabyliśmy nowe dane; nic istniejącego się nie
zmieniło.

### Zmienione klucze — dwa, oba NOWE

| Klucz | Rodzaj |
|---|---|
| `dane.manifesty.manifest_trades.md` | **nowy wpis** |
| `raporty.hashe.D5_etap1_kontrole.md` | **nowy wpis** |

**Zero kluczy istniejących uległo zmianie** — sprawdzone porównaniem struktur,
nie tylko hasha:

| Warstwa / grupa | Zmienione | Nowe |
|---|---|---|
| `dane.parquet` (13 zbiorów) | brak | brak |
| `dane.csv` (3 kalendarze) | brak | brak |
| `dane.manifesty` | brak | `manifest_trades.md` |
| `raporty.hashe` (20 raportów) | brak | `D5_etap1_kontrole.md` |
| `raporty.metryki` (8 metryk) | identyczne | — |
| `silnik`, `metryki`, `walidacja`, `rejestr` | identyczne | — |

### Powód

Zakup jednego dnia `trades` MNQ (D5 Etap 1) i wykonanie dziewięciu zamrożonych
kontroli. Specyfikacja zamrożona **przed** zakupem (`41d3eee`), korekta budżetu
(`953b5ec`), zakup i kontrole po niej.

| | |
|---|---|
| Sesja | `2026-07-30`, kontrakt `MNQU6` |
| Rekordów | 1 696 891 |
| Koszt | **2,1240 USD** (limit 2,15) |
| SHA-256 pliku | `dfee7684c7bdce99272d91567752d7220291896bd8ebf694c281b6efab4df172` |

Plik `.dbn.zst` nie jest commitowany — `data/raw/` jest w `.gitignore`.
Manifest z parametrami odtworzenia: `data/manifest_trades.md`.

### Werdykt kontroli: `D5-A GO`

`side != NONE` = **99,9999%** przy progu 95%; kompletność ≥ 99,998% w każdym
segmencie sesji.

### Ustalenie uboczne o znaczeniu dla całego projektu

Rekonstrukcja `ohlcv-1m` z surowych transakcji dała **zgodność doskonałą:
0 niezgodności na 1 380 barach** w open, high, low, close i wolumenie —
pod warunkiem agregacji po **`ts_recv`**, nie `ts_event` (ten drugi daje
8 / 6 / 20 niezgodności przez przesunięcia na granicy minuty).

To domyka zaległość z audytu 4 (poprawka A4-10): niezależna kontrola jakości
barów przez rekonstrukcję z transakcji, zaplanowana w Etapie 1 projektu
i nigdy niewykonana.

### Wpływ na wnioski W001–W013

**Żaden.** Kontrola techniczna, zero policzonych zwrotów, zero P&L.
**Licznik prób: 0.**

---

## v7 — D5-B: wynik testu identyfikowalności (werdykt `GO`)

```
hash_wynikow  75b6d617de2db3862da58753b9bc8b2c59fb2f4560451bd85b3c3e9ca469e461
           -> 2735b8f76023ebc8645b0d7afdb8c70776507eed67d81edff13910ae60cb65c2
hash_danych   BEZ ZMIANY
```

**Zmienione klucze — dokładnie jeden:**

| Klucz | Zmiana |
|---|---|
| `raporty.hashe.D5_etap2_wyniki.md` | NOWY |

`hash_danych` bez zmiany: próbka `trades` leży w `data/raw/` (poza
`.gitignore`), a baseline haszuje `data/clean/`. Żaden plik `clean/` nie
został dotknięty.

**Powód:** zakończenie Etapu 2 kierunku D5 — test identyfikowalności
nierównowagi zdarzeń agresora względem równoczesnego momentum ceny.
Werdykt `D5-B GO`, wszystkie sześć warunków z zamrożonej specyfikacji
spełnione. Szczegóły: `reports/D5_etap2_wyniki.md`.

**Dwa błędy własne wykryte i naprawione przed wydaniem werdyktu:**

1. **Przepełnienie typu bez znaku** w różnicach `n_buy − n_sell`,
   `f_buy − f_sell`, `v_buy − v_sell`. Pierwszy przebieg dał `NO-GO`
   z koncentracją 58,50% zmienności na jednej sesji — wartość niewiarygodna,
   która doprowadziła do diagnozy. `I_count` jest z konstrukcji w [−1, +1],
   a przyjmował wartości rzędu 1,5 mln. **Fałszywy `NO-GO` nie został nigdzie
   zaraportowany jako wynik.** Naprawa: rzutowanie na `Int64` w miejscu
   agregacji + strażnik zakresu przerywający obliczenia.
2. **Dwie zaległości wobec zamrożonej specyfikacji**: nieliczone warunki 4 i 5
   z §8 oraz brak wykluczania grup niejednoznacznych z §3. Oba uzupełnione;
   oba mogą werdykt wyłącznie zaostrzyć.

**Wpływ na wnioski W001–W013: żaden.** Zero policzonych zwrotów przyszłych,
zero P&L, zero backtestu. **Licznik prób: 0.** H017 nie powstaje.

---

## v8 — raport zamknięcia dwóch defektów technicznych

```
hash_wynikow  2735b8f76023ebc8645b0d7afdb8c70776507eed67d81edff13910ae60cb65c2
           -> 6fed5171c876bbc5ef1753afda9677ae77405e2dbd18aeb06fdbac24ecd6d3d2
hash_danych   BEZ ZMIANY
```

**Zmienione klucze — dokładnie jeden:**

| Klucz | Zmiana |
|---|---|
| `raporty.hashe.audyt_typy_i_kalendarz.md` | NOWY |

**Powód:** zamknięcie dwóch usterek wskazanych przed H017 — martwej flagi
`short_day` i powtarzającego się przepełnienia przy odejmowaniu kolumn bez
znaku. Szczegóły: `reports/audyt_typy_i_kalendarz.md`.

**`hash_danych` celowo bez zmiany.** Naprawa kalendarza zmienia zawartość
`data/clean/` (`short_day`: 72 206 barów `False→True`; `gap_kind`: 192 bary
`anomaly→expected` na MNQ, analogicznie NQ i ES), ale **przebudowa nie została
wykonana**. Wpływ jest zmierzony na kopii i przedstawiony właścicielowi
projektu do decyzji, bo zmienia próbkę i raport `data_quality.md`. Kod jest
naprawiony, dane pozostają w poprzednim stanie — stan pośredni świadomy
i odnotowany.

**Wpływ na wnioski W001–W013: żaden.** Żaden moduł badawczy nie czyta
`short_day`; audyt typów nie znalazł ani jednego niezabezpieczonego
odejmowania, więc żaden opublikowany wynik nie był nim dotknięty.
**Licznik prób: 0.**

---

## v9 — kontrolowana przebudowa `data/clean/` po naprawie kalendarza CME

**Pierwsza zmiana `hash_danych` wynikająca z naprawy kodu, nie z zakupu danych.**

```
hash_danych   e86a2ace5ec1c3a2b253b38a7763fd3ad73126be846051feba3886db24308519
           -> 595a3ab7e31b6fda362521bd786c2f1fa8cc998abf3c74d3dd43ebe4f2f34c36

hash_wynikow  6fed5171c876bbc5ef1753afda9677ae77405e2dbd18aeb06fdbac24ecd6d3d2
           -> 6fbed6d1262c53bd5ceca590c990294f89c5249557d6f2fca7ab8f7c636b0d8a
```

### Powód

Kod znał poprawny kalendarz CME (commit `a508d2d`), ale zapisane parquety nadal
zawierały martwą flagę `short_day`. Ten sam commit dawałby różne znaczenie
zależnie od tego, czy ktoś odbudował dane — niespójność, którą trzeba domknąć
przed H017.

### Zmienione pliki danych

| Symbol | Wierszy | `short_day` `False→True` | Dni | `gap_kind` `anomaly→expected` | SHA-256 stary | SHA-256 nowy |
|---|---|---|---|---|---|---|
| MNQ | 2 551 265 | **72 206** | 64 | **192** | `7b9be5aa8cccb1e0…` | `d010b740247626fe…` |
| NQ | 2 573 758 | **72 494** | 64 | **113** | `fd2d18d5c9acd5f6…` | `9e207e4faa10bedf…` |
| ES | 2 573 653 | **72 383** | 64 | **178** | `52c320b03562797f…` | `e758573956df8f1e…` |

Kierunek zmian jest **jednostronny w obu kolumnach**: `short_day` wyłącznie
`False→True`, `gap_kind` wyłącznie `anomaly→expected`. Skrypt przebudowy
przerywa, gdy pojawi się kierunek przeciwny.

### Potwierdzenie zerowej różnicy — 15 kolumn zabronionych

`ts_utc`, `open`, `high`, `low`, `close`, `volume`, `contract`, `trade_date`,
`segment`, `px_raw`, `px_adj`, `halt_window`, `days_to_roll`, `dst_transition`,
`data_condition` — **0 różnic w każdej, w każdym z trzech instrumentów.**
Liczba wierszy bez zmian. Zestaw kolumn bez zmian.

Kontrola jest **jawną listą**, nie regułą „wszystko poza dozwolonymi", żeby
dopisanie kolumny do schematu nie osunęło jej po cichu.
Skrypt: `scripts/rebuild_clean.py`, raport: `reports/przebudowa_clean.json`.

### Zmienione raporty — dokładnie trzy

| Raport | Zmiana |
|---|---|
| `data_quality_mnq.md` | `anomaly` 3 304 → 3 112, `expected` 2 322 → 2 514 |
| `data_quality_nq.md` | analogicznie, −113 anomalii |
| `data_quality_es.md` | analogicznie, −178 anomalii |

Suma `anomaly + expected` bez zmian — luki nie zniknęły, zostały **poprawnie
zaklasyfikowane** jako wynikające z oficjalnego kalendarza.

### Potwierdzenie identyczności wyników Gen1

Dowód **empiryczny**, nie z hashy plików statycznych: trzy badania Gen1
przeliczono na przebudowanych danych i porównano z poprzednimi wersjami.

| Badanie | Linii różniących się poza stopką z datą |
|---|---|
| `W001_overnight_drift` | **0** |
| `W004_partia1_preflight` | **0** |
| `W010_partia3_preflight` | **0** |

Jedyną różnicą była data generacji, więc oryginały przywrócono — regeneracja
samej stopki dodałaby do baseline'u szum bez treści.

Dodatkowo: **bramka silnika na realnych danych** (PLAN rozdz. 5.6 — zerowa
przewaga, znany efekt, symetria, determinizm) przechodzi na przebudowanych
danych. Metryki silnika, karty hipotez i werdykty: **bez zmian**.

### Rozbieżności baseline'u: 11 zmian, 0 usuniętych, 0 nowych

6 wpisów parquetów (hash + rozmiar × 3), `hash_danych`, `hash_wynikow`
i 3 raporty jakości. **Ani jeden wpis `metryki.*` ani `silnik.*` nie drgnął.**

**Licznik prób: 0.** P&L nie mierzony. H017 nie powstaje.

---

## v10 — D5-B zdegradowane do `INCONCLUSIVE` po odpowiedzi Databento

```
hash_wynikow  6fbed6d1262c53bd5ceca590c990294f89c5249557d6f2fca7ab8f7c636b0d8a
           -> 0c74df56bd8ed810cce3a0d249b7f467dcc6e9747fe62b0a9b9c7bbe0fbe0149
hash_danych   BEZ ZMIANY
```

**Zmienione klucze — dokładnie jeden:**

| Klucz | Zmiana |
|---|---|
| `raporty.hashe.D5_etap2_wyniki.md` | blok zastąpienia werdyktu na początku |

**Powód:** Databento potwierdziło (2026-08-04, 11:00 UTC), że `sequence` jest
numerem sekwencyjnym wiadomości CME i **nie identyfikuje** pojedynczego
zdarzenia dopasowania — jedna wiadomość może zawierać wiele Trade Summaries,
także po przeciwnych stronach.

**Obliczenia D5-B nie są numerycznie błędne.** Błędna była interpretacja
głównej zmiennej A jako liczby zdarzeń agresora. Dlatego zmieniony jest
**status**, a nie liczby:

```
D5-B GO  ->  D5-B INCONCLUSIVE — niewłaściwa jednostka pomiaru
```

**Raport nie został usunięty ani przepisany.** Blok zastąpienia dodany na
początku, oryginalna treść w całości poniżej. `reports/D5_etap2_wyniki.json`
celowo **bez zmian** — to zapis obliczenia, które pozostaje poprawne
i odtwarzalne; ostrzeżenie o nieaktualnym werdykcie trafiło do docstringa
`scripts/audit_d5_etap2.py`, żeby ponowne uruchomienie nie było czytane jako
aktualny status.

**Potwierdzone przy okazji i pozostające w mocy:** `ts_recv` jako podstawa
agregacji barów GLBX.MDP3 — **oficjalnie, przez dostawcę**. Cała decyzja
o granicach okien 60-sekundowych była prawidłowa.

**Wpływ na wnioski W001–W012: żaden.** Dodane W013 (martwa flaga) i W014
(zgodność empiryczna nie zastępuje semantyki protokołu) oraz reguła R9
(zwięzłość zapytań do wsparcia). Uzupełnione R4 i R5, które cytowałem
w opisie PR, zanim trafiły do rejestru.

**Licznik prób: 0.** P&L nie mierzony. H017 nie powstaje.

---

## v11 — D5-C `GO`: kanoniczna jednostka zdarzenia agresora znaleziona

```
hash_wynikow  0c74df56bd8ed810cce3a0d249b7f467dcc6e9747fe62b0a9b9c7bbe0fbe0149
           -> 08af84e30d5d0d4fb9e1b2311883fbd16bef1b0515bead713b343a5421a4189f
hash_danych   BEZ ZMIANY
```

**Zmienione klucze — dokładnie jeden:**

| Klucz | Zmiana |
|---|---|
| `raporty.hashe.D5_etap3_wyniki.md` | NOWY |

`hash_danych` bez zmiany: próbka `mbo` leży w `data/raw/` (poza `.gitignore`),
a baseline haszuje `data/clean/`. Żaden plik `clean/` nie został dotknięty.

**Powód:** audyt jednodniowej próbki MBO (2026-07-30, RTH). Werdykt `D5-C GO`.
`order_id` agresora obecny na **100,00%** rekordów `Trade`, **0 agresorów po
obu stronach** wobec 732 dwustronnych par `(ts_event, sequence)` z D5-B.
Suma pasywnych `Fill` == rozmiar `Trade` w **100,000%** przypadków.
Rekonstrukcja `trades` z MBO dokładna co do rekordu i sztuki.

**Koszt:** 3,5961 USD przy zamrożonym limicie 4,00 USD.

**Wpływ na wnioski W001–W014: żaden.** Zero policzonych zwrotów, zero P&L,
zero backtestu. **Licznik prób: 0.** H017 nie powstaje.

---

## v12 — D5-C: zamknięcie mianownika podziału zdarzeń

```
hash_wynikow  08af84e30d5d0d4fb9e1b2311883fbd16bef1b0515bead713b343a5421a4189f
           -> cc56236b1b0c78f4500210e7d3d7db5fe7bdcdde967fcbb1ec88baa5cbc70140
hash_danych   BEZ ZMIANY
```

**Zmienione klucze — dokładnie jeden:**

| Klucz | Zmiana |
|---|---|
| `raporty.hashe.D5_etap3_wyniki.md` | dodana sekcja Q6b — pełny podział zdarzeń |

**Powód:** niezmiennik Q6 dotyczył 767 588 zdarzeń, a zdarzeń z transakcją jest
842 757. Różnica 75 169 była niewyjaśniona — metryka bez zapisanego mianownika.

Podział rozłączny i wyczerpujący: `1T_pasywne_zgodne` **767 588** +
`wieleT_zgodne` **75 169** + pięć pozostałych kategorii **0** = **842 757**,
**niewyjaśnionych 0**.

**Poprawka reguły przypisania.** Pierwsze przeliczenie dało 8 niezgodności.
Po obejrzeniu wszystkich ośmiu: zlecenie będące agresorem w jednej transakcji
potrafi być stroną **pasywną** w drugiej, w tym samym zdarzeniu `F_LAST`.
Rola agresora jest więc własnością **pojedynczej transakcji**, nie zlecenia
w oknie. Po zmianie przypisania na per-`Trade` niezmiennik trzyma się
w **100,0000%** — 842 757 z 842 757.

Trzecia z rzędu „niezgodność danych", która okazała się wadą reguły zliczania.
Zapisane jako wniosek **W015**.

**Wpływ na wnioski W001–W014: żaden.** Zero policzonych zwrotów, zero P&L.
**Licznik prób: 0.** H017 nie powstaje.
