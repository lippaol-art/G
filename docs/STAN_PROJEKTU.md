# Stan projektu G — jeden plik, z którego widać całość

**Dla właściciela i recenzenta.** Odpowiada na trzy pytania: *co to za projekt*,
*gdzie dokładnie jesteśmy* i *co jest do zrobienia, w jakiej kolejności*.

Aktualizacja: **13.08.2026** · branch `claude/financial-market-strategy-8mb1y1` · PR #4

> ### Czego w tym pliku NIE MA — i to jest celowe
>
> **Nie ma tu kwot, liczb rekordów ani wyników liczbowych.** Projekt ma regułę:
> jedna liczba mieszka w jednym pliku. Dwie kopie tej samej kwoty rozjeżdżają się
> przy pierwszej zmianie — zdarzyło się to już z liczbą testów (trzy razy w ciągu
> doby) i z listą pobranych sesji (dwa razy, raz z konsekwencją fizyczną).
>
> Ten plik jest **mapą i procesem**. Po liczby odsyła do źródeł prawdy (§3).

---

## 1. Projekt w pięciu zdaniach

Szukamy **oryginalnej, statystycznie zweryfikowanej strategii** na kontrakcie
Micro E-mini Nasdaq-100 (MNQ) — przy użyciu świec, wskaźników pochodnych
i danych o zdarzeniach makro.

Wszystko liczone jest **na danych rzeczywistych**; jedyny wyjątek to ręcznie
skonstruowane rekordy w testach jednostkowych, i to rozróżnienie jest jawnie
zapisane, żeby nigdy nie zamazało się w praktyce.

Dokumentem założycielskim jest **`docs/PLAN.pdf`** (49 stron, wersja 1.1 po
czterech niezależnych audytach zewnętrznych) — wiążący tam, gdzie definiuje
metodę i progi.

Projekt jest prowadzony przez **trzy modele i jednego człowieka**, z jawnym
podziałem ról: Wykonawca nigdy nie wystawia werdyktu o własnej pracy (§5).

**Licznik prób wynosi 0.** Szesnaście hipotez upadło na tanich bramkach
wstępnych, zanim którakolwiek dotarła do backtestu. To jest wynik poprawny,
nie zaległość.

---

## 2. Kontekst właściciela — dlaczego reguły wyglądają, jak wyglądają

Ograniczony budżet, za rok płatne studia, cel docelowy to konto fundowane
z limitem 5% dziennie i 10% całkowicie.

Trzy rzeczy wynikają z tego wprost i **nie podlegają negocjacji przy żadnym
wyniku**:

- każdy płatny zakup przechodzi przez procedurę zgody (**R1**),
- **nie wolno stroić specyfikacji pod oczekiwany wynik** (**R2**) — deklarowane
  1–2%/mies. jest potrzebą finansową, nie targetem strategii,
- skalowanie ma być finansowane z rzeczywistych wypłat, nie z dopłat
  z pieniędzy na życie.

---

## 3. Mapa dokumentów — kto jest źródłem prawdy dla czego

**Zasada: w razie sprzeczności wygrywa plik z tej kolumny, nie ten, który
akurat czytasz.**

| Pytanie | Źródło prawdy |
|---|---|
| Metoda, progi, aparat statystyczny | `docs/PLAN.pdf` (v1.1) |
| Ile wydaliśmy i na co | `data/KOSZTY.md` |
| Stan hipotez, reguły R, licznik prób | `hypotheses/REGISTRY.md` |
| Jak wznowić pracę (dla świeżej sesji agenta) | `HANDOFF.md` |
| Podział ról i format recenzji | `docs/PROTOKOL_WSPOLPRACY.md` |
| Założenia o danych i rynku (A1…, B1…) | `docs/ZALOZENIA.md` |
| Incydent normalizacji GLBX.MDP3 | `docs/D5_DRYF_METADANYCH.md` |
| Specyfikacja bieżącego etapu D5 | `docs/D5_ETAP4_SPEC.md` |
| Konfiguracja maszyny lokalnej | `docs/URUCHOMIENIE_LOKALNE.md` |
| Zamrożone wyniki liczbowe | `golden/baseline.json` + `golden/ZMIANY.md` |
| Surowe pomiary mikro-diffów | `reports/D5_mikro_diff*.json` |

**Dokument, który czytasz, nie jest źródłem prawdy dla niczego.** Jest
skorowidzem i opisem procesu.

---

## 4. Gdzie jesteśmy

### 4.1 Zamknięte

