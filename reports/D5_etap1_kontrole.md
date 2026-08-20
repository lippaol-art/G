# D5 Etap 1 — dziewięć kontroli danych `trades`

# Werdykt: `D5-A GO`

`side != NONE` w **99,9999%** transakcji, przy progu 95%. Semantyka agresora
potwierdzona empirycznie. Kompletność ≥ 99,998% w **każdym** segmencie sesji.

Sesja `2026-07-30`, kontrakt `MNQU6`, 1 696 891 transakcji, koszt 2,1240 USD.
Specyfikacja zamrożona przed zakupem (`41d3eee`), budżet skorygowany (`953b5ec`).
Odtworzenie: `python3 scripts/audit_d5_etap1.py`.

**Zero zużytych prób.** Nie policzono ani jednego przyszłego zwrotu, P&L,
progu nierównowagi ani okna.

---

## 1–2. Kompletność pola `side`

Globalnie: **99,9999%** — dwie transakcje z 1 696 891 bez strony agresora.

| Segment | Transakcji | `side != NONE` |
|---|---:|---:|
| midday | 469 026 | 100,000% |
| asia | 326 223 | 100,000% |
| rth_open | 321 450 | 100,000% |
| europe | 200 317 | 100,000% |
| close | 97 791 | 100,000% |
| afternoon | 95 847 | 100,000% |
| premarket | 72 925 | 100,000% |
| globex_open | 57 808 | 99,998% |
| after_hours | 55 504 | 99,998% |

Największe ryzyko audytu D5 — że `side` będzie często `NONE` i poziom A okaże
się niemierzalny — **nie zmaterializowało się**. Nie tylko przekracza próg,
ale przekracza go o cztery rzędy wielkości marginesu.

---

## 3. Semantyka `side` — ustalona z danych, nie z pamięci

Nie przyjąłem konwencji z dokumentacji (strona zwraca 403) ani z pamięci.
Odczytałem ją z danych:

| Kierunek zmiany ceny | n | `B` | `A` |
|---|---:|---:|---:|
| cena rośnie | 634 703 | **87,7%** | 12,3% |
| cena spada | 632 380 | 11,9% | **88,1%** |

Stąd:

- **`B` = agresor kupujący** (bierze płynność z asku),
- **`A` = agresor sprzedający** (bierze płynność z bidu).

**Uwaga metodologiczna.** Tick posłużył tu **wyłącznie do odczytania znaczenia
etykiety**, a nie do jej odtworzenia. Etykieta pozostaje wzięta z pola `side`.
Zakaz z sekcji 4 specyfikacji — rekonstrukcji strony z ruchu ceny — dotyczy
budowania zmiennej i **nie został naruszony**; zresztą przy 99,9999%
kompletności nie ma czego rekonstruować.

---

## 4. Znaczniki czasu

```
ts_event : 2026-07-29 22:00:00.000000Z -> 2026-07-30 20:59:59.765379Z
ts_recv  : 2026-07-29 22:00:00.013066Z -> 2026-07-30 20:59:59.765673Z
```

| Wielkość | Mediana | p99 | Min |
|---|---:|---:|---:|
| `ts_recv − ts_event` | 269 µs | 4 909 µs | 153 µs |
| `ts_in_delta` | 12 878 ns | 19 134 ns | — |

**Ujemnych opóźnień: 0.** Okno pokrywa dokładnie zamówioną dobę handlową.

Praktyczny wniosek dla D5: własne opóźnienie odbioru danych jest rzędu setek
mikrosekund, czyli **o cztery rzędy wielkości mniejsze** niż deklarowany
horyzont mechanizmu (dziesiątki sekund do minut). Opóźnienie feedu nie jest
tu wąskim gardłem — będzie nim opóźnienie platformy wykonawczej.

---

## 5. Duplikaty i kolejność

| Kontrola | Wynik |
|---|---|
| `ts_event` niemonotoniczne | **0** |
| `sequence` niemonotoniczne | **0** |
| `sequence` zduplikowane | 224 564 |
| rekordy identyczne na `[ts_event, price, size, side, sequence]` | 20 552 |

### Duplikaty `sequence` nie są defektem — i mają znaczenie dla konstrukcji D5

Jedno zlecenie agresora wypełnia się przeciw wielu zleceniom pasywnym, a CME
drukuje **osobny rekord na każde wypełnienie**. Stąd:

```
1 696 891 wypełnień  ->  1 479 365 zdarzeń agresora
                          (średnio 1,15 wypełnienia na zdarzenie)
```

