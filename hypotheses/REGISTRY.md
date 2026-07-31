# Rejestr hipotez — Projekt G

Pamięć instytucjonalna projektu. **Każda sesja agenta zaczyna od przeczytania tego pliku.**

Rejestr pełni trzy funkcje: (1) zapewnia ciągłość między sesjami, (2) jest jawnym licznikiem prób
wchodzącym do DSR, (3) akumuluje wnioski przekrojowe zasilające projektowanie kolejnych partii.

Specyfikacja procesu: `docs/PLAN.pdf` rozdz. 8. Test oryginalności: rozdz. 8.4.

---

## Stany hipotezy

```
IDEA → TESTING → REJECTED(faza)
              ↘ CANDIDATE → [bramka Tier 1] → PROMISING → (forward paper) → CERTIFIED
                                            ↘ REJECTED(gate)
```

`REJECTED` jest trwały. Hipoteza może wrócić wyłącznie jako **nowa karta z nowym ID**
i jawnym odwołaniem do poprzedniczki (np. „H017, wariant H003 z wnioskiem W-12").

---

## Benchmarki — B01–B04

**Nie są kandydatami na oryginalną strategię.** Uruchamiane raz, z parametrami wprost z
literatury, bez optymalizacji. Służą jako grupa kontrolna w teście przyrostowym (8.4 krok 3).
**Nie zużywają globalnego licznika prób** — to bezpośredni zysk dla DSR wszystkich kandydatów.

| ID | Karta | Publiczny odpowiednik | Status | Wynik |
|----|-------|----------------------|--------|-------|
| B01 | Gap otwarcia i domknięcie | Gap-fill (klasyka indeksowa) | IDEA | — |
| B02 | Cykl kontrakcja–ekspansja | NR7 i pochodne, Crabel ~1990 | IDEA | — |
| B03 | Asymetria piątek→poniedziałek | Weekend effect, Cross 1973 / French 1980 | IDEA | — |
| B04 | Mechanika zamknięcia / proxy MOC | Momentum wewnątrzdzienne, Gao i in. JFE 2018 | IDEA | — |

---

## Karty przeformułowane — H001–H004

Mechanizmy warte ratowania, pod warunkiem przejścia kroków 1–2 testu oryginalności.
**Reguła samoczyszcząca:** jeśli przy pisaniu pełnej karty różnicy mechanizmu nie da się
obronić, karta schodzi do benchmarków — decyzja zapada na papierze, zanim spali próbę.

| ID | Karta | Benchmark | Wymagana różnica mechanizmu | Status | Warianty |
|----|-------|-----------|----------------------------|--------|----------|
| H001 | Kompresja nocna: przyczyna, nie fakt | B02 + ORB | Kompresja z braku uczestników vs z równowagi sił (wolumen przy wąskim zakresie) | IDEA | 0/8 |
| H002 | Powrót do VWAP: kto stoi po drugiej stronie | „lunch VWAP fade" | Struktura wolumenu, która wytworzyła odchylenie — szum egzekucyjny vs informacja | IDEA | 0/6 |
| H003 | Reakcja na publikację: odwrócenie vs kontynuacja | „fade the news" | Relacja impulsu do struktury płynności sprzed publikacji, nie wielkość impulsu | IDEA | 0/6 |
| H004 | Dryf nocny — czy jeszcze istnieje | Cooper–Cliff–Gulen 2008 | **Blokada:** test wstępny musi najpierw wykazać, że efekt bazowy nie wygasł | IDEA | 0/4 |

### H004 — test wstępny obowiązkowy przed jakąkolwiek pracą

Zewnętrzne badania wskazują na wygaśnięcie dryfu overnight na indeksach US po 2020 r.
**Nie przyjmujemy tego na wiarę ani nie odrzucamy** — sprawdzamy na własnych danych:
dekompozycja zwrotów close→open rok po roku, 2019–2026, z przedziałami ufności.

- Dryf obecny w ostatnich latach → karta wchodzi do badań z pytaniem o warunkowość reżimową.
- Dryf wygasł → karta schodzi do benchmarków, a wynik trafia do wniosków przekrojowych jako
  **własny, policzony dowód zaniku znanego efektu**.

---

## Kandydaci — główny front badań

| ID | Karta | Klasa | Priorytet | Status | Warianty |
|----|-------|-------|-----------|--------|----------|
| H011 | Sekwencja Azja→Europa jako predyktor RTH | K1 | **najwyższy** — najniższe pokrycie z literaturą | IDEA | 0/6 |
| H005 | Mikrostruktura kolejnych testów poziomu | K5 | wysoki | IDEA | 0/6 |
| H010 | Zmienność zrealizowana wobec oczekiwanej | K3 × K1 | wysoki (+ warstwa reżimowa dla innych kart) | IDEA | 0/6 |
| H013 | Rezydualny repricing po wynikach megacapów | K6 × K4 | wysoki (wymaga warstwy danych K6) | IDEA | 0/8 |
| H014 | Dywergencja NQ–ES wokół szoków stóp | K6 × K4 | średni (wymaga ES) | IDEA | 0/6 |
| H016 | Reżim dyspersji składników NDX | K6 × K3 | średni (oceniana przyrostem w innych kartach) | IDEA | 0/6 |

### H015 — zarejestrowana, niebadalna

| ID | Karta | Powód wstrzymania |
|----|-------|-------------------|
| H015 | Price discovery NQ→MNQ (lead-lag) | Zjawisko rozgrywa się w milisekundach. Na barach M1 **każdy wynik byłby artefaktem agregacji** — i to artefaktem wyglądającym przekonująco. Wraca, gdy pozyskamy dane `trades`/MBP. **Nie zużywa ani jednej próby.** |

Karta jest zapisana celowo: jawne odnotowanie „wiemy o tym mechanizmie i wiemy, dlaczego go nie
badamy" chroni przyszłe iteracje przed przypadkowym wejściem w tę pułapkę.

---

## Kolejność partii

| Partia | Skład | Uzasadnienie |
|--------|-------|--------------|
| **0** | Test dryfu nocnego + benchmarki B01–B04 | Tanie, szybkie, rozstrzyga los H004 i dostarcza punktów odniesienia dla wszystkich testów przyrostowych. Zero zużycia licznika prób. |
| **1** | H011, H005, H010 | Najniższe pokrycie z literaturą przy zadowalającej częstości sygnałów. |
| **2** | H013, H014, H016 | Klasa K6 — wymaga gotowej warstwy danych (PLAN rozdz. 4.7). |
| **3** | H001, H002, H003 | Po przejściu kroków 1–2 testu oryginalności. Część prawdopodobnie odpadnie do benchmarków. |

---

## Wnioski przekrojowe (W-xx)

Fakty o rynku i o procesie odkryte przy okazji badań. Zasilają projektowanie kolejnych partii.

| ID | Wniosek | Źródło |
|----|---------|--------|
| — | *(brak — projekt przed pierwszą partią)* | |

---

## Licznik prób

Stan globalnego licznika: patrz `validation/trial_counter.json`.

**Reguła bezwzględna:** każdy przebieg backtestu — każda kombinacja parametrów w każdej siatce
każdej hipotezy — inkrementuje licznik. DSR każdego kandydata liczy się względem *całego*
licznika projektu, z korektą na korelację między wariantami (algorytm ONC, aneks A.3).

Limity: **≤ 10 wariantów na hipotezę**, **≤ 40 na partię**. Benchmarki nie liczą się do limitu,
bo nie są optymalizowane.

Dlaczego to jest twarde: przy N_eff = 30 nie przechodzi certyfikacji nawet strategia o Sharpe 1.5
(tabela wykonalności, PLAN rozdz. 6.5). Im dłużej szukamy, tym wyższy próg musi przeskoczyć
zwycięzca — to cena uczciwości i płacimy ją świadomie.
