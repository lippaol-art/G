# Rejestr kosztów danych Databento

Jawna księgowość wszystkich zakupów danych w projekcie. Powstał, gdy przenosiny
na maszynę lokalną wymusiły **ponowne pobranie sesji już raz kupionej** —
i decyzja właściciela projektu brzmiała: *„Nie ukrywamy tej duplikacji
w księgowości."*

**Ograniczenie, które trzeba znać:** Databento **nie udostępnia w API endpointu
rozliczeniowego** (`metadata` ma tylko `get_cost`, `get_record_count`,
`get_billable_size`). Wszystkie kwoty poniżej to **wyceny `metadata.get_cost`
dla dokładnie tych zapytań, które wykonano**, a nie odczyt z konta. Stan
kredytu należy weryfikować w panelu Databento.

---

## 1. Zakupy wykonane

| # | Etap | Zakres | Koszt | Uwagi |
|---|---|---|---|---|
| 1 | Gen1 | MNQ, NQ, ES `ohlcv-1m` 2019–2026 + warstwa K6 | **7,8200 USD** | udokumentowane w `data/manifest.md` |
| 2 | D5 Etap 1 | `trades` MNQU6, **pełna doba** 2026-07-30 | **2,1240 USD** | limit 2,15 — dotrzymany |
| 3 | D5-B | `trades` MNQU6, 21 sesji RTH lipca 2026 | **26,4060 USD** | wycena; górna granica **27,9160** |
| 4 | D5-C | `mbo` MNQU6, RTH 2026-07-30 | **3,5961 USD** | limit 4,00 — dotrzymany |

**Suma zakupów unikalnych: 39,9461 USD** (przy górnej granicy pozycji 3:
41,4561 USD).

### Dlaczego pozycja 3 ma dwie liczby

Pierwsze podejście urwało transfer sesji `2026-07-07` (koszt tej sesji
1,5098 USD) i ponowne pobranie mogło zostać naliczone drugi raz. Bez endpointu
rozliczeniowego **nie potrafię odczytać rzeczywistej kwoty**, więc podaję
granicę górną zamiast liczby, której nie zmierzyłem.

---

## 2. Duplikacja — ponowne pobranie 2026-07-30

| | |
|---|---|
| Plik | `mbo` MNQU6, RTH 2026-07-30 |
| Pierwszy zakup | **3,5961 USD** — środowisko zdalne, 2026-08-04 |
| Ponowne pobranie | **3,5961 USD** — maszyna lokalna |
| **Nadmiarowy wydatek** | **3,5961 USD** |

**Przyczyna:** dane surowe są w `.gitignore` i nigdy nie przechodzą przez
repozytorium, a dysk środowiska zdalnego znika razem z kontenerem. Plik ma
646 MiB przy limicie transferu 30 MiB — przeniesienie było niewykonalne.

**Czego duplikacja uniknęła:** plik `trades` (31,1 MB) zmieścił się w limicie
i został przeniesiony, oszczędzając **2,1240 USD**.

**Bilans przenosin: −3,5961 USD zapłacone drugi raz, +2,1240 USD uniknięte.**

Ta pozycja **nie zwiększa** kosztu unikalnej próbki miesięcznej — sesja
2026-07-30 i tak wchodzi w skład 22 sesji MBO. Jest natomiast realnym wydatkiem
z konta i dlatego stoi tu osobno.

---

## 3. Planowane, jeszcze niewykonane

| Pozycja | Koszt | Status |
|---|---|---|
| MBO, pozostałe **21 sesji** RTH lipca 2026 | **75,0083 USD** | 🔄 **W TRAKCIE.** Wycena 06.08.2026: 78,6044 USD za 22 sesje (limit 82,00); 2026-07-30 pominięta (SHA zgodny). Pobrano **3 z 21**: 2026-07-01, 07-02, 07-03 — **9,6916 USD**. Przerwane na 2026-07-06 (`Response ended prematurely`, plik częściowy 215,2 MB). |
| Cała miesięczna próbka MBO (22 sesje) | 78,6044 USD | limit zamrożony: **82,00 USD** |

Miesięczny downloader **musi wykryć 2026-07-30 jako kompletną i ją pominąć** —
inaczej naliczyłby ją trzeci raz.

---

## 3b. ⛔ ZAKUP WSTRZYMANY 06.08.2026 — dryf metadanych

Wycena tych samych, zamrożonych zapytań wzrosła z **78,6044** na **80,6729 USD**
(+2,63%), bo liczba rekordów wzrosła we **wszystkich 22 sesjach**. Analiza:
`docs/D5_DRYF_METADANYCH.md`.

Skutek dla tego rejestru: **nie da się dziś podać kosztu dokończenia zakupu**,
bo nie wiadomo, którą wersję danych kupujemy ani czy za tydzień nie będzie
trzeciej. Zgodnie z zasadą 4 podaję więc granicę, nie liczbę: pozostałe
18 sesji to **≤ 68 USD** przy wycenie z 06.08.

Pobrane i opłacone do tej pory: **4 z 22 sesji**. Plików **nie kasujemy** —
zgadzają się z liczbami, za które zapłacono.

---

## 3a. Pozycja do wyjaśnienia — 2026-07-06

| Pozycja | Kwota | Status |
|---|---|---|
| MBO 2026-07-06, pobranie przerwane w locie | **3,0388 USD** | ⚠️ **NIEPOTWIERDZONA** |

Transfer przerwał się po 215,2 MB z ~0,7 GB (`BentoError: Response ended
prematurely`). Plik jest niekompletny i bezużyteczny; sesja zostanie pobrana
ponownie, co naliczy 3,0388 USD **drugi raz**.

**Nie wiem, czy pierwsze, przerwane pobranie zostało naliczone.** Precedens
z D5-B (2026-07-07) sugeruje, że tak — Databento rozlicza zrealizowane
zapytanie, nie odebrane bajty — ale tego nie zmierzyłem i nie wolno mi tego
podawać jako faktu. **Do sprawdzenia na stronie zużycia konta Databento.**

Zgodnie z zasadą 3 tego rejestru duplikacja dostaje własną pozycję i nie
zostaje schowana w sumie zbiorczej. Po weryfikacji: albo wpis znika, albo
zamienia się w potwierdzoną pozycję duplikacji.

---

## 4. Zasady, które ten rejestr utrwala

1. **Każdy zakup ma zamrożony limit w commicie sprzed zakupu** (reguła R4).
   Limit zatrzymał zakup dwukrotnie i za każdym razem miał rację.
2. **Wycena bezpośrednio przed pobraniem**, nie sprzed kilku dni. Moje
   ekstrapolacje kosztu myliły się o 21% i o 40%.
3. **Nie ukrywamy ponownych naliczeń.** Duplikacja ma własną pozycję.
4. **Kwota, której nie zmierzyłem, jest podawana jako granica**, nie jako
   liczba.
