# HANDOFF — wznowienie pracy nad Projektem G

**Ten dokument jest napisany dla sesji, która nie widziała poprzedniej rozmowy.**
Kontener jest efemeryczny, więc wszystko potrzebne do kontynuacji jest tutaj i w repo.

Data: 11.08.2026 · Branch: `claude/financial-market-strategy-8mb1y1` · PR #4

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
niezmienników, CI, golden baseline. **585 funkcji testowych (661 przypadków po parametryzacji), pokrycie 92%, ruff i mypy czyste.**
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

**Zakup jest wstrzymany (niżej), a diagnostyka ZAMKNIĘTA** — testy 1–5
wykonane, `pobrano_utc` odczytane, panel Databento odczytany. Nic więcej nie
da się ustalić po naszej stronie.

**Korespondencja z dostawcą ZAMKNIĘTA w trzech z czterech punktów** (11.08,
`D5_DRYF` §5d): stare pliki są ważne, dodatkowy rekord `N` powstaje wyłącznie
dla zdarzeń wielopakietowych, **starej normalizacji nie da się już pobrać**.
Billing przekazany do ich zespołu.

### ⏳ ZOSTAŁA JEDNA BRAMKA: drugi mikro-diff

Decyzje właściciela z 11.08 zamknęły wszystko poza nią:

| | |
|---|---|
| ✅ Kwestia kont | **zamknięta bez rozstrzygnięcia**, świadomie. Kredyt 100+ USD potwierdzony, ryzyko szczątkowe = przerwany bieg, nie utrata danych (`KOSZTY` §3a) |
| ✅ Kopia zapasowa | **wykonana** 11.08 |
| ✅ `reports/D5_mikro_diff.json` | zacommitowany (`76e6710`) **przed** jakimkolwiek biegiem |
| ✅ Wątek billingowy | zamknięty — żadnych dalszych maili |
| ✅ Zgoda R1 na drugi mikro-diff | **udzielona**, limit 1,00 USD na okno |
| ✅ Drugi mikro-diff | **wykonany 11.08**, koszt 0,6133 USD (limit 1,00). Cztery punkty kryterium spełnione — `D5_DRYF` §5e |
| ⏳ **Werdykt PASS/FAIL** | **u recenzenta.** Wykonawca nie ocenia własnej pracy |

**Limity bez zmian: 82,00 USD na miesiąc (R4) i 1,00 USD na okno.** Zamknięcie
tematu kont **nie jest** zgodą na rozluźnianie czegokolwiek — obu limitów
pilnują testy.

> **Najpierw aktywuj venv.** Bez tego każda z poniższych komend kończy się
> `ModuleNotFoundError: No module named 'databento'`. Rozpoznanie zajmuje
> sekundę: znak zachęty **musi** zaczynać się od `(.venv)`.
>
> ```powershell
> .\.venv\Scripts\Activate.ps1
> ```
>
> Gdyby PowerShell odmówił uruchomienia skryptu (polityka wykonywania), można
> pominąć aktywację i wołać interpreter wprost:
> `.\.venv\Scripts\python.exe scripts\diff_mikro.py ...`
>
> **Ten błąd nic nie kosztuje** — `import databento` jest przed jakimkolwiek
> wywołaniem sieciowym, więc skrypt pada, zanim dotknie API.

```powershell
python scripts/diff_mikro.py --wycena --sesja 2026-07-06
python scripts/diff_mikro.py --sesja 2026-07-06
python scripts/diff_mikro.py --flagi --sesja 2026-07-06
python scripts/diff_mikro.py --rekonstrukcja --sesja 2026-07-06
```

Pierwsza darmowa, druga płatna (skrypt sam odmówi powyżej 1,00 USD), dwie
ostatnie darmowe z dysku. Potem wpis kosztu do `KOSZTY` §1 (warunek 4 zgody)
i commit raportu — **pod nową nazwą, więc nic się nie nadpisze**:

```powershell
git add reports/D5_mikro_diff_2026-07-06.json
git commit -m "reports: wynik mikro-diffu 07-06"
git push
```