| Etap | Wynik |
|---|---|
| Dokument założycielski v1.1 | cztery audyty zewnętrzne wniesione |
| Etap 0 — fundament repo | ✅ |
| Etap 1 — dane rynkowe | ✅ MNQ/NQ/ES, bary M1 2019–2026, w repozytorium |
| Etap 2 — silnik i aparat walidacyjny | ✅ bramka PLAN 5.6 zaliczona na pełnych danych |
| **Gen1 — 16 hipotez** | ✅ **wszystkie odrzucone w pre-flightach** |

**Wniosek przekrojowy Gen1:** bary M1 przewidują **amplitudę, nie kierunek**.
Pełna synteza: `docs/SYNTEZA_GEN1.md`.

To jest najważniejsza rzecz, jaką projekt dotąd ustalił — i kosztowała zero
prób, bo każda karta padła na bramce tańszej niż backtest.

### 4.2 W toku — D5, przepływ agresywny na danych MBO

Pytanie: czy **kto inicjuje transakcje** niesie informację o przyszłości,
a nie tylko o sobie samym. Wymaga danych MBO, więc kupowanych etapami.

| Podetap | Wynik | Lekcja |
|---|---|---|
| D5-A | GO | mechanizm w ogóle mierzalny |
| D5-B (`trades`) | ~~GO~~ → **INCONCLUSIVE** | werdykt **cofnięty**: `sequence` to numer wiadomości CME, nie identyfikator zdarzenia. Potwierdzone przez dostawcę |
| D5-C (jeden dzień MBO) | **GO** | znaleziona jednostka kanoniczna: akcja agresywna per `Trade`, po `order_id` |
| Dry run D5-B2 | 8/8 niezmienników | rekonstrukcja działa |
| **D5-B2 — miesiąc MBO** | 🔄 **zakup wstrzymany** | patrz §4.3 |

### 4.3 Co dokładnie blokuje zakup miesiąca

**Incydent normalizacji GLBX.MDP3** (pełna analiza: `docs/D5_DRYF_METADANYCH.md`).

W skrócie, bez liczb: dostawca wdrożył w weekend 8–9.08 zmianę normalizacji,
która dokłada rekordy-wypełniacze `action=N` i **przenosi na nie znacznik końca
zdarzenia**. Zmiana działa **wstecz na całą historię**, a **starej wersji nie
da się już pobrać**.

Sprawdziliśmy to pięcioma darmowymi testami i dwoma płatnymi pomiarami treści.
Wynik: nasze pliki mają **komplet realnych zdarzeń**, a jednostka obserwacji
jest po obu stronach identyczna.

**Stan bramki: czekamy na werdykt recenzenta.** Po nim znana jest droga
i koszt — obie mieszczą się w zamrożonym limicie.

### 4.4 Konsekwencja, która przeżyje ten incydent

**Pliki pobrane przed 8.08 to jedyny istniejący egzemplarz starej
normalizacji.** Nie odtworzy ich nikt — ani my, ani dostawca. Kopia zapasowa
przestała być ostrożnością i stała się warunkiem koniecznym; lista plików do
skopiowania jest pilnowana testem, bo dwa razy wypadła z niej jedna sesja.

---

## 5. Proces recenzji — jak to faktycznie działa

Pełna specyfikacja: `docs/PROTOKOL_WSPOLPRACY.md`. Tu jest opis praktyki.

### 5.1 Role wynikają z DOSTĘPU, nie z „specjalizacji"

| Rola | Kto | Czego NIE wolno |
|---|---|---|
| **Wykonawca** | Claude Code — jedyny z dostępem do repo i do uruchamiania kodu | **wystawiać werdyktu o własnej pracy** |
| **Recenzent** | model bez dostępu do zapisu, czytający repo przy **przypiętym SHA** | zmieniać kod — może tylko wnosić zarzuty |
| **Właściciel** | człowiek | — podejmuje **wszystkie** decyzje o pieniądzach i kierunku |

Ten podział nie jest kurtuazją. Wykonawca ma systematyczną skłonność do
uznawania własnej pracy za poprawną — w tym projekcie **trzy tezy Wykonawcy
zostały obalone**, dwie przez własne pomiary, jedna przez dostawcę.

### 5.2 Cykl jednej rundy

```
1. Wykonawca robi zmianę           → jeden commit na temat, opis mówi CO i DLACZEGO
2. Bramka lokalna                  → bash scripts/check_all.sh  +  golden --sprawdz
3. Push                            → CI musi być zielone
4. Wykonawca składa MELDUNEK       → liczby, nie oceny; sekcja NIEPEWNOŚCI obowiązkowa
5. Recenzent czyta przy SHA        → wnosi zarzuty w formacie z §6 protokołu
6. Wykonawca weryfikuje KAŻDY      → w źródle, zanim cokolwiek zmieni
7. Korekty w JEDNYM commicie       → z jawnym rozliczeniem, co było nie tak
8. Recenzent wystawia WERDYKT      → PRZYJĘTE / do poprawki
```

