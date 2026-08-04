# Pytanie do wsparcia Databento — semantyka `sequence`, `flags`, `F_LAST`, `ts_recv`

## Status wysyłki

| | |
|---|---|
| Kanał ustalony | **support@databento.com** — potwierdzony na `databento.com/support` (HTTP 200, 2026-08-03) |
| Alternatywa | formularz kontaktowy `databento.com/contact` |
| Treść | zamrożona niżej w §A, gotowa do wysłania bez zmian |
| **Wysłano** | **NIE** |
| Powód | w tej sesji **nie ma włączonego kanału poczty** — konektor Gmail jest zainstalowany, ale `enabledInChat: false`, więc jego narzędzia nie są załadowane. Nie mam żadnego innego sposobu wysłania wiadomości. |
| Data i godzina wysyłki | *do uzupełnienia po wysłaniu* |
| Identyfikator zgłoszenia | *do uzupełnienia po wysłaniu* |
| Status sprawy | **oczekuje na wysłanie** |
| Przypomnienie | jedno krótkie, po **pięciu dniach roboczych** od wysyłki |

**Nie napisałem, że wysłałem, bo nie wysłałem.** Żeby to ruszyło, potrzebne jest
jedno z dwojga: włączenie konektora Gmail w ustawieniach tej rozmowy, albo
wklejenie treści z §A ręcznie. Po wysłaniu uzupełniam tabelę wyżej.

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

*Pusta do czasu otrzymania. Wklejamy w całości, bez parafrazy i bez skracania.*

---

## D. Interpretacja dla projektu

*Pusta do czasu otrzymania odpowiedzi. Pisana osobno od §C, żeby nigdy nie
pomylić tego, co powiedział dostawca, z tym, co z tego wywnioskowaliśmy.*

Cztery scenariusze i ich konsekwencje są ustalone **z góry**, przed poznaniem
odpowiedzi:

| Odpowiedź | Konsekwencja |
|---|---|
| `sequence` identyfikuje jedno zdarzenie agresora | `candidate_aggressor_event` → `aggressor_event`; reguła zatwierdzona; 732 pary dwustronne zostają jawnie wykluczonym przypadkiem brzegowym; **droga do H017 otwarta** |
| `sequence` identyfikuje pakiet z potencjalnie kilkoma zleceniami | nie wolno nazywać grupy jednym zdarzeniem agresora; wynik D5-B pozostaje ważny dla agregatu empirycznego, ale nie potwierdza mechanizmu znaku kolejnych zleceń; stosujemy metodę kanoniczną dostawcy i **przeliczamy D5-B przy niezmienionych progach**; `GO` po przeliczeniu → H017; wymóg MBP/MBO → osobna decyzja o schemacie, koszcie i dysku |
| `trades` nie wystarcza, potrzebne MBP/MBO | obecna agregacja zostaje kontrolą empiryczną; **H017 w obecnej postaci nie powstaje**; wyceniamy minimalny schemat, **nie kupujemy automatycznie**; sprawdzamy konieczność dla mechanizmu i mieszczenie się na dysku |
| brak potwierdzenia, ale A/B/C zgodne | nadal **nie wolno** twierdzić, że rozpoznaliśmy pojedyncze zlecenie; karta możliwa wyłącznie na zmiennej empirycznej, z mechanizmem opisanym węziej: *„technicznie zdefiniowane grupy agresywnych wypełnień wykazują trwałość znaku"*, **nie** *„zidentyfikowane zlecenia jednego metaorderu"* |
| brak odpowiedzi | jedno przypomnienie po pięciu dniach roboczych; **H017 nie powstaje dlatego, że wsparcie milczy** |
