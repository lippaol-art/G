# HANDOFF — wznowienie pracy nad Projektem G

**Ten dokument jest napisany dla sesji, która nie widziała poprzedniej rozmowy.**
Kontener jest efemeryczny, więc wszystko potrzebne do kontynuacji jest tutaj i w repo.

Data: 08.08.2026 · Branch: `claude/financial-market-strategy-8mb1y1` · PR #4

> **Reguła utrzymania tego pliku.** HANDOFF aktualizuje się w TYM SAMYM commicie, który
> zmienia stan projektu. **Nieaktualny HANDOFF to defekt P1, jak czerwony test** — nie
> „dług dokumentacyjny" do nadrobienia później. Ten plik przez pięć dni twierdził, że
> Etap 1 jest zablokowany przez politykę sieciową, w czasie gdy dane były już w repozytorium,
> a Gen1 zamknięta. Świeża sesja zaczyna od niego i poszłaby „odblokowywać" rozwiązany
> problem albo powtórzyć zamknięte badanie.

**Podział ról między agentami: [`docs/PROTOKOL_WSPOLPRACY.md`](docs/PROTOKOL_WSPOLPRACY.md).**
Przeczytaj go, zanim wystawisz jakąkolwiek ocenę własnej pracy — Wykonawca nie wystawia
sobie werdyktu końcowego.

---

## 1. Stan projektu w dziesięciu liniach

Budujemy laboratorium badawcze do znalezienia oryginalnej strategii na MNQ (Micro E-mini
Nasdaq-100). Dokument założycielski `docs/PLAN.pdf` (49 stron, wersja 1.1 po czterech
niezależnych audytach zewnętrznych) jest **jedynym źródłem prawdy** — kod ma go realizować,
a nie odwrotnie.

Gotowe: fundament repo, silnik backtestowy, komplet aparatu walidacyjnego, strażnicy
niezmienników, CI, golden baseline. **543 funkcji testowych (609 przypadków po parametryzacji), pokrycie 92%, ruff i mypy czyste.**
Liczbę pilnuje `tests/test_guards.py::test_handoff_podaje_aktualna_liczbe_testow` —
bez tego rotowała dwa razy w ciągu doby, co jest dokładnie tym defektem, przed
którym ostrzega reguła na górze tego pliku.
Dane rynkowe są w repozytorium (MNQ/NQ/ES, bary M1, 2019–2026). Bramka silnika z PLAN
rozdz. 5.6 zaliczona na pełnych 2 551 265 barach.

Zamknięte: **Gen1 — wszystkie 16 hipotez odrzucone w pre-flightach.** Wniosek przekrojowy:
bary M1 przewidują amplitudę, nie kierunek. **Licznik prób nadal wynosi 0** — ani jedna
karta nie doszła do backtestu, bo żadna nie przeszła taniej bramki wstępnej. To jest wynik
poprawny, nie porażka procesu.

Trwa: **D5 — audyt wykonalności mechanizmu przepływu agresywnego** na danych MBO.
Stan i najbliższy krok: sekcja 4.

---

## 2. Sieć i klucz API — stan faktyczny

**Blokera sieciowego nie ma.** `hist.databento.com` odpowiada 200. Historyczny opis blokady
z 31.07.2026 usunięty, bo opisywał stan nieistniejący. Weryfikacja jedną komendą:

```bash
curl -sS --max-time 20 -o /dev/null -w "%{http_code}\n" \
  -u "$DATABENTO_API_KEY:" https://hist.databento.com/v0/metadata.list_datasets
```

Gdyby kiedykolwiek wróciło 403/407: to **odmowa polityki organizacji**, nie awaria.
`/root/.ccr/README.md` mówi wprost — zgłosić, nie obchodzić. Nie ponawiać w pętli, nie szukać
innego hosta, nie wyłączać weryfikacji TLS.

**Klucz API: rotacja nadal zalecana, świadomie odłożona przez właściciela.** Pierwszy klucz
przeszedł przez transkrypt rozmowy. Ryzyko jest ograniczone (odczyt danych, koszt limitowany
kredytami), więc nie jest to bloker — ale rekomendacja pozostaje otwarta i nie wolno jej
uznać za zamkniętą bez decyzji właściciela.

