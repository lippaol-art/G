# D5 Etap 1 — specyfikacja zamrożona PRZED zakupem

**Ten dokument jest commitowany przed pobraniem jakichkolwiek danych.**
Commit zamrażający poprzedza zakup, tak samo jak przy H003 (`ae0f9f8`,
`d03337c`). Cokolwiek zobaczymy w danych, ta specyfikacja się nie zmienia.

---

## 1. Zamrożone parametry zakupu

| Parametr | Wartość |
|---|---|
| **Dataset** | `GLBX.MDP3` |
| **Schemat** | `trades` |
| **Symbol** | `MNQU6` (`stype_in="raw_symbol"`) |
| **Sesja** | **`trade_date = 2026-07-30`** |
| **Okno UTC** | `2026-07-29T22:00` → `2026-07-30T21:00` |
| **Koszt maksymalny** | **1,75 USD** — powyżej tej kwoty **nie kupuję** |
| **Próg werdyktu** | `side != NONE` w **> 95%** transakcji |

### Zasada wyboru daty i dlaczego wypadła na 2026-07-30

Reguła: **ostatnia kompletna, zamknięta, standardowa sesja.**

Dzisiaj jest 2026-08-03 (poniedziałek). Kandydaci w kolejności wstecznej:

| Sesja | Werdykt |
|---|---|
| 2026-08-03 (pon.) | **odpada** — sesja niezamknięta |
| 2026-07-31 (pt.) | **odpada** — obiektywna wada techniczna: nasze dane referencyjne `ohlcv-1m` mają dla tej sesji **120 barów z ~1380**, więc kontrola rekonstrukcji OHLCV byłaby niewykonalna |
| **2026-07-30 (czw.)** | **WYBRANA** |

Weryfikacja, że 2026-07-30 jest standardowa — z naszych danych, przed zakupem:

- **1380 barów** w `ohlcv-1m`, dokładnie mediana ostatnich 60 sesji,
- `short_day = False` — nie jest dniem skróconym,
- `halt_window = False` — brak okna haltu,
- kontrakt **`MNQU6`** jednoznacznie, bez granicy rolowania w tej sesji,
- czwartek, nie koniec miesiąca, nie tydzień wygasania.

Wykluczenie 2026-07-31 mieści się w zadeklarowanym wyjątku („brak danych"),
i to **braku po naszej stronie**, nie u dostawcy. Odnotowuję to jawnie, bo
wyjątek został użyty — nie jest to wybór wygodny, tylko wymuszony brakiem
odniesienia do kontroli rekonstrukcji.

### Okno czasowe odpowiada naszej definicji doby handlowej

`trade_date` zaczyna się o 18:00 ET dnia poprzedniego (założenie A1). Dla
2026-07-30 przy czasie letnim (EDT, UTC−4):

```
18:00 ET 2026-07-29  =  22:00 UTC 2026-07-29
17:00 ET 2026-07-30  =  21:00 UTC 2026-07-30
```

Okno zakupu jest więc **dokładnie tą samą dobą**, co nasz `trade_date` —
inaczej porównanie z `ohlcv-1m` byłoby niepoprawne o godziny.

---

## 2. Co Etap 1 sprawdza

Wyłącznie własności danych. Dziewięć kontroli:

1. odsetek `BID` / `ASK` / `NONE` w polu `side`,
2. kompletność `side` **globalnie i per segment sesji** (azja, europa,
   premarket, rth_open, midday, afternoon, close, wieczór),
3. oficjalna semantyka `BID`/`ASK` — czy oznaczają stronę agresora,
4. poprawność `ts_event`, `ts_recv`, `sequence`, `ts_in_delta`,
5. duplikaty i odwrócenia kolejności,
6. tick size, zakres cen, rozkład rozmiarów,
7. jednoznaczność kontraktu (jeden `instrument_id`),
8. **rekonstrukcja `ohlcv-1m`** i porównanie z posiadanymi barami,
9. zgodność czasu z ET i przypisaniem do `trade_date`.

## 3. Czego Etap 1 NIE liczy

- przyszłych zwrotów,
- P&L,
- optymalnych okien,
- progów nierównowagi,
- skuteczności sygnału.

**Zero zużytych prób.**

---

## 4. Werdykt — kryteria zamrożone

| Warunek | Werdykt |
|---|---|
| `side != NONE` > 95% **i** semantyka agresora potwierdzona **i** dobra kompletność w kluczowych segmentach | **`D5-A GO`** |
| w przeciwnym razie | **`D5-A NO-GO`** |

### Zakaz rekonstrukcji strony z ruchu ceny

Jeśli próg nie przejdzie, **nie wolno** odtwarzać strony agresora z kierunku
zmiany ceny (reguła tick-test / Lee–Ready). Wbudowałoby to momentum wprost
w zmienną, którą później mamy od momentum **odróżniać** — czyli
zagwarantowałoby porażkę Etapu 2 przez konstrukcję, albo, gorzej, pozorny
sukces będący tautologią.

---

## 5. Budżet

| Pozycja | Kwota |
|---|---|
| Stan przed | 62,42 USD |
| Etap 1 (maks.) | −1,75 USD |
| **Stan po** | **60,67 USD** |

---

## 6. Co zostanie zapisane po zakupie

Faktyczny koszt, rozmiar pliku, parametry zapytania, SHA-256 pliku surowego,
data pobrania, wersja biblioteki — w `data/manifest_trades.md`.

---

## 7. Po Etapie 1 — zatrzymanie

Miesiąc `trades` (~29,83 USD) wymaga **osobnej decyzji** oraz wcześniejszego
zamrożenia: definicji nierównowagi, okna, benchmarku momentum i sposobu
liczenia VIF.

**H017 nie powstaje. P&L nie jest mierzony. Licznik prób: 0.**
