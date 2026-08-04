# Uruchomienie projektu na maszynie lokalnej

Dokument powstał, bo etap D5-B2 wymaga dysku, którego nie ma w środowisku
zdalnym: miesiąc MBO to ~15 GB plików surowych, a warunek zakupu mówi
o **co najmniej 100 GB wolnego miejsca** przed startem.

---

## 1. Co się właściwie przenosi

**Repozytorium, nie środowisko.** Sesja zdalna działa w efemerycznym
kontenerze w chmurze i nie ma żadnej drogi do Twojego komputera. Żeby agent
pracował na Twoim dysku, musi działać **w Twoim terminalu** — przez Claude Code
zainstalowane lokalnie.

Po instalacji nic się nie zmienia w sposobie pracy: te same narzędzia, ten sam
repozytorium, ta sama bramka `scripts/check_all.sh`. Zmienia się jedno —
dochodzi dostęp do Twojego dysku i znika limit 26 GB.

### Co przychodzi z klonem

| | |
|---|---|
| Historia gita | ~417 MB |
| `data/clean/` — parquety MNQ, NQ, ES, K6, kalendarze | **266 MB, w repozytorium** |
| `golden/baseline.json` | tak |
| Kod, testy, raporty, specyfikacje | tak |

**Bramka silnika z rozdz. 5.6 działa od razu po klonie** — dane oczyszczone są
wersjonowane, więc nie trzeba niczego pobierać, żeby uruchomić pełne testy.

### Czego NIE ma w klonie

`data/raw/` (1,5 GB) jest w `.gitignore` — surowe `.dbn.zst` nigdy nie trafiają
do repozytorium. Dotyczy to również jednodniowej próbki MBO.

---

## 2. Instalacja

### 2.1 Claude Code

Instrukcja: <https://claude.com/claude-code>. Po instalacji uruchamiasz `claude`
w katalogu repozytorium.

### 2.2 Python

Wymagany **3.11 lub 3.12** (`pyproject.toml` przypina `>=3.11,<3.13` — zgodnie
z rozdz. 11.2 dokumentu, `ib_async` ma problemy z nowszymi).

### 2.3 Repozytorium i zależności

```bash
git clone https://github.com/lippaol-art/G.git
cd G
git checkout claude/financial-market-strategy-8mb1y1

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev,validation,data]"
pip install ruff mypy pytest-cov
```

`data` jest potrzebne dla `databento`, `validation` dla `arch` i `scikit-learn`.
Bez `validation` moduły `spa.py` i `dsr.py` **po cichu schodzą na ścieżkę
zapasową** — ich ścieżka główna nie zostałaby wykonana ani razu.

---

## 3. Zmienne środowiskowe

### 3.1 Klucz Databento

**Nigdy nie trafia do żadnego pliku w repozytorium.** Wyłącznie zmienna
środowiskowa; skrypty czytają ją przez `os.environ` i failują z czytelnym
błędem, gdy jej brak.

```bash
export DATABENTO_API_KEY="db-..."           # Linux / macOS
```
```powershell
$env:DATABENTO_API_KEY = "db-..."           # Windows PowerShell, ta sesja
[Environment]::SetEnvironmentVariable("DATABENTO_API_KEY", "db-...", "User")
```

**Rekomendacja rotacji pozostaje w mocy.** Obecny klucz przeszedł przez
transkrypt rozmowy. Przy okazji przenosin na nową maszynę to naturalny moment,
żeby wygenerować nowy w panelu Databento i stary unieważnić.

### 3.2 Magazyn danych surowych

```bash
export PROJECT_G_DATA_ROOT="/mnt/dane/projekt_g"    # dysk z >= 100 GB wolnego
```
```powershell
$env:PROJECT_G_DATA_ROOT = "D:\dane\projekt_g"
```

Kieruje **wyłącznie danymi surowymi**. `data/clean/` zostaje w repozytorium
niezależnie od tej zmiennej — to artefakt wersjonowany, na którym stoi
`hash_danych` golden baseline'u. Bez zmiennej wszystko działa jak dotąd,
względem katalogu repozytorium.

---

## 4. Weryfikacja instalacji

```bash
bash scripts/check_all.sh
```

Musi zakończyć się `BRAMKA ZIELONA`. Sześć kroków: ruff, mypy, testy
z pokryciem, strażnicy niezmienników, bramka silnika na realnych danych
(rozdz. 5.6) i golden baseline.

Jeśli krok z pokryciem wywali się na nieznanym argumencie `--cov`, to znaczy,
że `pytest` z `PATH` pochodzi z innego środowiska niż `pytest-cov` — skrypt
używa `python3 -m pytest` właśnie z tego powodu, ale w niektórych konfiguracjach
trzeba jeszcze aktywować venv.

**Golden baseline musi wyjść `ZGODNY`.** Jeśli pokazuje różnicę zaraz po
klonie, coś jest nie tak z instalacją — nie kontynuuj.

