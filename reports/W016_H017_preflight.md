# W016 — pre-flight H017: kontynuacja przepływu agresywnego

Karta: [`hypotheses/H017.md`](../hypotheses/H017.md), zamrożona w `efa4a8f` przed napisaniem tego kodu. Kod: `research/W016_H017_preflight.py`. Dane: `data/clean/d5b2_okna/` (lipiec 2026 — **zbiór deweloperski**).

**Werdykt: `REJECTED (pre-flight)` — BRAK — brak trwalosci znaku, mechanizm nie istnieje.**

Par (t → t+1): **8 356** w **22** sesjach. Ruch Δ: średnia -0,20 pkt, odchylenie 15,06 pkt. **Licznik prób: 0.**

## Przewidywania P1–P6 (progi z karty §9)

| # | Wynik | Próg | |
|---|---|---|---|
| P1 trwałość znaku | korelacja `I_t`–`I_t+1` **0,057**, dodatnia w **17/22** sesjach | > 0 i ≥ 18/22 | ❌ |
| P2 przyrost ponad momentum | wsp. **-1,978** pkt, t = **-0,77** | > 0 i t ≥ 2,0 | ❌ |
| P3 monotoniczność | rośnie w **2/4** krokach | ≥ 3/4 i Q5 > Q1 | ❌ |
| P4 symetria | Q5 **0,11**, Q1 **-0,09** pkt | Q5 > 0, Q1 < 0 | ✅ |
| P5 koszty | (Q5 − Q1)/2 = **0,10** pkt | ≥ 1,10 pkt | ❌ |
| P6 stabilność | dodatni w **10/22** sesjach; jackknife -3,108 … -0,655 | ≥ 15/22 i jackknife > 0 | ❌ |

Średnie `Δ̃` (pkt) w kwintylach `I_t`, Q1 → Q5: -0,09 · -0,39 · 0,46 · -0,09 · 0,11

Stress-test ×2 (2,20 pkt, raportowany, nie rozstrzyga): NIE spełniony.

## Ablacje (karta §10 — raportowane, nie zmieniają werdyktu)

| # | Ablacja | wsp. | t | (Q5 − Q1)/2 |
|---|---|---|---|---|
| — | **`A` (karta)** | -1,978 | -0,77 | 0,10 |
| 1 | `A` → `C` (wolumen) | -1,072 | -0,56 | 0,36 |
| 2 | `A` → `B` (rekordy Trade) | -1,810 | -0,76 | 0,14 |
| 3 | bez kontroli `m_t` | 2,471 | 0,86 | — |
| 4 | samo `m_t` (benchmark momentum) | 0,027 | 1,30 | — |

## Opisowe: normalizacja (nie wchodzi do werdyktu)

| Grupa | par | wsp. przy `I_t` | t |
|---|---|---|---|
| stara | 1760 | -5,660 | -1,37 |
| nowa | 6596 | -0,748 | -0,22 |

## Czego ten raport NIE mówi

Lipiec jest zbiorem deweloperskim: 22 sesje to 5% podłogi N ≥ 400 (karta §5). Pre-flight może kartę **odrzucić**, nie może jej **potwierdzić**. Błędy grupowane przy 22 grupach są przybliżeniem.