Niezmiennie obowiązuje:

1. Klucz czytany **wyłącznie** z `os.environ["DATABENTO_API_KEY"]`. Nigdzie nie ma wartości
   domyślnej i nie wolno jej dodawać.
2. `.gitignore` blokuje `.env*`, `data/raw/`, `*.dbn`.
3. Strażnik `tests/test_guards.py::TestSecrets` skanuje repo pod kątem wzorców kluczy,
   a CI robi to samo na **całej historii gita** — łącznie z komunikatami commitów.

---

## 3. Gdzie leżą dane

| Co | Gdzie | Uwaga |
|---|---|---|
| Bary M1 MNQ/NQ/ES, kontrakt ciągły | `data/clean/*.parquet` | **w repozytorium**, wersjonowane |
| Kalendarze: wyniki, makro, warstwa K6 | `data/clean/*.csv`, `data/clean/k6/` | w repozytorium |
| Surowe MBO / trades (`*.dbn.zst`) | **poza repozytorium** | `.gitignore`; ścieżkę wskazuje `PROJECT_G_DATA_ROOT` |
| Manifesty zakupów surowych | `PROJECT_G_DATA_ROOT/manifests/` | poza repo, bo dotyczą plików spoza repo |

`engine/paths.py` jest jedynym miejscem, które rozstrzyga te ścieżki. `raw_dir()` honoruje
`PROJECT_G_DATA_ROOT`; `clean_dir()` **zawsze** zostaje w repo, bo od niego zależy golden
baseline. Konfiguracja maszyny lokalnej: `docs/URUCHOMIENIE_LOKALNE.md`.

### Maszyna właściciela (Windows)

| Rola | Ścieżka |
|---|---|
| Klon repozytorium | `C:\ProjektG` |
| Dane surowe poza repo | `C:\ProjektG_dane` → `PROJECT_G_DATA_ROOT` |

**Rozstrzyga zmienna środowiskowa, nie ta tabela.** Jeżeli `PROJECT_G_DATA_ROOT` wskazuje
gdzie indziej, prawdą jest zmienna — tabela jest tylko zapisem przyjętej konwencji.
Sprawdzenie: `python -c "from engine.paths import raw_dir; print(raw_dir())"`.

### Budżet

Każdy wydany dolar jest w `data/KOSZTY.md`, łącznie z ponownymi naliczeniami — duplikacja ma
tam własną pozycję i nie wolno jej chować w sumie zbiorczej. **Ten plik jest źródłem prawdy
o budżecie; nie przepisuj kwot tutaj**, bo dwie kopie liczby rozjadą się przy pierwszym
zakupie. Stan i pozycje planowane: `data/KOSZTY.md` §2–3.

---

## 4. Najbliższy krok: D5-B2

### Skąd się wziął ten etap

Gen1 wyczerpała to, co da się zobaczyć w barach M1. D5 pyta o mechanizm głębszy: czy
**przepływ agresywny** (kto inicjuje transakcje) niesie informację o przyszłości, a nie tylko
o sobie samym. To wymaga danych MBO — drogich, więc kupowanych etapami, z limitem zamrożonym
w commicie **sprzed** zakupu.

### Przebyta droga — i dlaczego warto ją znać

| Etap | Wynik | Lekcja |
|---|---|---|
| D5-A | GO | mechanizm w ogóle mierzalny |
| D5-B (schemat `trades`) | ~~GO~~ → **INCONCLUSIVE** | obliczenia były poprawne, **interpretacja nie**: `sequence` to numer wiadomości CME, nie identyfikator zdarzenia dopasowania. Potwierdzone oficjalnie przez Databento (`docs/D5_PYTANIE_DATABENTO.md`). Werdykt cofnięty, historia nieusunięta. |
| D5-C (jeden dzień MBO) | **GO** | znaleziona kanoniczna jednostka: **akcja agresywna per Trade**, po `order_id`. 842 757 zdarzeń rozliczonych, **0 niewyjaśnionych**. |
| Dry run D5-B2 | **8/8 niezmienników** | rekonstrukcja działa: 903 116 akcji na 2026-07-30 |
| Test 1 i 2 na maszynie lokalnej | **zgodne co do liczby** | laboratorium jest przenośne; trzy błędy cross-platform wyszły dopiero tam |