**Konsekwencja projektowa:** jednostką mechanizmu kontynuacji metaorderu jest
**zdarzenie agresora**, nie pojedyncze wypełnienie. Liczenie nierównowagi po
wypełnieniach nadważyłoby zlecenia, które trafiły w rozdrobnioną książkę —
czyli mierzyłoby fragmentację płynności zamiast agresji.

To ustalenie trafia do zamrożonej definicji nierównowagi w Etapie 2.

---

## 6–7. Ceny, rozmiary, kontrakt

| Kontrola | Wynik |
|---|---|
| zakres cen | 27 204,75 – 28 410,00 |
| poza siatką ticka 0,25 | **0** |
| rozmiar: min / mediana / p99 / max | 1 / 1 / 8 / 170 |
| rozmiar ≤ 0 | **0** |
| `instrument_id` unikalnych | **1** (`42004800`) |
| `symbol` unikalnych | **1** (`MNQU6`) |

Kontrakt jednoznaczny, bez sklejeń. Mediana rozmiaru = 1 potwierdza, że MNQ
jest instrumentem drobnicowym — istotne przy szacowaniu, jak duży przepływ
w ogóle da się na nim zaobserwować.

---

## 8. Rekonstrukcja `ohlcv-1m` — i najważniejsze uboczne ustalenie audytu

Zrekonstruowałem bary minutowe z surowych transakcji i porównałem z posiadanym
zbiorem `ohlcv-1m`.

| Pole | Niezgodnych | Max różnicy |
|---|---:|---:|
| open | **0** z 1 380 | 0,0000 |
| high | **0** z 1 380 | 0,0000 |
| low | **0** z 1 380 | 0,0000 |
| close | **0** z 1 380 | 0,0000 |
| wolumen | **0** z 1 380 | 0 |

**Zgodność doskonała na wszystkich 1 380 barach.**

### Bary agregują się na `ts_recv`, nie na `ts_event`

To nie było oczywiste i kosztowało jedną iterację. Pierwsza rekonstrukcja,
oparta na `ts_event`, dała:

| Baza | open | close | wolumen |
|---|---:|---:|---:|
| `ts_event` | 8 niezgodnych | 6 | 20 |
| **`ts_recv`** | **0** | **0** | **0** |

Sygnałem, że to efekt granicy minuty, a nie brak danych, była **suma różnic
wolumenu równa dokładnie zero** — transakcje przenosiły się między sąsiednimi
minutami, nic nie ginęło.

**Znaczenie dla D5:** granica okna obserwacji musi być liczona na `ts_recv`.
Użycie `ts_event` dałoby ciche przesunięcia kilkunastu barów na sesję, bez
żadnego wyjątku ani ostrzeżenia — dokładnie ta klasa błędu, którą projekt
tropi od początku.

### To domyka zaległość z audytu 4 (poprawka A4-10)

Niezależna kontrola jakości barów przez rekonstrukcję z transakcji była
zaplanowana w Etapie 1 projektu i **nigdy nie wykonana** — skrypt
`verify_bars.py` nie powstał. Etap 1 D5 wykonał ją przy okazji i wynik jest
najmocniejszym dotąd potwierdzeniem jakości naszych danych: **bary dostawcy
odtwarzają się z surowych transakcji co do ticka i co do sztuki.**

---

## 9. Zgodność z ET i `trade_date`

Wszystkie 1 696 891 transakcji mapuje się na **jeden** `trade_date`:
`2026-07-30`. Okno zakupu (`22:00Z → 21:00Z`) odpowiada dokładnie naszej
definicji doby handlowej od 18:00 ET (założenie A1), przy czasie letnim EDT.

---

## Werdykt i co dalej

| Warunek | Próg | Wynik |
|---|---|---|
| `side != NONE` | > 95% | **99,9999%** ✅ |
| semantyka agresora potwierdzona | — | ✅ z danych |
| kompletność w kluczowych segmentach | dobra | ✅ ≥ 99,998% wszędzie |

# `D5-A GO`

**Zatrzymuję się tutaj.** Miesiąc `trades` (~29,83 USD) wymaga osobnej decyzji
oraz wcześniejszego zamrożenia: definicji nierównowagi (po **zdarzeniach
agresora**, nie wypełnieniach), okna obserwacji, benchmarku momentum i sposobu
liczenia VIF.

**H017 nie powstaje. P&L nie jest mierzony. Licznik prób: 0.**

Budżet: 62,42 − 2,1240 = **60,2960 USD**.
