# Manifest danych `trades`

## MNQ, sesja 2026-07-30 — D5 Etap 1

| Pole | Wartość |
|---|---|
| Dataset | `GLBX.MDP3` |
| Schemat | `trades` |
| Symbol | `MNQU6` (`stype_in="raw_symbol"`) |
| Okno | `2026-07-29T22:00Z` → `2026-07-30T21:00Z` |
| `trade_date` | `2026-07-30` (jedna sesja, potwierdzone) |
| **Koszt faktyczny** | **2,1240 USD** |
| Limit zatwierdzony | 2,15 USD |
| Rekordów | 1 696 891 |
| Plik | `data/raw/mnq_trades_2026-07-30.dbn.zst` |
| Rozmiar | 31 107 991 B (31,1 MB skompresowane) |
| **SHA-256** | `dfee7684c7bdce99272d91567752d7220291896bd8ebf694c281b6efab4df172` |
| Pobrano (UTC) | `2026-08-03T20:02:23` |
| Biblioteka | `databento` 0.82.0 |
| Wycena `metadata` | 2026-08-03, identyczna z kosztem faktycznym |
| Koszt per mln rekordów | **1,2517 USD/mln** |

Specyfikacja zamrożona przed zakupem: `docs/D5_ETAP1_SPEC.md`
(commit `41d3eee`), korekta budżetu `953b5ec`.

Plik `.dbn.zst` **nie jest commitowany** — `data/raw/` jest w `.gitignore`.
Odtworzenie: parametry powyżej + `metadata.get_cost` przed ponownym zakupem.

### Budżet

| Pozycja | Kwota |
|---|---|
| Stan przed | 62,42 USD |
| Etap 1 | −2,1240 USD |
| **Stan po** | **60,2960 USD** |

Wydatek projektu łącznie: 7,82 (Gen1) + 2,1240 = **9,9440 USD**.

### Przeznaczenie próbki

**Kontrola techniczna, nie badanie.** Dziewięć kontroli Etapu 1 nie liczy
zwrotów, P&L ani progów. Licznik prób pozostaje **0**.

Zgodnie z regułą ekspozycji na dane: ta sesja została **obejrzana**, więc
gdyby kiedykolwiek weszła do próby badawczej, jest **development only**.
Jedna sesja z 250 rocznie — wpływ pomijalny, ale odnotowany.