---

## 5. Test 1 — lokalne odtworzenie D5-C, bez podwójnego kosztu

Warunek mówi o powtórzeniu D5-C lokalnie i porównaniu JSON co do bajtu. Wymaga
to pliku MBO z sesji `2026-07-30`, którego **nie ma w repozytorium**.

**Nie kupuj go osobno.** Ta sesja wchodzi w skład 22 sesji miesiąca
(3,5961 USD z 78,6044 USD), więc naturalna kolejność jest taka:

1. pobierz **tylko** `2026-07-30` jako pierwszą sesję zakupu miesiąca,
2. sprawdź SHA-256 wobec `data/manifest_d5c.json`:
   `3e6f023d3d6978a23af9a49256f68dd2862420b32eadab80c7b23abf0974ac42`,
3. uruchom `python3 scripts/audit_d5_etap3.py`,
4. porównaj `reports/D5_etap3_wyniki.json` z wersją z repozytorium **co do
   bajtu**,
5. dopiero po zgodności pobieraj pozostałe 21 sesji.

Test 1 staje się wtedy **pierwszym krokiem zakupu**, a nie osobnym wydatkiem.

Jedyny realnie dodatkowy koszt to plik `trades` dla tej sesji (**1,2318 USD**),
potrzebny do kontroli Q7 — rekonstrukcji schematu `trades` z MBO. Bez niego
JSON nie będzie identyczny, bo sekcja Q7 się nie policzy.

### Wymagany wynik

```
842 757 kopert F_LAST
767 588 kopert z jednym Trade
 75 169 kopert z wieloma Trade
      0 niezgodności
      0 niewyjaśnionych
    986 dotkniętych brakiem snapshotu
  7 362 z Fill agresora
```

**Różnica w czasie lub RAM jest dopuszczalna. Różnica w wynikach nie.**

Dla odniesienia, pomiary ze środowiska zdalnego: 281,9 s, szczytowy RSS
2,106 GB, zużycie dysku poza plikiem surowym zerowe.

---

## 6. Test 2 — już wykonany

Dry run D5-B2 (`scripts/dry_run_d5b2.py`) przeszedł osiem niezmienników
strukturalnych w środowisku zdalnym — `reports/D5_b2_dry_run.md`. Lokalnie
warto go powtórzyć po Teście 1, ale nie jest to warunek blokujący.

---

## 7. Warunki automatycznej zgody na zakup miesiąca

Zakup może ruszyć **bez kolejnej decyzji**, gdy wszystkie są spełnione:

| # | Warunek | Gdzie sprawdzić |
|---|---|---|
| 1 | CI zielone dla aktualnego commita | GitHub Actions |
| 2 | lokalny D5-C daje **identyczny JSON** | §5 |
| 3 | dry run D5-B2 przechodzi niezmienniki | **spełniony** |
| 4 | **≥ 100 GB wolnego** przed zakupem | `df -h` / `Get-PSDrive` |
| 5 | ponowna wycena 22 sesji **≤ 82,00 USD** | `metadata.get_cost` |
| 6 | zakres: te same 22 sesje RTH | `docs/D5_ETAP4_SPEC.md` |
| 7 | schemat `mbo`, instrument `MNQU6` | jw. |
| 8 | brak rozszerzenia okna do północy UTC | jw. |

**Jeden niespełniony warunek zatrzymuje zakup.**

---

## 8. Reguły pobierania miesiąca

- dzień po dniu, bezpośrednio do `PROJECT_G_DATA_ROOT`,
- dla każdej sesji zapisać: zakres UTC i ET, cenę, liczbę rekordów, rozmiar,
  SHA-256, wynik parsowania, status kompletności,
- **żadnego ślepego automatycznego retry po błędzie 504** — najpierw sprawdzić,
  czy powstał plik kompletny czy częściowy, i ponawiać **wyłącznie** brakującą
  lub uszkodzoną sesję. Inaczej ryzykujemy podwójne naliczenie kosztu,
- downloader odmawia kontynuacji, gdy: suma wycen przekroczy 82 USD, zabraknie
  miejsca, istniejący plik nie przejdzie kontroli kompletności, zakres różni
  się od manifestu albo parser zgłosi brak oczekiwanych rekordów lub granic.

**Istnienie pliku nie jest dowodem kompletności.** Ta reguła powstała po tym,
jak przerwany transfer zostawił obciętą sesję, która parsowała się bez błędu.

---

## 9. Czego nie robimy po przeniesieniu

Nie zmieniamy progów z §8, nie zmieniamy definicji jednostki, nie mierzymy
przyszłych zwrotów ani P&L, nie tworzymy H017. **Licznik prób pozostaje 0**
aż do pierwszego kanonicznego backtestu po ewentualnym `D5-B2 GO`.