**Werdykt PASS/FAIL wystawia recenzent, nie Wykonawca** — meldunek z liczbami
wg czterech punktów kryterium §5e, liczniki surowych rekordów per epoka
**poza** kryterium. Po werdykcie: PASS → wariant (a), zakup 17 sesji za
63,94 USD (bieg będzie wymagał `--akceptuj-rozjazd`, świadomie: archiwizuje
manifest, a `przeniesione_wyniki` chroni pochodzenie pięciu starych sesji).
FAIL → decyzja właściciela (b)/(c) wg tabeli §5d.
3. *(opcjonalne)* **Lektura oryginału ogłoszenia**
   `databento.com/blog/cme-normalization-changes-2026-07`. **Treść i cytaty są
   już w `D5_DRYF` §5b** — recenzent przeczytał je 11.08 i przekazał. Świeża
   sesja nie powinna uznać, że treść jest nieznana; zostaje tylko sprawdzenie
   oryginału, gdyby coś budziło wątpliwość (`databento.com` blokuje tu egress).
4. **Drugi mikro-diff** na otwarciu sesji pełnowymiarowej (07-06 13:30–14:00),
   limit 1,00 USD, wymaga zgody R1. **Dopiero po nim** decyzja mieszać/odkupić
   — `D5_DRYF` §5d i §5e.

