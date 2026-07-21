# propbot — setup, krok po kroku

Przewodnik uruchomienia od zera do handlu na koncie **demo**. Trzy fazy:
**Telegram → VPS + MT5 demo → backtest/forward test**.

> ⚠️ **Bezpieczeństwo:** token bota, hasło MT5 i klucz API trafiają **wyłącznie
> do pliku `.env` na VPS**. Nigdy nie wklejaj ich tutaj w czacie ani do repo.

---

## Faza 1 — Telegram (5 min, bez VPS)

1. W Telegramie napisz do **@BotFather** → `/newbot` → nazwa → **skopiuj token**.
2. Napisz do swojego bota cokolwiek (np. „hi").
3. Sprawdź token i wyciągnij swój `chat_id`:
   ```bash
   export TELEGRAM_BOT_TOKEN=123456:ABC...
   python scripts/check_telegram.py
   ```
   → wypisze `✅ Bot OK` i `chat_id=...`.
4. Test w drugą stronę: `python scripts/check_telegram.py <chat_id>` → bot odpisze.

✅ **Efekt:** masz token + chat_id. Zapiszesz je w `.env` w Fazie 2.

---

## Faza 2 — VPS + MT5 demo

MT5 + Python działają **tylko na Windows**, więc potrzebny Windows VPS.

1. **VPS** (Londyn, blisko serwerów brokera): TradingFXVPS / ForexVPS (~$25–35/mc),
   albo tani Windows VPS (Contabo ~$12) na fazę testów.
2. Na VPS zainstaluj **MetaTrader 5**, otwórz **konto DEMO** (broker The5ers albo
   dowolne demo z indeksem US30), włącz **Algo Trading**
   (Tools → Options → Expert Advisors → Allow automated trading).
3. Sklonuj repo i zainstaluj zależności:
   ```bash
   pip install -r requirements.txt
   ```
4. **Zweryfikuj połączenie i specyfikację kontraktu** (ważne — decyduje o sizingu):
   ```bash
   python scripts/check_mt5.py US30 NAS100
   ```
   → wypisze konto + `pip_value_per_lot`, `volume_min`, i podgląd lotów przy 1%.
5. Skonfiguruj:
   - `cp config/settings.example.yaml config/settings.yaml` i wpisz **dokładny
     symbol** brokera (US30 / DJI30 / US30.cash…) + `pip_value_per_lot` i
     `volume_min` z kroku 4. Ustaw `execution.adapter: mt5`.
   - `cp .env.example .env` i wpisz `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`,
     `TELEGRAM_ALLOWED_CHAT_IDS`.
6. Odpal bota:
   ```bash
   python -m propbot.app
   ```
   albo dwuklik `scripts/run_vps.bat` (autostart — patrz niżej).

✅ **Efekt:** bot analizuje dzień → wysyła setup na Telegram → klikasz ✅ →
składa zlecenie na **demo** z pełną weryfikacją.

### Autostart na VPS (żeby wstawał po restarcie)
- `scripts/run_vps.bat` uruchamia bota w pętli (restart po awarii).
- Dodaj go do **Task Scheduler** → „At startup" → uruchamiaj przy logowaniu.

---

## Faza 3 — backtest + forward test

1. Eksport danych z MT5:
   ```bash
   python scripts/export_mt5_candles.py US30 --days 120 --out US30_M15.csv
   ```
2. Backtest pod regułami The5ers:
   ```bash
   python -m propbot.backtest.cli US30_M15.csv --symbol US30
   ```
   → krzywa: liczba trade'ów, win rate, profit factor, max DD, **naruszenia reguł**.
3. **Forward test na demo ≥ 30 dni** zanim kupisz challenge ($69).

---

## Co musisz mi dostarczyć (żebym mógł dalej pomagać)

Wklej **tutaj w czacie** (to NIE są sekrety):

1. **Output `python scripts/check_mt5.py`** — ustawię `symbol_specs` co do grosza.
2. **Dokładna nazwa symbolu** US30/NAS100 u Twojego brokera demo.
3. **Plik `US30_M15.csv`** (możesz wrzucić jako załącznik) — puszczę backtest i
   dostroję parametry (długość range'u, R:R, filtr dnia).
4. Decyzje: który **broker demo** i który **VPS** wybierasz (mogę doradzić).

❌ **Nie wysyłaj:** tokena bota, hasła MT5, klucza API — te tylko w `.env` na VPS.

---

## Co mogę jeszcze poprawić (backlog)

Priorytetowo:

1. **Zarządzanie pozycją po wejściu** — teraz wejście + stały SL/TP. Dodać:
   break-even po +1R, trailing stop, częściowe TP. *(największy wpływ na wynik)*
2. **Trwałość day-start equity przez restart** — dziś po restarcie bota w środku
   dnia referencja dziennej straty resetuje się do bieżącego equity (drobny bug
   przy trailing/daily-loss). Zapisać day-start do pliku stanu.
3. **Auto-downloader kalendarza** newsów (cron na VPS → JSON) — konwersja i
   walidacja już są, brakuje pobierania.
4. **Final-check LLM przy potwierdzeniu** — hook istnieje, podłączyć opcjonalnie.

Później:

5. Druga strategia (**VWAP reversion**) jako kandydat obok ORB.
6. **Walk-forward + sweep parametrów** w backteście (anty-overfitting z researchu).
7. Modelowanie **prowizji i swapów** w backteście (realniejsza krzywa).
8. Filtry sesji / dni tygodnia, dashboard statusu.

Powiedz, które z tych wziąć — proponuję zacząć od **1 i 2** (najbardziej ruszają
wynik i bezpieczeństwo), resztę po pierwszym backteście na realnych danych.