**Uwaga o F_LAST, która kosztowała cofnięcie werdyktu raz i nie może kosztować drugi.**
Koperta `F_LAST` **nie jest** jednostką obserwacji — 2,4% kopert zawiera co najmniej dwóch
agresorów. Jednostką jest akcja agresywna przypisana **per Trade**. Reguły są zamrożone
w `docs/D5_ETAP4_SPEC.md` §1 i zaimplementowane w `engine/mbo_events.py`.

### Co zrobić teraz — dokładnie

```powershell
git pull --ff-only

# 1. Wycena bez zakupu. Metadane są darmowe.
python scripts/fetch_d5b2_month.py --wycena

# 2. Zakup, dopiero gdy wycena zmieści się w limicie 82,00 USD
python scripts/fetch_d5b2_month.py
```

> ## ⛔ ZAKUP WSTRZYMANY — rozjazd metadanych, przyczyna NIEUSTALONA
>
> **08.08.2026: te same zamrożone zapytania dały inne liczby rekordów niż przy
> poprzednim przebiegu. Wszystkie 22 sesje w górę o 1,67–3,06% (mediana +2,66%),
> koszt 78,6044 → 80,6729 USD.** Zapytanie identyczne (warunek 3 potwierdził).
>
> **Pierwsza diagnoza („dostawca zrewidował dane") została ODRZUCONA** jego
> własnym `get_dataset_condition`: żadna sesja lipca nie była modyfikowana
> w sierpniu. Obowiązująca hipoteza — wcześniejsze wyceny mogły być **zaniżone**,
> bo powstały w czasie awarii 503/504. Jeśli tak, **pobrane pliki mogą być
> niepełne**.
>
> Skutek praktyczny: każdy **już opłacony** plik wygląda na niekompletny, więc
> skrypt zaproponował zakup całego miesiąca **drugi raz**. Zatrzymał go
> warunek 4; od tej pory blokuje to wprost **warunek 8** (furtka:
> `--akceptuj-rozjazd`, **nie używać przed odpowiedzią dostawcy**).
>
> Analiza, odrzucone hipotezy z rachunkiem i gotowy mail:
> **[`docs/D5_DRYF_METADANYCH.md`](docs/D5_DRYF_METADANYCH.md)**.
>
> **Najbliższy krok to `python scripts/diag_dryf.py`** — lokalnie, bez sieci,
> za darmo; rozstrzyga, czy pobrane pliki obejmują całe okno RTH.
>
> **Nie kupuj i nie kasuj niczego.** Stan: 4 z 22 sesji pobrane, **12,7304 USD
> potwierdzone wycenami**, do ~7,49 USD niepotwierdzone (przerwane 07-06 i 07-07).

Wycena z przebiegu, który pobrał sesje 07-01…07-06: **78,6044 USD za 22 sesje**
wobec limitu 82,00; nagłówek pokazał **75,0083 USD** za 21 sesji. Wycena z 08.08 to już
**80,6729 USD** — do zamrożonego limitu zostaje **1,3271 USD**.

**2026-07-30 musi zostać pominięta** — inaczej naliczy się trzeci raz. Skrypt ma na to
warunek 4 (twarda odmowa, gdy ta sesja trafi na listę zakupową) i weryfikuje plik nie tylko
liczbą rekordów, ale **SHA-256 wobec `data/manifest_d5c.json`**. Zgodna liczba rekordów
mówi tylko, że plik ma właściwą długość; SHA mówi, że to ten sam plik, na którym policzono
audyt Etapu 3.

**Po błędzie pobierania skrypt NIE ponawia automatycznie i to jest celowe.** Pobieranie jest
płatne i tworzy plik; ślepe ponowienie grozi podwójnym naliczeniem i cichym zostawieniem
obciętej sesji, która parsuje się bez błędu.

> **Wznowienie NIE jest darmowe dla sesji przerwanej w locie.** Sesje już **kompletne**
> są pomijane bez kosztu — ale sesja, której pobieranie przerwano, zostanie naliczona
> ponownie, bo Databento liczy za zrealizowane zapytanie, nie za odebrane bajty.
> Precedens: D5-B, sesja 2026-07-07, pozycja „duplikacja" w `data/KOSZTY.md`.
> Nie przerywaj pobierania bez powodu.

Po zakupie: kopia zapasowa surowego MBO na drugi dysk. Odtworzenie kosztuje ~78 USD,
skopiowanie kosztuje nic.

### Potem: bramka GO/NO-GO

Rekonstrukcja akcji sesja po sesji → okna 60-sekundowe po `ts_recv` → model z **sześcioma
progami z §8 specyfikacji, zamrożonymi przed zobaczeniem wyniku**. Wynik jest naprawdę
nieznany. Przy NO-GO licznik prób zostaje na zerze i to też jest wynik.

---

## 5. Bramka silnika — ✅ ZALICZONA 01.08.2026

**Zanim uruchomisz jakiekolwiek badanie**, silnik musi przejść testy z `docs/PLAN.pdf`
rozdz. 5.6. Niesprawdzony silnik produkuje śmieci z dokładnością do sześciu miejsc
po przecinku.

**Status: GO.** Cztery testy zaliczone na pełnych 2 551 265 barach MNQ
(2019-05-05 → 2026-07-30). Kod: `tests/test_engine_on_real_data.py`.
Liczby: `reports/engine_gate.md` (odtworzenie: `python3 scripts/engine_gate_report.py`).

| Test | Oczekiwany wynik | Co oznacza porażka | Wynik 01.08.2026 |
|------|------------------|--------------------|------------------|
| **Zerowa przewaga** — losowe wejścia, losowy SL/TP | wynik ≈ −(koszty × liczba transakcji), rozkład symetryczny przed kosztami | przeciek informacji w silniku | **t = −2.21** na 11 494 losowych transakcjach przed kosztami (próg \|t\| < 3.0); żaden z 5 seedów nie wyszedł na plus |
| **Znany efekt** — kup na close RTH / sprzedaj na open vs odwrotnie | odtworzenie znanej asymetrii overnight/intraday co do znaku i rzędu wielkości | silnik źle mierzy — to linijka, nie strategia | overnight **+13 193 pkt** (t = 2.20) vs intraday **+3 956 pkt** (t = 0.51); noc = **76.9%** ruchu |
| **Symetria** — odwrócenie long↔short na strategii losowej | wynik lustrzany przed kosztami | błąd w obsłudze jednej ze stron | rozjazd **dokładnie 0.0 USD** na 1 980 transakcjach |
| **Determinizm** — dwa przebiegi z tym samym ziarnem | wyniki bitowo identyczne | nieziarnowana losowość gdzieś w ścieżce | identyczny SHA-256 listy transakcji; inne ziarno → inny wynik (kontrola) |

**Uwaga o ujemnym odchyleniu w teście zerowej przewagi.** Wynik lekko ujemny jest
POŻĄDANY i nie wolno go „naprawiać". Rozbicie w `reports/engine_gate.md` pokazuje
źródła: 0.9% transakcji wychodzi jako `stop_gap` (open bara już poza stopem — realny
koszt luki, tabela 5.4), a limit wymaga przebicia o tick, gdy stop wyzwala samo
dotknięcie. Dodatnie t byłoby alarmem; ujemne o tej wielkości jest projektem.

---

## 6. Golden baseline — kontrola, której nie ma w CI

`golden/baseline.json` (obecnie **v14**) zamraża wyniki liczbowe projektu. CI go nie
uruchamia, bo w CI nie ma danych rynkowych — jest to więc jedyna kontrola wychwytująca
**niezamierzoną zmianę wyników po refaktorze**, i działa tylko lokalnie:

```bash
bash scripts/check_all.sh          # pełna bramka, w tym baseline
bash scripts/check_all.sh --szybko # bez bramki 5.6 i bez baseline
```

`scripts/check_all.sh` jest kanoniczną bramką i **musi odpowiadać `.github/workflows/ci.yml`
krok w krok**. Powstał po tym, jak push z błędami mypy przeszedł lokalnie, bo uruchomiłem
ruff i testy, a mypy pominąłem. Każda zmiana w workflow wymaga zmiany tam — i odwrotnie.

Historia zmian baseline'u wraz z uzasadnieniem każdej: `golden/ZMIANY.md`. Baseline ma
rozdzielone `hash_danych` i `hash_wynikow`, żeby zmiana danych nie maskowała zmiany logiki.

---

## 7. Zasady, których nie wolno naruszyć

1. **Limit 10 wariantów na hipotezę.** Nie preferencja stylistyczna, tylko wynik tabeli
   wykonalności DSR: przy 30 wariantach certyfikacji nie przechodzi nawet strategia o Sharpe
   1.5. Licznik w `validation/trial_counter.json` jest wspólny dla całego projektu.
2. **Test oryginalności przed testem statystycznym.** Każda karta musi mieć nazwany publiczny
   benchmark i nazwaną **różnicę mechanizmu** (nie parametrów) — inaczej schodzi do benchmarków
   zanim spali choć jedną próbę. PLAN rozdz. 8.4.
3. **Zero syntetycznych danych w badaniach.** Ręcznie budowane bary w testach jednostkowych to
   fixture'y i są w porządku; żaden wniosek o rynku nie może pochodzić z danych innych niż realne.
4. **Zakaz strojenia pod wynik docelowy (R2).** Żadnej zmiany specyfikacji ani parametru po
   zobaczeniu P&L, jeśli motywem jest zbliżenie się do 1–2% miesięcznie.
5. **Każde nowe płatne źródło (R1)** wymaga: uzasadnienia, oszacowania kosztu, sprawdzenia
   darmowej alternatywy i **zgody właściciela**. Limit zamrożony w commicie sprzed zakupu (R4).
6. **Wyniki „zbyt piękne" traktuj jako objaw błędu.** Profit factor powyżej 2 przy strategii
   intraday — protokół nakazuje najpierw szukać buga, dopiero potem się cieszyć.
   `engine/metrics.py` ma flagę `Metrics.suspicious`.
7. **Nie ponawiaj automatycznie płatnych pobrań.** Metadane są darmowe i idempotentne —
   te ponawiamy. Pobranie tworzy plik i obciąża konto — tu decyduje człowiek.
8. **Ręczna edycja `validation/trial_counter.json` jest ZAKAZANA.** Jedyna dozwolona droga
   to `scripts/rejestruj_probe.py`. Powód jest asymetryczny: zawyżenie licznika obniża
   własny werdykt niepotrzebnie, ale **zaniżenie certyfikuje strategię niezasłużenie
   i nie zostawia śladu w żadnym wyniku**.
9. **Przed każdym odczytem lockboxa — wpis do `validation/lockbox_log.json`.** Jedno
   spojrzenie = zużycie sejfu. Bez dziennika reguła istnieje tylko w docstringu i nie
   da się po fakcie stwierdzić, ile razy sejf otwarto.
10. **Od H017: karta bez zielonego `scripts/waliduj_karte.py` nie może zostać zamrożona.**
    Linter sprawdza to, czego brak wychodzi dopiero po wydaniu prób: nazwanego przymuszonego
    uczestnika, różnicę wobec benchmarków, warunek negatywny, plan N/mocy, liczbę wariantów
    i sekcję „Recenzje". Karty Gen1 powstały przed linterem i **nie są** wstecznie objęte —
    ich wyniki mają pozostać odtwarzalne, a nie zgodne z późniejszym formularzem.

---

## 8. Mapa repozytorium

```
docs/PLAN.pdf            ŹRÓDŁO PRAWDY — 49 stron, czytaj przed zmianami w kodzie
docs/D5_ETAP4_SPEC.md    zamrożona specyfikacja bieżącego etapu
docs/SYNTEZA_GEN1.md     dlaczego wszystkie 16 kart Gen1 upadło
docs/URUCHOMIENIE_LOKALNE.md   konfiguracja maszyny właściciela
hypotheses/REGISTRY.md   katalog hipotez, pamięć instytucjonalna, stan każdej karty
HANDOFF.md               ten dokument
data/KOSZTY.md           każdy wydany dolar, łącznie z duplikacjami

engine/
  sessions.py       segmentacja doby w ET, DST, klasyfikacja luk
  cme_calendar.py   kalendarz CME z opublikowanych REGUŁ, zweryfikowany na danych
  costs.py          koszty i poślizg (baza 2.20 USD RT, skalowanie zmiennością)
  backtest.py       rozstrzyganie wewnątrzbarowe (tabela 5.4), warstwa ryzyka
  guards.py         HistoryView (blokada lookaheadu), zakres wartości, rozdzielenie serii
  roll.py           rolowanie wolumenowe, back-adjust różnicowy, px_raw/px_adj
  features.py       ATR, VWAP, percentyle, poziomy referencyjne (tylko na px_raw)
  metrics.py        PF, Sharpe + poprawka Lo, Sortino, MDD, MAR, SQN, koncentracja
  dataset.py        pipeline raw -> clean
  loader.py         GRANICA — wymaga danych w data/clean/
  databento_io.py   granica metadane/pobieranie; BRAK ponawiania pobrań jest celowy
  mbo_events.py     kanoniczna jednostka D5-B2 (akcja agresywna per Trade)
  paths.py          PROJECT_G_DATA_ROOT; clean_dir() zawsze w repo
  macro.py, earnings.py, equities.py, ndx_sensitivity.py    warstwa zdarzeń i K6

validation/
  dsr.py         Deflated Sharpe Ratio, SR₀ wg FST, N_eff przez ONC
  power.py       moc testu, liczność próby
  walkforward.py okna 12m/3m, purge + embargo, lockbox
  cpcv.py        Combinatorial Purged CV — 15 ścieżek zamiast jednej
  pbo.py         Probability of Backtest Overfitting (bramka < 0.20)
  spa.py         test SPA Hansena
  montecarlo.py  permutacja, bootstrap blokowy BCa, syntetyki
  trial_counter.json   globalny licznik prób — nadal 0

scripts/fetch_d5b2_month.py   NASTĘPNY KROK: zakup 21 sesji MBO
scripts/check_all.sh          kanoniczna bramka lokalna = CI + golden baseline
scripts/rejestruj_probe.py    JEDYNA droga zmiany licznika prób
scripts/waliduj_karte.py      linter kart hipotez — bramka zamrożenia od H017
validation/lockbox_log.json   dziennik otwarć sejfu OOS
docs/PROTOKOL_WSPOLPRACY.md   role, meldunek, pakiety recenzji, arbitraż
tests/                        regresja na liczbach z PLAN.pdf + strażnicy procesu
```

---

## 9. Jak zacząć następną sesję

```bash
git pull --ff-only
cat HANDOFF.md                      # ten plik
cat hypotheses/REGISTRY.md          # co żyje, co umarło, jakie wnioski
cat validation/trial_counter.json   # budżet prób
cat data/KOSZTY.md                  # ile już wydano i na co
bash scripts/check_all.sh --szybko  # czy wszystko nadal zielone
```

Potem sekcja 4 — najbliższy krok. Opis PR #4 zawiera bieżący status projektu.

---

## 10. Czego świadomie NIE robimy

Spisane, żeby kolejna sesja nie „ulepszała" rzeczy zamrożonych celowo:

- **Nie rozbijamy `engine/backtest.py`.** Kolejność operacji w barze **jest** specyfikacją
  (PLAN tabela 5.4); refaktor kosmetyczny grozi cichą zmianą wyników.
- **Nie ruszamy zamrożonych skryptów Gen1.** Ich wyniki są w rejestrze i mają być odtwarzalne.
- **Nie rozbudowujemy aparatu walidacyjnego.** DSR/PBO/CPCV/SPA są gotowe *przed* badaniami,
  nie po — to była świadoma kolejność i jest zrealizowana.
- **Nie optymalizujemy `mbo_events.py` przed testem miesięcznym.** Specyfikacja jest zamrożona,
  dry run przeszedł. Gdyby kiedyś optymalizować — z wymogiem **bitowej identyczności** wyników
  na 2026-07-30.
- **Nie kupujemy danych na zapas.** Dane kupuje się dopiero, gdy zamrożona karta ich żąda.

Wąskim gardłem projektu jest procedura i dane, nie kod.