**Krok 6 jest nienegocjowalny.** Zarzut bywa trafny co do faktu i błędny co do
wniosku; przyjęcie go bez sprawdzenia byłoby tym samym błędem, co odrzucenie
bez sprawdzenia.

### 5.3 Format meldunku — co musi w nim być

- **liczby dosłowne**, nigdy „około" ani „mniej więcej",
- **co zostało zmierzone, a co jest uogólnieniem** — jawnie rozdzielone,
- **sekcja NIEPEWNOŚCI z co najmniej jednym wpisem**; „brak" jest zakazane,
- **żadnego werdyktu o własnej pracy**.

### 5.4 Poziomy recenzji

| Poziom | Kiedy |
|---|---|
| **P1** | codziennie — bieżące commity |
| **P2** | przed zamrożeniem karty hipotezy lub specyfikacji |
| **P3** | spór — arbitraż trzeciego modelu |

### 5.5 Kryterium zapisuje się PRZED pomiarem

Reguła, która w tym projekcie zadziałała dosłownie: warunki zaliczenia
płatnego pomiaru trafiają do **commita sprzed biegu**. Inaczej „przeszło"
znaczy tyle, co „dopasowaliśmy próg do tego, co wyszło".

Przy obu mikro-diffach kryterium było zapisane wcześniej i dlatego wynik da się
obronić bez odwoływania się do niczyjej dobrej woli.

---

## 6. Reguły trwałe

| # | Reguła | Gdzie |
|---|---|---|
| **R1** | Płatne źródło wymaga: uzasadnienia, kosztu, sprawdzenia darmowej alternatywy i **zgody właściciela** | REGISTRY |
| **R2** | **Zakaz strojenia pod wynik docelowy** — żadnej zmiany po zobaczeniu P&L | REGISTRY |
| **R3** | Limity firmowe to bariery awaryjne, nie robocze; metryką operacyjną jest **prawdopodobieństwo utrzymania konta** | REGISTRY |
| **R4** | Każdy zakup ma **limit zamrożony w commicie sprzed zakupu** | REGISTRY + `KOSZTY` §4 |
| **R9** | Zgłoszenia do dostawcy: **zwięźle, prozą**, 2–3 pytania na wątek | REGISTRY |

Dodatkowo, wbudowane w kod, nie w dyscyplinę:

- **zero lookaheadu** — architektoniczna blokada, nie konwencja,
- **zakaz wykonania przy zerowym wolumenie**,
- **rozdzielenie `px_raw` / `px_adj`** — poziomy międzysesyjne tylko na serii surowej,
- **globalny licznik prób**: ≤ 10 wariantów na hipotezę, ≤ 40 na partię;
  benchmarki nie liczą się, bo nie są optymalizowane.

---

## 7. Dziennik decyzji wiążących

Chronologicznie, tylko rzeczy, które zmieniły kierunek. **Wpisy się nie
kasują** — jeśli coś okazało się błędem, dopisujemy korektę obok.

| Data | Decyzja |
|---|---|
| 31.07 | baza kosztów 1 tick/stronę; konserwatyzm wyłącznie w stress-teście ×2 |
| 31.07 | rewizja dokumentu **batchowa** — po zebraniu wszystkich audytów, jedną zmianą |
| ~01.08 | **system dwustopniowy** PROMISING/CERTIFIED; limit **10** wariantów na hipotezę zamiast 30 |
| 02.08 | reguła oryginalności zastąpiona **4-krokowym testem** (benchmark → różnica mechanizmu → test przyrostowy → ablacje) |
| 02.08 | **Gen1 zamknięta**, licznik prób zostaje na 0 |
| 02.08 | reguły **R1–R3** zapisane na stałe |
| 04.08 | `sequence` — werdykt D5-B **cofnięty** po odpowiedzi dostawcy |
| 09.08 | zgoda R1 na **pierwszy mikro-diff**, pięć warunków egzekwowanych w kodzie |
| 11.08 | kwestia przypisania kont **zamknięta bez rozstrzygnięcia** — świadomie, ryzyko szczątkowe to przerwa, nie strata |
| 11.08 | wątek billingowy u dostawcy **zamknięty**; żadnych dalszych maili |
| 11.08 | zgoda R1 na **drugi mikro-diff**; limity 82,00 i 1,00 **bez zmian** |
| 11.08 | **R9** — korespondencja z dostawcą prozą, po dwóch reprymendach |