> **Zasada korespondencji z dostawcą, wprowadzona po dwóch reprymendach.**
> Maile do Databento pisze się **prozą, prostym tekstem** — bez tabel, `**`,
> backticków i `>`. Markdown jest u nich nieczytelny. Powiedzieli to 04.08
> („please at least ask that it do so in a concise manner"), zignorowałem
> i usłyszałem drugi raz 11.08. Dwie z trzech rund poszły na czytelność
> zamiast na treść.

Jedna rzecz do zacommitowania z maszyny lokalnej — plik z wynikiem mikro-diffu
powstał podczas płatnego przebiegu i leży poza tym repo-klonem:

```powershell
git add reports/D5_mikro_diff.json
git commit -m "reports: wynik mikro-diffu 07-03 z 09.08"
git push
```

> **Nazwa `D5_mikro_diff.json` bez sesji jest HISTORYCZNA** — to pomiar okna
> 2026-07-03 z 09.08, sprzed parametryzacji skryptu. Kolejne okna zapisują się
> jako `D5_mikro_diff_<sesja>.json`. Zrób ten commit **zanim** uruchomisz
> cokolwiek z `diff_mikro.py`: do korekty ścieżki raportu drugi bieg nadpisywał
> ten plik, a jest on jedynym maszynowym śladem pomiaru, którego nie da się
> powtórzyć.

> **Bloki `powershell` w tym pliku nie mogą używać `&&`.** Windows PowerShell
> 5.1 nie zna tego separatora (`The token '&&' is not a valid statement
> separator in this version`). Jedna komenda na linię — właściciel pracuje na
> Windows, więc to nie jest kosmetyka, tylko warunek działania instrukcji.

Dopiero po odpowiedzi dostawcy wracają kroki zakupowe:

```powershell
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
> **Dwie diagnozy już upadły, obie obalone pomiarem.** (1) „Dostawca zrewidował
> dane" — odrzucone przez `get_dataset_condition` (brak modyfikacji w sierpniu).
> (2) „Wyceny zaniżone przez awarię 503/504" — odrzucone przez oś czasu: commit
> `299ca34` z **04.08 13:31Z**, dwa dni przed awarią, ma identyczne liczby,
> a pobrania z 04–05.08 fizycznie je zawierają.
>
> **Mechanizm NAZWANY przez dostawcę 10.08:** *„We released a change for
> GLBX.MDP3 over the weekend, which leads to additional MBO records being
> published for some events."* (Renan, Databento). To **celowa zmiana
> normalizacji**, nie awaria i nie utrata danych — zgodna z każdym naszym
> pomiarem. Szczegóły i to, czego odpowiedź NIE rozstrzyga: `D5_DRYF` §5b.
>
> **Rozliczenie mojego błędu:** wycofałem wcześniej ryzyko A4-11 z audytu 4
> („zmiana normalizacji GLBX.MDP3, VII 2026"), powołując się na
> `last_modified_date`. Audyt miał rację. `last_modified_date` **nie obejmuje
> zmian normalizacji** — brak sygnału w polu metadanych jest dowodem tylko
> wtedy, gdy wiadomo, co to pole obejmuje.
>
> Skutek praktyczny: każdy **już opłacony** plik wygląda na niekompletny, więc
> skrypt zaproponował zakup całego miesiąca **drugi raz**. Zatrzymał go
> warunek 4; od tej pory blokuje to wprost **warunek 8** (furtka:
> `--akceptuj-rozjazd`, **nie używać przed odpowiedzią dostawcy**).
>
> Analiza, odrzucone hipotezy z rachunkiem i gotowy mail:
> **[`docs/D5_DRYF_METADANYCH.md`](docs/D5_DRYF_METADANYCH.md)**.
>
> **Diagnostyka 08.08, oba testy wykonane.** Test 1: pięć plików bez uciętego
> ogona, 07-07 obcięty (3,94% rekordów). Test 2 — **rozstrzygający**: w oknie
> 13:30–14:30 sesji 07-03 nasz plik ma **1 362 037** rekordów wobec **1 389 818**
> u dostawcy. Brakuje **27 781 (−2,00%)** w oknie o **pełnym pokryciu czasowym**.
>
> **„PEŁNY" jest obalone empirycznie.** Pliki są krótsze o ~2%, a brak siedzi
> w środku sesji, nie na końcu. Nie jest też jednorodny (stosunek stóp 1,133).
>
> ### ✅ ROZSTRZYGNIĘTE 09.08 — wariant B′, mikro-diff za 0,0789 USD
>
> Porównanie **treści** 30 minut sesji 07-03 (`scripts/diff_mikro.py`, zgoda R1
> z pięcioma warunkami, wszystkie egzekwowane w kodzie):
>
> | | |
> |---|---:|
> | wspólnych rekordów | **822 240** |
> | tylko u dostawcy | **18 152** — wszystkie `action=N` |
> | **tylko u nas** | **0** |
> | A, C, F, M, T | różnica **+0 w każdym** |
>
> **Nasze pliki mają komplet realnych zdarzeń.** Nadwyżka to wypełniacze
> `order_id=0, side=N, size=0, price=INT64_MAX` — bez treści ekonomicznej.
> **Odkup z tytułu kompletności odpada.** Zakaz mieszania plików z obu okresów
> **zostaje w mocy** — liczebności nadal się rozjeżdżają, mechanizm bez nazwy.
>
> **Test 4 (`--flagi`, 09.08, darmowy):** wszystkie 18 152 rekordy `N` niosą
> `F_LAST` — **ale liczba kopert jest identyczna** (698 358 po obu stronach),
> a nadwyżka `F_LAST` na A (+7 506), C (+8 337) i M (+2 309) sumuje się co do
> rekordu do 18 152. **Bit został przeniesiony na osobny wypełniacz, nie
> dodany.** Skrypt wydrukował wtedy werdykt „audyt WYMAGA POWTÓRZENIA" — jest
> **nieprawdziwy**, gałąź `if` sprawdzała flagi przed sumami. Poprawione.
>
> **Test 5 (`--rekonstrukcja`, 09.08, darmowy) — DOMKNIĘCIE.** Rekonstrukcja
> jednostki obserwacji z obu plików: **29 734 akcje identyczne we wszystkich
> polach**, suma `n_trade` 32 953, suma rozmiaru 63 394 — po obu stronach ta
> sama. Cross-check: 32 953 zgadza się z licznikiem `action=T` z testu 3.
>
> ### ✅ AUDYT D5-C STOI. Diagnostyka ZAMKNIĘTA (testy 1–5)
>
> Wynik `842 757 zdarzeń, 0 niewyjaśnionych` opisuje **rynek**, a nie wersję
> serwowania danych. Przeniesienie `F_LAST` na wypełniacz jest dla naszej
> jednostki nieodróżnialne. Zmierzono 30 minut jednej sesji — dla pozostałych
> 21 równoważność pozostaje **uogólnieniem**.
>
> **Zakaz mieszania plików z obu okresów obowiązuje nadal.** Propozycja jego
> zawężenia (mieszać wolno dla analiz idącej przez `rekonstruuj`, nie wolno dla
> liczników surowych rekordów) czeka na decyzję właściciela — `D5_DRYF` §4 pkt 4.
>
> **Nie kupuj i nie kasuj niczego.** Stan: **5 z 22 sesji** (4 kampanijne + 07-30 z D5-C) pobrane. Panel Databento
> odczytany 09.08: **obciążono 20,65 USD, z karty 0,00** (pokryte kredytami),
> kredyt pozostały **104,35 / 125**. Przerwane pobrania **zostały naliczone
> w pełnym zakresie** — to już pomiar, nie hipoteza. Szczegóły i residuum
> 0,3490 USD: `data/KOSZTY.md` §3a.

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
> ponownie. **Korekta 11.08:** Databento rozlicza **dane faktycznie przesłane**
> („*you'll be charged for the partial data sent*", Rob), a nie całe zapytanie —
> wcześniejszy zapis w tym pliku był błędny. Przerwanie nadal kosztuje, bo płaci
> się za urwany fragment **i** za pełne pobranie przy wznowieniu.
> Precedens: D5-B, sesja 2026-07-07, pozycja „duplikacja" w `data/KOSZTY.md`.
> Nie przerywaj pobierania bez powodu.

> ## ⛔ KOPIA ZAPASOWA PRZESTAŁA BYĆ OSTROŻNOŚCIĄ — 11.08
>
> Databento na pytanie o przypinanie wersji: *„**The old data is not available
> anymore in our API.**"* Stara normalizacja jest **bezpowrotnie niedostępna**.
>
> **PIĘĆ** pobranych sesji to **jedyny istniejący egzemplarz** tej wersji
> danych:
>
> | sesja | rekordów | gdzie |
> |---|---:|---|
> | 2026-07-01 | 39 297 265 | `d5b2_mbo/` |
> | 2026-07-02 | 61 279 315 | `d5b2_mbo/` |
> | 2026-07-03 | 2 660 629 | `d5b2_mbo/` |
> | **2026-07-06** | **32 369 900** | `d5b2_mbo/` |
> | 2026-07-30 | 38 306 877 | `d5c_mbo/` — SHA `3e6f023d…74ac42` |
>
> Do wczoraj obowiązywało „odtworzenie kosztuje ~78 USD, skopiowanie nic".
> Dziś **odtworzenie nie jest możliwe za żadną cenę** — utrata dysku to utrata
> danych, na których policzono audyt D5-C.
>
> **Sesja 2026-07-06 wypadła z tej listy dwa razy** (raz w mailu do dostawcy,
> raz właśnie tutaj). Za drugim razem miałoby to skutek fizyczny, więc listę
> pilnuje teraz `tests/test_guards.py::TestKopiaZapasowa` porównując ją ze stałą
> `SESJE_STARA_NORMALIZACJA` w kodzie.
>
> ### ✅ WYKONANA 11.08.2026 (deklaracja właściciela)
>
> Poniższe zostaje jako procedura odtworzeniowa i lista kontrolna dla kolejnych
> zakupów — nie jako zaległe zadanie. Do skopiowania:
> **pięć plików `.dbn.zst`**, `manifest_d5b2.json`, `wycena_cache.json`
> i katalog `diag_mikro/`. Procedura: `docs/URUCHOMIENIE_LOKALNE.md` §8.1.
>
> ```powershell
> robocopy C:\ProjektG_dane E:\ProjektG_dane_backup /E /COPY:DAT /R:2 /W:5
> Get-FileHash -Algorithm SHA256 E:\ProjektG_dane_backup\raw\d5c_mbo\mnq_mbo_rth_2026-07-30.dbn.zst
> Get-ChildItem E:\ProjektG_dane_backup\raw\d5b2_mbo -Filter *.dbn.zst | Get-FileHash -Algorithm SHA256
> ```

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
