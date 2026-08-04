# Pytanie do wsparcia Databento — semantyka `sequence`, `flags`, `F_LAST`, `ts_recv`

## Status wysyłki

| | |
|---|---|
| Adres odbiorcy | **support@databento.com** — potwierdzony na `databento.com/support` |
| Temat | `GLBX.MDP3 trades — semantics of \`sequence\`, \`flags\`/F_LAST, and ts_recv bar alignment` |
| Treść | zamrożona w §A, wysłana bez zmian |
| Wersja robocza utworzona | 2026-08-04, 10:50 UTC (`r-2030752981535618052`) |
| **Wysłano** | **2026-08-04, 10:51:53 UTC** przez właściciela projektu |
| ID wiadomości wysłanej | `19fcc66c2d5dcc50` |
| ID wątku | `19fcc64fb4b52d9f` |
| Autoodpowiedź | 2026-08-04, 10:52:16 UTC („We'll be back online in 3 hours") |
| **Odpowiedź merytoryczna** | **2026-08-04, 11:00:27 UTC** — Eric, Databento |
| ID wiadomości z odpowiedzią | `19fcc6e9c6c20e05` |
| System zgłoszeń | Intercom; **osobnego numeru sprawy nie przydzielono** — identyfikacja przez ID wątku |
| **Status sprawy** | **ODPOWIEDŹ OTRZYMANA — sprawa zamknięta** |
| Przypomnienie | **niepotrzebne** — odpowiedź przyszła po ośmiu minutach |

Odpowiedź jest **jednoznaczna i zmienia status D5-B**. Pełne brzmienie w §C,
interpretacja dla projektu — osobno, w §D.

**Odpowiedź zapisujemy w pełnym brzmieniu** w §C — bez parafrazy i bez skrótów.
Interpretacja dla projektu idzie osobno, do §D.

### Czego w wiadomości nie ma — kontrola przed wysyłką

Sprawdzone pozycja po pozycji: brak klucza API, brak jakichkolwiek danych
logowania, brak surowych plików w załączniku, brak informacji pozwalających
przejąć konto. Jedyne dane w wiadomości to **15 publicznych rekordów
transakcyjnych** z jednej sekundy sesji — informacja z publicznego strumienia
rynkowego, którą dostaje każdy abonent tego samego zbioru.

---

## A. Treść do wysłania (angielski, gotowa do wklejenia)

> **Subject:** GLBX.MDP3 `trades` — semantics of `sequence`, `flags`/`F_LAST`, and `ts_recv` bar alignment
>
> Hello,
>
> We are using the `trades` schema for a research project and would like to
> confirm the correct interpretation of a few fields before we build anything
> on top of our current assumptions. This is purely a question about reading
> the data correctly — we are not reporting a problem and not requesting
> any change.
>
> **Sample we are asking about**
>
> | | |
> |---|---|
> | Dataset | `GLBX.MDP3` |
> | Schema | `trades` |
> | Instrument | `MNQU6` (`stype_in=raw_symbol`) |
> | Range | 22 RTH sessions, 2026-07-01 … 2026-07-30, 09:30–16:00 America/New_York |
> | Records | 22,080,246 |
> | Client library | `databento` 0.82.0 (Python), `timeseries.get_range` → `.dbn.zst` |
>
> **What we observe across the whole sample**
>
> | Observation | Value |
> |---|---|
> | `action` | always `T` |
> | `flags` | **always 0**, in all 22,080,246 records |
> | `depth` | always 0 |
> | `side == NONE` | 4 records out of 22,080,246 |
> | distinct `sequence` values | ~88.9% of the fill count |
> | groups of `(ts_event, sequence, side)` | 19,837,327 |
> | largest such group | 15 fills |
> | `(ts_event, sequence)` pairs carrying **both** sides | 732 (0.0037% of groups) |
>
> **A concrete multi-price group** (2026-07-21, all 15 records share the same
> `ts_event`, `sequence` and `ts_in_delta`; prices ascend monotonically across
> 15 consecutive tick levels, one side only):
>
> ```
> ts_recv                          ts_event                         sequence   side action price     size flags depth ts_in_delta
> 2026-07-21 16:08:20.155257921Z   2026-07-21 16:08:20.153712211Z   176716970  B    T      29324.25     4     0     0       15122
> 2026-07-21 16:08:20.155257921Z   2026-07-21 16:08:20.153712211Z   176716970  B    T      29324.50     9     0     0       15122
> 2026-07-21 16:08:20.155257921Z   2026-07-21 16:08:20.153712211Z   176716970  B    T      29324.75     5     0     0       15122
> 2026-07-21 16:08:20.155257921Z   2026-07-21 16:08:20.153712211Z   176716970  B    T      29325.00     2     0     0       15122
> ...  (11 more rows, same key, prices 29325.25 … 29327.75)
> 2026-07-21 16:08:20.155257921Z   2026-07-21 16:08:20.153712211Z   176716970  B    T      29327.75    83     0     0       15122
> ```
>
> **Our questions**
>
> **Q1 — Semantics of `sequence` in `trades` for GLBX.MDP3.**
> Is `sequence` the MDP 3.0 packet/message sequence number, or an identifier of
> a single matching event? Concretely: are two fills sharing the same
> `(ts_event, sequence)` guaranteed to come from one matching event — one
> aggressing order consuming several resting orders or price levels — or only
> from one packet, which may contain unrelated events?
>
> **Q2 — `(ts_event, sequence)` pairs carrying both aggressor sides.**
> We find 732 such pairs (0.0037%). If `sequence` identified a single matching
> event, both sides should not appear under one pair. What produces these —
> counter wraparound, several events in one packet, implied matching, or
> something else? We currently exclude them from our analysis and would like to
> know whether that is the right response.
>
> **Q3 — Why is `flags` always 0?**
> The documentation describes `F_LAST` (last message in an event), `F_TOB`,
> `F_SNAPSHOT`, `F_MBP`. In our sample `flags == 0` in every one of 22 million
> records. Is `trades` for GLBX.MDP3 simply not setting flags, or is this a
> consequence of the DBN version, the encoding, or the delivery path we used?
>
> **Q4 — Is `F_LAST` available through another schema or delivery path?**
> If `F_LAST` were set, it would give a direct boundary for a matching event and
> our grouping rule would stop being an approximation. Is there a schema
> (`mbo`, `mbp-1`, `tbbo`) or a delivery mode where flags are preserved for
> this dataset?
>
> **Q5 — Canonical method for reconstructing one aggressing order.**
> If no field in `trades` is sufficient for this, what is the recommended
> method, and which schema is the minimum needed? We are asking before
> purchasing, not after.
>
> **Q6 — Bar alignment: `ts_recv` vs `ts_event`.**
> We reconstructed `ohlcv-1m` from `trades` twice — on 1 session and on 22
> sessions (8,400 bars). We match your bars exactly in open, high, low, close
> and volume — to the tick and to the contract — **only** when aggregating on
> `ts_recv`. Aggregating on `ts_event` produces roughly a dozen mismatches per
> session, with the volume differences summing to exactly zero (trades shift
> between adjacent minutes). Can you confirm that `ohlcv-*` bars for GLBX.MDP3
> are aggregated on `ts_recv`? This determines the observation-window boundary
> in our entire study.
>
> We are not asking for participant-level information or order-originator
> identifiers — only for the correct interpretation of the fields already
> present in the data we have.
>
> Thank you,

---

## B. Dlaczego to pytanie w ogóle powstało

Reguła grupowania `candidate_aggressor_event = (ts_event, sequence, side)`
jest w projekcie przyjęta **warunkowo**. Wynik `D5-B GO`
(`reports/D5_etap2_wyniki.md`) jest ważny dla tak zdefiniowanego agregatu
niezależnie od odpowiedzi — ale **nazwanie tej grupy jednym zleceniem agresora**
wymaga potwierdzenia od dostawcy. Bez niego mechanizm karty H017 musiałby
zostać opisany węziej.

Przykład z §A wygląda jak podręcznikowy sweep księgi jednym zleceniem
marketowym: jeden `ts_event`, jedna `sequence`, jedno `ts_in_delta`, jedna
strona, ceny rosnące monotonicznie przez 15 kolejnych poziomów. **To jest
przesłanka, nie dowód** — i właśnie dlatego pytamy.

---

## C. Odpowiedź Databento — pełna treść

Przepisana **w całości, bez parafrazy i bez skracania**, z pola `plaintextBody`
wiadomości `19fcc6e9c6c20e05` (2026-08-04, 11:00:27 UTC). Zachowana także uwaga
o długości pytania — należy do odpowiedzi i nie mam prawa jej usuwać.

> Jack,
>
> Thanks for reaching out. Happy to answer any questions you may have, but I
> think your LLM may be making these questions a bit longer and more complex
> than necessary. We have real humans respond to every message. Moving forward,
> if you absolutely must use an LLM to craft your questions for you, please at
> least ask that it do so in a concise manner.
>
> **Q1:** `sequence` is the original CME venue message sequence number. It is
> not a unique matching-event identifier. A CME Trade Summary message can
> contain multiple trade summaries, so records sharing `(ts_event, sequence)`
> are not guaranteed to represent one aggressing order or matching event.
>
> **Q2:** Pairs containing both aggressor sides can occur because one source
> message may contain multiple trade summaries. They are not necessarily caused
> by sequence wraparound or bad data. Excluding these groups is reasonable if
> your methodology requires an unambiguous single aggressor, but
> `(ts_event, sequence)` should not generally be used as that grouping key.
>
> **Q3:** This is expected for the `trades` schema. For GLBX.MDP3, `F_LAST` is
> meaningful in MBO, where it marks the last record for each instrument in an
> event. Databento accounts for event boundaries when deriving Trades and MBP
> schemas, so flags outside MBO can be ignored. This is not dependent on the
> DBN version, encoding, or delivery method.
>
> **Q4:** Use the `mbo` schema to obtain `F_LAST`. Changing between historical
> streaming, batch delivery, DBN, CSV, or JSON will not add this information to
> the `trades` schema. MBP-1 and TBBO are derived schemas and do not provide the
> passive fill detail needed for this purpose.
>
> **Q5:** MBO is the minimum recommended schema for reconstructing individual
> matching events and the resting orders consumed. Each CME Trade Summary is
> normalized into a Trade record, followed by associated passive-order Fill
> records. The Trade record may also contain the aggressing `order_id`, when CME
> provides one. Use `F_LAST` to identify the per-instrument event boundary
> rather than grouping Trades by `(ts_event, sequence)`.
>
> **Q6:** Confirmed. GLBX.MDP3 OHLCV bars are aggregated using `ts_recv`, and
> the resulting interval timestamp is exposed as the bar's `ts_event`. This is
> why resampling Trades on their `ts_recv` index reproduces the published bars,
> while using the trade-level `ts_event` can move records across adjacent
> interval boundaries.
>
> **Eric**
> Databento

---

## D. Interpretacja dla projektu

Pisana **osobno od §C**, żeby nigdy nie pomylić tego, co powiedział dostawca,
z tym, co z tego wywnioskowaliśmy.

### Który scenariusz się ziścił

Scenariusze były ustalone **przed** poznaniem odpowiedzi. Ziścił się **drugi**:
`sequence` identyfikuje wiadomość, nie zdarzenie dopasowania — z zaostrzeniem,
bo metodą kanoniczną okazuje się inny schemat (`mbo`), a nie inny sposób
grupowania w `trades`.

| Pytanie | Co rozstrzyga | Skutek dla projektu |
|---|---|---|
| **Q6** | `ts_recv` **oficjalnie potwierdzone** — bary agregowane po `ts_recv`, a znacznik interwału wystawiany jako `ts_event` bara | **Potwierdza całą decyzję o granicach okien 60 s.** Nasze dwukrotne odtworzenie 8 400 barów co do ticka miało poprawną przyczynę, nie zbieg okoliczności. |
| **Q1, Q2** | `sequence` to numer sekwencyjny wiadomości CME; jedna wiadomość może zawierać wiele Trade Summaries, także po przeciwnych stronach | **Unieważniają interpretację `candidate_aggressor_event`.** Wyjaśniają 732 pary dwustronne — to nie defekt danych, tylko normalna struktura protokołu. |
| **Q3** | `flags == 0` jest oczekiwane dla `trades`; nie zależy od wersji DBN, kodowania ani sposobu dostarczenia | Zamyka hipotezę o błędzie po naszej stronie. |
| **Q4, Q5** | `mbo` jest **minimalnym właściwym schematem**; `F_LAST` wyznacza granicę zdarzenia per instrument; Trade + Fill + czasem `order_id` agresora | Wskazuje jedyną kanoniczną drogę rekonstrukcji. MBP-1 i TBBO **nie wystarczą** — brak informacji o pasywnych wypełnieniach. |

### Co to znaczy dla D5-B

**Obliczenia D5-B nie są numerycznie błędne. Błędna jest interpretacja głównej
zmiennej A jako liczby zdarzeń agresora.**

Zamrożona specyfikacja mówiła, że **główny werdykt pochodzi wyłącznie z A**,
a A opiera się na grupowaniu, które dostawca właśnie oficjalnie odrzucił.
Dlatego werdykt zmienia się z `GO` na:

```
D5-B INCONCLUSIVE — niewłaściwa jednostka pomiaru
```

**Nie `NO-GO`**, bo nie wykazaliśmy, że mechanizm nie działa: pola `side` są
poprawne, `trades` odtwarzają bary idealnie, a B i C też miały niski VIF.
Problemem jest **niemożność odtworzenia pojedynczego zdarzenia agresora
z wybranego schematu**, a nie brak zjawiska.

**B i C nie mogą teraz zastąpić A.** Były kontrolami pomiaru; zmiana głównej
definicji po zobaczeniu wyników złamałaby regułę zamrożoną przed zakupem.

### Lekcja metodologiczna

Empirycznie grupowanie wyglądało niemal idealnie: monotoniczność cen w grupach,
tylko 0,0037% grup dwustronnych, A, B i C zgodne co do VIF. **Interpretacja
i tak była błędna.** Ładna zgodność empiryczna nie zastępuje semantyki
protokołu źródłowego — zapisane jako wniosek **W014**.

To nie jest porażka D5. To poprawne działanie audytu: niewłaściwa jednostka
wykryta **przed** H017, przed jakimkolwiek pomiarem przyszłego zwrotu i przed
próbą nr 1. **Licznik prób: 0.**

### Uwaga Erica o długości wiadomości

Zasadna i przyjęta jako reguła **R9**. Odpowiedź merytoryczna była przy tym
w pełni konkretna i rozstrzygnęła wszystkie sześć punktów.
