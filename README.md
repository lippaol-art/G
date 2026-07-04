# 🧠 QuizMaster — Twoja prywatna wersja Quizleta

Prywatna aplikacja do nauki fiszek, inspirowana funkcjami Quizleta — ale **bez kont, bez reklam, bez dziennych limitów i bez wysyłania danych na żaden serwer**. Wszystkie zestawy są zapisywane wyłącznie w Twojej przeglądarce (localStorage).

## 🚀 Jak uruchomić

Nie potrzeba żadnej instalacji ani internetu:

1. **Najprościej:** otwórz plik `index.html` w przeglądarce (dwuklik).
2. **Albo lokalny serwer** (zalecane, jeśli chcesz mieć wspólne dane niezależnie od ścieżki pliku):

   ```bash
   python3 -m http.server 8000
   # otwórz http://localhost:8000
   ```

## 📚 Tryby nauki (jak w Quizlecie)

| Tryb | Opis |
|---|---|
| 🃏 **Fiszki** | Przeglądanie i odwracanie kart, tasowanie, czytanie na głos (synteza mowy), skróty klawiszowe (spacja, strzałki) |
| 🎓 **Ucz się** | Tryb adaptacyjny — nowe pojęcia dostają pytania wielokrotnego wyboru, potem pisanie; pojęcie jest „opanowane" po dwóch poprawnych odpowiedziach z rzędu |
| ✍️ **Pisanie** | Wpisujesz odpowiedzi z klawiatury; błędne pytania wracają na koniec rundy |
| 📝 **Test** | Konfigurowalny sprawdzian (wybór / pisanie / prawda-fałsz), z oceną procentową i przeglądem odpowiedzi |
| ⚡ **Dopasowanie** | Gra na czas — dopasuj pary pojęcie–definicja; błąd to +1 s kary; aplikacja zapamiętuje Twój rekord |

## ✨ Pozostałe funkcje

- **Tworzenie i edycja zestawów** — dowolna liczba pojęć, opisy zestawów
- **Szybki import z tekstu** — wklej listę w formacie `pojęcie - definicja` (albo rozdzielane tabulatorem / średnikiem), po jednym wpisie na linię
- **Eksport / import JSON** — kopia zapasowa wszystkich zestawów albo pojedynczego zestawu; przenoszenie danych między przeglądarkami i urządzeniami
- **Śledzenie postępów** — status każdego pojęcia (nowe / w trakcie / opanowane) widoczny w zestawie
- **Wyszukiwarka zestawów**
- **Ciemny motyw**, responsywny układ (działa też na telefonie)

## 🔒 Prywatność

- Zero kont i logowania
- Zero zapytań sieciowych — aplikacja działa w pełni offline
- Dane trzymane w `localStorage` przeglądarki; kopię zapasową robisz przyciskiem **Eksport**

## 🛠 Technologia

Czysty HTML + CSS + JavaScript (bez frameworków, bez builda, bez zależności).

```
index.html      – struktura aplikacji
css/style.css   – style (ciemny motyw)
js/app.js       – cała logika: zestawy, tryby nauki, import/eksport
```