---

## 8. Co jest do zrobienia — kolejka

### 8.1 Teraz

| # | Zadanie | Kto | Blokuje |
|---|---|---|---|
| 1 | **Werdykt PASS/FAIL** dla drugiego mikro-diffu | recenzent | zakup miesiąca |
| 2 | Po PASS: zakup pozostałych sesji MBO | właściciel uruchamia | D5-B2 |
| 3 | Po FAIL: decyzja wariantu z tabeli `D5_DRYF` §5d | właściciel | D5-B2 |

**Bieg zakupowy będzie wymagał jawnej flagi `--akceptuj-rozjazd`** — świadomie:
archiwizuje stary manifest zamiast go nadpisać, a pochodzenie starych sesji
chroni osobny mechanizm.

### 8.2 Zaraz po zakupie

1. **Kopia zapasowa** świeżo pobranych plików — przed jakąkolwiek analizą.
2. **Rekonstrukcja miesiąca** i bramka GO/NO-GO dla D5-B2 z **sześcioma progami
   zamrożonymi w specyfikacji przed zobaczeniem wyniku**.
3. Przy NO-GO: licznik prób zostaje na zerze i **to też jest wynik**.

### 8.3 Otwarte, nieblokujące

| Temat | Stan |
|---|---|
| **Rotacja klucza API** | rekomendacja **otwarta**; pierwszy klucz przeszedł przez transkrypt rozmowy. Świadomie odłożona przez właściciela — nie wolno uznać za zamkniętą bez jego decyzji |
| Zakaz mieszania plików z obu okresów normalizacji | obowiązuje; propozycja **zawężenia** czeka na decyzję właściciela |
| Przecięcie populacji „koperty wielopakietowe" vs „≥2 agresorów" | obserwacja **niezmierzona**, sprawdzalna lokalnie za darmo |
| Symulator zasad kont fundowanych | odłożony świadomie do czasu GO/NO-GO |
| Gen2 — nowa generacja kart | brief i kandydaci gotowi (`docs/GEN2_BRIEF.md`, `docs/GEN2_KANDYDACI.md`); start po D5 |

---

## 9. Czerwone linie

**Nigdy, niezależnie od wyniku:**

1. **Nie zmieniamy specyfikacji po zobaczeniu P&L**, jeśli motywem jest
   zbliżenie się do oczekiwanego zwrotu (R2).
2. **Nie kupujemy danych bez zgody właściciela** i bez limitu zamrożonego
   w commicie sprzed zakupu (R1, R4).
3. **Nie obchodzimy odmowy polityki sieciowej** — zgłaszamy ją, nie szukamy
   objazdu, nie wyłączamy weryfikacji TLS.
4. **Klucz API tylko ze zmiennej środowiskowej**, nigdy w pliku, nigdy
   z wartością domyślną.
5. **Nie ponawiamy ślepo płatnych pobrań po błędzie** — najpierw sprawdzamy,
   co powstało na dysku.
6. **Wykonawca nie ogłasza werdyktu o własnej pracy.**
7. **Zero danych syntetycznych** we wnioskach o rynku. Ręczne rekordy
   w testach jednostkowych to fixture'y i są tak nazwane.

---

## 10. Jak sprawdzić, że wszystko stoi

```bash
bash scripts/check_all.sh          # linter, typy, testy, strażnicy, bramka silnika
python scripts/golden_baseline.py --sprawdz   # musi dać: BASELINE ZGODNY
```

`scripts/check_all.sh` jest **bramką kanoniczną** i odpowiada CI krok w krok. Pełny
przebieg dokłada bramkę silnika na realnych danych i golden baseline — tych
dwóch CI nie uruchamia, bo nie ma tam danych rynkowych.

**Na maszynie właściciela (Windows) najpierw aktywuj środowisko** — znak
zachęty musi zaczynać się od `(.venv)`. Bez tego wszystko kończy się
`ModuleNotFoundError`.

---

## 11. Czego ten projekt NIE obiecuje

Najbardziej prawdopodobnym wynikiem każdej kolejnej karty jest to, że **upadnie** —
i tak było szesnaście razy z rzędu. To nie pesymizm, tylko zmierzona baza.

Aparat jest zbudowany tak, żeby porażkę wykryć **tanio i wcześnie**, a nie
żeby ją ukryć. Backtest ma prawo zaniżać wynik; nie ma prawa go zawyżać.

Decyzja o realnym kapitale należy wyłącznie do właściciela. Żaden wynik
backtestu ani symulacji nie gwarantuje wyników rzeczywistych.
