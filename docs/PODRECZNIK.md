# Podręcznik właściciela

Krok 12 Etapu 2. Dwanaście pytań, na które właściciel projektu powinien umieć
odpowiedzieć **własnymi słowami**, bez zaglądania do kodu.

Kryterium nie jest znajomość odpowiedzi, tylko umiejętność jej odtworzenia.
System, którego właściciel nie rozumie, jest systemem cudzym — a decyzja
o realnym kapitale należy wyłącznie do właściciela.

Odpowiedzi poniżej są wzorcami. Jeśli któraś brzmi obco, to jest miejsce, gdzie
projekt wyprzedził swojego właściciela i trzeba się cofnąć.

---

## 1. Po co w ogóle istnieje ten projekt i co znaczyłby jego sukces?

Znaleźć **strukturalną nieefektywność** w MNQ, udowodnić statystycznie, że nie
jest artefaktem przeszukiwania danych, i dopiero potem rozmawiać o kapitale.

Sukcesem **nie jest** ładna krzywa kapitału. Sukcesem jest jedno z dwojga:
strategia, która przechodzi bramkę DSR na niezależnych danych, **albo**
wiarygodne stwierdzenie, że przewagi nie ma. Drugie jest tańsze niż fałszywa
przewaga odkryta na realnym rachunku.

Stan po pierwszej generacji: **osiem kart odrzuconych, zero zużytych prób,
7,82 USD wydane.** To jest poprawny wynik, nie porażka.

## 2. Dlaczego licznik prób wynosi 0, skoro wykonano trzynaście badań?

Bo pre-flight bada **rozkłady i mechanizm**, a nie optymalizuje reguły ani nie
mierzy P&L. Nie ma czego przeszukiwać, więc nie ma czego deflować.

Każdy backtest zużywa próbę i podnosi poprzeczkę dla wszystkich pozostałych —
przy N_eff = 10 nawet Sharpe 1,2 nie przechodzi bramki DSR na naszej długości
danych. Dlatego karty zabija się **przed** wydaniem próby, nie po.

**Ważne zastrzeżenie, którego nie wolno pominąć:** „zero prób" nie znaczy „zero
ekspozycji na dane". Projektowanie każdej kolejnej karty było informowane
wcześniejszymi ustaleniami, a tego DSR nie mierzy. Licznik jest uczciwy wobec
formalnej definicji, ale nie jest pełnym opisem tego, ile razy popatrzyliśmy
w te same dane.

## 3. Skąd bierze się przewaga, jeśli w ogóle?

Z **struktury rynku**, nie ze wskaźnika. Pięć klas mechanizmów wewnątrz MNQ
(płynność, kotwice, przymus, reakcja na informację, mikrostruktura) plus szósta
dodana po audycie: **transmisja międzyrynkowa** — NQ żyje w sieci NQ–ES–SOX–
megacapy i to jest przestrzeń najsłabiej skomercjalizowana publicznie.

Wskaźnik nie jest przewagą. RSI liczy ten sam RSI wszystkim; jeśli to
wystarczało, przewaga zniknęłaby dawno temu.

## 4. Co to znaczy, że reguła jest „oryginalna"?

Cztery kroki, wszystkie obowiązkowe:

1. wskaż **najbliższy publiczny benchmark** i wpisz go do karty,
2. nazwij **różnicę w mechanizmie** — nie w parametrach,
3. udowodnij **przyrost OOS ponad benchmark** po kosztach,
4. zrób **ablacje**: usuń po kolei każdy „oryginalny" warunek; jeśli wynik się
   nie zmienia, warunek był dekoracją.

Poprzednia reguła brzmiała „połączenie dwóch znanych warunków tworzy
oryginalność" i była **błędna**. ORB plus filtr zmienności to dwie rzeczy znane,
a ich kombinacja jest standardem w każdej implementacji ORB — stara reguła
pobłogosławiłaby ją jako oryginalną.

## 5. Dlaczego jedna strategia może być statystycznie niecertyfikowalna, choć zarabia?

Bo **False Strategy Theorem** mówi, że przy ograniczonej długości danych
i wielu próbach nie da się certyfikować umiarkowanej przewagi. Liczby z naszych
danych (T ≈ 1500 dni, realny sufit projektu):

| Sharpe roczny | N_eff = 1 | N_eff = 5 | N_eff = 10 | N_eff = 30 |
|---|---|---|---|---|
| 0,8 | 0,974 ✅ | 0,776 ❌ | 0,647 ❌ | 0,452 ❌ |
| 1,2 | 0,998 ✅ | 0,958 ✅ | 0,912 ❌ | 0,803 ❌ |
| 1,5 | 1,000 ✅ | 0,993 ✅ | 0,981 ✅ | 0,943 ❌ |

Stąd dwa poziomy: **OBIECUJĄCA** (przechodzi bramki, brak certyfikacji — droga
dalej to forward paper trading, które dokłada T bez zużywania prób) i
**CERTYFIKOWANA** (DSR ≥ 0,95). Tylko drugi uprawnia do rozmowy o kapitale.

## 6. Dlaczego są dwie serie cen i co się stanie, jeśli je pomylić?

`px_raw` to cena, która realnie widniała na tablicy — do poziomów
międzysesyjnych. `px_adj` to cena po back-adjuście różnicowym — do zwrotów
i P&L.

Pomylenie w jedną stronę: P&L na serii surowej wstawia na każdym rolowaniu
sztuczny skok rzędu kilkudziesięciu punktów, na którym strategia „zarabia" bez
pokrycia. W drugą: poziom „wczorajszy szczyt" policzony na serii skorygowanej
rozjeżdża się w 4 dniach rolowania w roku.

