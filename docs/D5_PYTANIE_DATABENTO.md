# Pytanie do wsparcia Databento — semantyka `sequence`, `flags`, `F_LAST`

**Status:** przygotowane, **niewysłane**. Wysyłka i treść odpowiedzi wymagają
decyzji właściciela projektu.
**Kontekst:** `docs/D5_ETAP2_SPEC.md`, wynik `reports/D5_etap2_wyniki.md`.
**Po co:** reguła grupowania `candidate_aggressor_event` jest w projekcie
przyjęta **warunkowo**. Odpowiedź musi być dołączona do dokumentacji, zanim
powstanie karta H017.

---

## 1. Co zmierzyliśmy (dane, na których opieramy pytanie)

Próbka: `GLBX.MDP3`, `MNQU6`, schemat `trades`, 22 sesje RTH lipca 2026
(09:30–16:00 America/New_York), **22 080 246 wypełnień**.

| Obserwacja | Wartość |
|---|---|
| `action` | zawsze `T` |
| `flags` | **zawsze 0** — w całej próbce, bez wyjątku |
| `depth` | zawsze 0 |
| `side == NONE` | **4 rekordy na 22 080 246** |
| `sequence` unikalnych | ~88,9% liczby wypełnień (przykład: 688 917 z 774 942) |
| Grup `(ts_event, sequence, side)` | 19 837 327 |
| Największa grupa | 15 wypełnień |
| Par `(ts_event, sequence)` z **obiema** stronami | 732 (0,0037% grup) |

---

## 2. Pytania

**P1. Semantyka `sequence` w `trades` dla GLBX.MDP3.**
Czy `sequence` jest numerem sekwencyjnym pakietu/wiadomości MDP 3.0, czy
identyfikatorem zdarzenia dopasowania? Konkretnie: czy dwa wypełnienia
o **tym samym** `(ts_event, sequence)` pochodzą z gwarancją z jednego zdarzenia
dopasowania (jedno zlecenie agresora zdejmujące kilka poziomów/zleceń
przeciwstawnych), czy tylko z jednego pakietu, który może zawierać zdarzenia
niepowiązane?

**P2. Pary `(ts_event, sequence)` z obiema stronami agresora.**
Zaobserwowaliśmy 732 takie pary (0,0037%). Jeśli `sequence` identyfikuje jedno
zdarzenie dopasowania, obie strony w jednej parze nie powinny wystąpić.
Co jest źródłem tych przypadków — zawinięcie licznika, wiele zdarzeń w jednym
pakiecie, implied matching, czy coś jeszcze? **Wykluczamy je z analizy**, ale
chcemy wiedzieć, czy to właściwa reakcja.

**P3. Dlaczego `flags` jest zawsze 0.**
Dokumentacja opisuje `F_LAST` (ostatnia wiadomość w zdarzeniu),
`F_TOB`, `F_SNAPSHOT`, `F_MBP`. W naszej próbce `flags == 0` w każdym
z 22 mln rekordów. Czy `trades` dla GLBX.MDP3 w ogóle nie ustawia flag, czy
jest to konsekwencja formatu/wersji DBN albo drogi dostarczenia
(`timeseries.get_range` → `.dbn.zst`, biblioteka `databento` 0.82.0)?

**P4. Czy `F_LAST` jest dostępne w innym schemacie lub innej ścieżce dostępu.**
Jeśli `F_LAST` byłoby ustawiane, dawałoby **bezpośrednią** granicę zdarzenia
agresora i nasza reguła grupowania przestałaby być przybliżeniem. Czy istnieje
schemat (`mbo`, `mbp-1`, `tbbo`) albo tryb dostarczenia, w którym dla tego
zbioru danych flagi są zachowane?

**P5. Kanoniczna metoda rekonstrukcji jednego zlecenia agresora.**
Jeśli żadne pole w `trades` nie wystarcza, jaka jest rekomendowana metoda —
i który schemat jest do tego minimalnie wystarczający? Pytamy przed zakupem,
nie po.

---

## 3. Nasze ustalenie, które warto potwierdzić lub zdementować

Rekonstruowaliśmy `ohlcv-1m` z `trades` dwukrotnie — na 1 sesji (Etap 1)
i na 22 sesjach (Etap 2, 8 400 barów). Zgodność co do jednego bara
w `open`, `high`, `low`, `close` i `volume` uzyskujemy **wyłącznie** przy
agregacji po **`ts_recv`**. Agregacja po `ts_event` daje kilkanaście
niezgodności na sesję, z sumą różnic wolumenu równą zero (transakcje
przenoszą się między sąsiednimi minutami).

**P6.** Czy potwierdzają Państwo, że bary `ohlcv-*` dla GLBX.MDP3 są
agregowane po `ts_recv`? To jest dla nas ustalenie o dużym znaczeniu —
decyduje o granicy okna obserwacji w całym badaniu.

---

## 4. Czego NIE pytamy

Nie pytamy o dane o uczestnikach, identyfikatory zleceniodawców ani cokolwiek,
co wykraczałoby poza publiczny strumień rynkowy. Interesuje nas wyłącznie to,
jak poprawnie odczytać semantykę pól, które już mamy.
