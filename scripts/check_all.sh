#!/usr/bin/env bash
# Kanoniczna bramka lokalna — DOKLADNIE ten sam zestaw co CI.
#
# DLACZEGO ISTNIEJE. Push z bledami mypy przeszedl lokalnie, bo uruchomilem
# ruff i testy, a mypy pominalem. Cztery osobne komendy do zapamietania to
# cztery okazje do pominiecia jednej. Jeden entrypoint usuwa ten problem
# u zrodla, zamiast liczyc na pamiec.
#
# Kolejnosc i argumenty MUSZA odpowiadac `.github/workflows/ci.yml`.
# Rozjazd miedzy tym plikiem a CI czyni bramke bezuzyteczna, wiec kazda
# zmiana w workflow wymaga zmiany tutaj — i odwrotnie.
#
# Dodatek ponad CI: `golden_baseline.py --sprawdz`. CI go nie uruchamia
# (nie ma danych rynkowych), ale lokalnie jest to jedyna kontrola, ktora
# wychwytuje niezamierzona zmiane wynikow po refaktorze.
#
# UWAGA O WYWOLANIU: uzywamy `python3 -m pytest`, nie golego `pytest`.
# Na tej maszynie `pytest` z PATH to narzedzie uv z wlasnym, izolowanym
# srodowiskiem — nie widzi `pytest-cov` zainstalowanego obok, wiec krok
# z pokryciem wywracal sie na nieznanym argumencie. CI ma jedno
# srodowisko i tam goly `pytest` dziala; lokalnie musi byc `-m`.
#
# Uzycie:
#     bash scripts/check_all.sh            # pelna bramka
#     bash scripts/check_all.sh --szybko   # bez bramki 5.6 i bez golden

set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=.

SZYBKO=0
[[ "${1:-}" == "--szybko" ]] && SZYBKO=1

krok() { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; }

krok "1/6  Linter (ruff)"
ruff check engine validation scripts tests research

krok "2/6  Kontrola typow (mypy)"
mypy engine validation --ignore-missing-imports

krok "3/6  Testy + pokrycie"
python3 -m pytest -q \
  --ignore=tests/test_engine_on_real_data.py \
  --cov=engine --cov=validation \
  --cov-report=term-missing \
  --cov-fail-under=75

krok "4/6  Straznicy niezmiennikow projektu"
python3 -m pytest tests/test_guards.py -q

if [[ $SZYBKO -eq 1 ]]; then
  printf '\n\033[1mTRYB SZYBKI — pominieto bramke 5.6 i golden baseline.\033[0m\n'
  printf 'Przed pushem uruchom pelna bramke.\n'
  exit 0
fi

krok "5/6  Bramka silnika na realnych danych (PLAN rozdz. 5.6)"
python3 -m pytest tests/test_engine_on_real_data.py -q

krok "6/6  Golden baseline"
python3 scripts/golden_baseline.py --sprawdz

printf '\n\033[1;32mBRAMKA ZIELONA — mozna pushowac.\033[0m\n'