Konkretna skala z prześledzonej transakcji: 5 marca 2024 różnica wynosiła
**2480,00 punktów**, czyli 4960 USD na kontrakt.

## 7. Dlaczego wykonanie następuje bar później niż sygnał?

Bo w momencie zamknięcia bara znamy jego close, ale **nie znamy trajektorii
ceny po nim**. Wykonanie w tym samym barze to lookahead — najczystsza forma
oszukiwania samego siebie.

Płacimy za to konkretną cenę: literatura mówi „wejście po cenie otwarcia sesji",
my wchodzimy minutę później. Ta sama cena obowiązuje benchmarki i karty własne,
więc porównanie między nimi zostaje sprawiedliwe.

## 8. Co się dzieje, gdy jeden bar dotyka i stop lossa, i take profitu?

Domyślnie **wygrywa SL**, bo dane M1 nie zawierają kolejności zdarzeń wewnątrz
minuty.

Ale to nie jest tylko konserwatyzm — to **skrzywienie statystyczne**:
systematycznie zaniża win rate strategii o wysokim R:R. Dlatego wynik przy
przeciwnej polityce (TP wygrywa) jest metryką **obowiązkową**, nie ciekawostką.
Docelowo sporne minuty rozstrzygamy sub-barami 1-sekundowymi z Databento —
policzone: 0,00024 USD za minutę, czyli 12 centów za 500 spornych minut w całej
historii.

## 9. Ile realnie kosztuje handel i dlaczego to często decyduje?

**2,20 USD round-turn** — 1,20 prowizji plus 1 tick poślizgu na stronę. Nie
3,20 USD: to był błąd arytmetyczny w pierwszej wersji dokumentu, wychwycony
przez audyt.

Przy 10 transakcjach dziennie to **5 522 USD rocznie**. Strategia o przewadze
2 punktów na transakcję oddaje w kosztach ponad połowę. Dlatego preferowane są
częstotliwości 0,5–3 transakcji dziennie, a stress-test ×2 jest warunkiem
bramki — bufor siedzi w teście, nie w bazie.

## 10. Co to jest golden baseline i po co go zamrażać?

Zapis tego, **co system liczy dzisiaj** — na pięciu warstwach: dane, silnik,
metryki, aparat walidacyjny, raporty. Osobny hash danych i osobny hash wyników,
żeby dało się odróżnić „zmieniły się dane" od „zmieniło się zachowanie kodu".

Po co: refaktor przy 11,8 tys. linii potrafi stworzyć błąd trudniejszy do
zauważenia niż duplikacja, którą usuwa. `--sprawdz` odpowiada na jedno pytanie:
czy po porządkach system liczy to samo.

Baseline został odtworzony **trzykrotnie z czystego stanu, bajt w bajt**. Bez
tego refaktor startowałby na niestabilnej podstawie i każda rozbieżność byłaby
niediagnostyczna.

## 11. Jaka jest różnica między bramką badawczą a operacyjną i dlaczego nie wolno ich mieszać?

**Badawcza** pyta: czy przewaga w ogóle istnieje i przechodzi SR/DSR.
**Operacyjna** pyta: czy przy tej przewadze da się utrzymać konto z limitem 10%.

Metryką operacyjną jest **prawdopodobieństwo utrzymania konta**, nie zwrot ani
Sharpe. Strategia o dobrym Sharpie może mieć nieakceptowalne ryzyko ruiny, jeśli
jej rozkład ma gruby lewy ogon.

Czego **nie wolno**: cofać się z bramki operacyjnej do badawczej. Gdyby karta
przeszła badanie, a potem okazała się zbyt ryzykowna dla konta, odpowiedzią jest
zmiana **wielkości pozycji** — nigdy zmiana reguły wejścia. To drugie byłoby
strojeniem sygnału pod ograniczenie kapitałowe, czyli dokładnie tym, czego
zakazuje reguła R2.

## 12. Co by mnie przekonało, że cały ten projekt nie działa?

Pytanie najważniejsze, bo bez odpowiedzi na nie projekt nie jest badaniem, tylko
poszukiwaniem potwierdzenia.

Przekonałoby mnie:

- **wyczerpanie klas mechanizmów** — sześć klas przebadanych, w każdej efekty
  albo nie istnieją, albo giną po kosztach;
- **systematyczny rozjazd paper kontra backtest** — jeśli wyniki live są
  regularnie gorsze, model wykonania jest fałszywy i wszystkie liczby są
  fikcją;
- **niestabilność w czasie** — efekt obecny do 2022 i nieobecny potem oznacza,
  że badamy historię, nie rynek;
- **przewaga w granicach kosztów** — 2 punkty przewagi przy 2,20 USD kosztu to
  nie strategia, to hazard z dodatkowymi krokami.

Odpowiedzią na każdy z tych scenariuszy jest zamknięcie projektu, a nie
obniżenie progów. Obniżenie progów po zobaczeniu wyniku to reguła R2 złamana
w najczystszej postaci.

---

## Jak sprawdzić, czy się rozumie

Nie przez przeczytanie. Przez:

1. odtworzenie transakcji z `docs/OD_DANYCH_DO_PNL.md` i wyjaśnienie każdego
   z dziewięciu etapów własnymi słowami,
2. wskazanie w `docs/ZALOZENIA.md` trzech założeń, których złamanie unieważnia
   najwięcej wyników,
3. wyjaśnienie, dlaczego H013 upadła, bez zaglądania do raportu.

Jeśli któryś punkt nie wychodzi, to nie jest problem właściciela — to jest
miejsce, gdzie dokumentacja projektu jest niewystarczająca i trzeba ją poprawić.
