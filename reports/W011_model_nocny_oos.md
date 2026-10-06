# W011 — walidacja OOS modelu nocnego (audyt zamykajacy H013)

*Wygenerowane przez `research/W011_model_nocny_oos.py`, 2026-08-02. N = 1690 predykcji, 2019-10-28 → 2026-07-29.*

**Status licznika prob: 0 zuzytych.**

## 0. Po co ten raport

W009 odrzucil H013 na podstawie rezyduum modelu nocnego, ale jakosci tego
modelu nie zmierzyl OOS. Jedyna podana liczba — redukcja odchylenia o 82% —
jest statystyka **in-sample**. W007 walidowal **inny obiekt**: QQQ na zwrotach
RTH wobec osmiu spolek, bez ES i SOXX.

Model jest tu **importowany z W009**, nie odtwarzany: `zbuduj()` zwraca te sama
macierz X i ten sam wektor y, ktore posluzyly do werdyktu.

## 1. Wynik out-of-sample

Predykcja dnia t z okna konczacego sie w t−1, okno 250 sesji, przez cala historie.

| Model | OOS R² | Obciazenie | MAE |
|---|---|---|---|
| pelny (skladniki + ES + SOXX) | 0.9753 | +0.14‱ | 8.18‱ |
| tylko ES + SOXX | 0.9393 | +0.11‱ | 12.73‱ |
| naiwny (rowne wagi skladnikow) | 0.8877 | +0.93‱ | 16.71‱ |

sd zwrotu nocnego NQ: 0.765% (77‱).

## 2. Kalibracja

Regresja `zrealizowane = α + γ · przewidziane`. Model dobrze skalibrowany ma
**γ ≈ 1** i **α ≈ 0**. γ < 1 oznacza, ze model **przestrzeliwuje** — a wtedy
rezyduum ma skladowa systematyczna, ktora karta H013 czytalaby jako sygnal.

| Model | γ (nachylenie) | α (wyraz wolny) |
|---|---|---|
| pelny (skladniki + ES + SOXX) | **1.013** | -0.19‱ |
| tylko ES + SOXX | **0.994** | -0.09‱ |
| naiwny (rowne wagi skladnikow) | **1.040** | -1.10‱ |

## 3. Rozklad roczny — z naciskiem na 2026

W007 znalazl w modelu DZIENNYM silne obciazenie w 2026 (−8.59‱ wobec +0.30‱
na calej probie). Pytanie, czy model nocny ma ten sam problem, jest kluczowe:
**jesli tak, rezyduum W009 ma w koncowce probki przesuniecie pochodzace
z modelu, a nie z rynku.**

| Rok | N | OOS R² | Obciazenie | MAE | γ |
|---|---|---|---|---|---|
| 2019 | 44 | 0.9723 | +1.14‱ | 3.23‱ | 1.020 |
| 2020 | 251 | 0.9659 | -2.62‱ | 11.76‱ | 0.998 |
| 2021 | 251 | 0.9594 | +1.05‱ | 7.44‱ | 1.055 |
| 2022 | 251 | 0.9792 | +0.43‱ | 8.38‱ | 0.979 |
| 2023 | 250 | 0.9775 | -0.34‱ | 6.10‱ | 1.023 |
| 2024 | 251 | 0.9780 | +0.77‱ | 7.31‱ | 1.000 |
| 2025 | 249 | 0.9872 | +0.65‱ | 7.72‱ | 1.017 |
| 2026 | 143 | 0.9723 | +1.46‱ | 10.37‱ | 1.095 |

## 4. Czy obciazenie rozni sie w sesje zdarzen

Gdyby model byl obciazony akurat w sesje publikacji wynikow, rezyduum W009
mialoby stale przesuniecie **dokladnie tam, gdzie karta patrzy**.

| Grupa | N | OOS R² | Obciazenie | MAE |
|---|---|---|---|---|
| sesje zdarzen | 185 | 0.9668 | +3.05‱ | 11.06‱ |
| pozostale sesje | 1505 | 0.9766 | -0.21‱ | 7.83‱ |

## 5. Czy korekta obciazenia zmienia werdykt W009

Obciazenie w sesje zdarzen (+3.05‱) jest rzedu **20% odchylenia
rezyduum** (153‱ na sesjach zdarzen wg W009). Przesuwa wiec **znak** rezyduum
w jedna strone — a znak jest sygnalem karty. W009 naliczyl 106 rezyduow
ujemnych wobec 79 dodatnich; przy symetrii oczekiwaloby sie ~93/93.

**Czesc "asymetrii stron" z przewidywania 4 W009 jest wiec artefaktem modelu,
nie wlasnoscia rynku.** Ponizej te same statystyki po korekcie obciazenia
sredniem z WCZESNIEJSZYCH sesji zdarzen (bez lookaheadu).

| Miara | Rezyduum surowe | Rezyduum skorygowane |
|---|---|---|
| Rezyduow ujemnych / dodatnich | 106 / 79 | 93 / 92 |
| korelacja(rezyduum, zwrot po otwarciu) | +0.0808 | +0.0893 |
| sredni wynik fade'u | -0.0363% | -0.0052% |
| **t** | **-0.79** | **-0.11** |

| Warunek | t (surowe) | t (skorygowane) |
|---|---|---|
| wszystkie zdarzenia | -0.79 | -0.11 |
| gorny tercyl \|rezyduum\| | -1.17 | -0.56 |
| gorny decyl \|rezyduum\| | -1.42 | -0.88 |

| Strona | N (skor.) | Sredni wynik | t |
|---|---|---|---|
| dodatnie rezyduum | 92 | +0.0582% | +0.95 |
| ujemne rezyduum | 93 | -0.0680% | -1.01 |

### Skad bierze sie ta "asymetria" — prostsze wyjasnienie

Po korekcie obie strony daja wynik o podobnej wielkosci i przeciwnym znaku,
co wyglada na mechanizm dzialajacy tylko w jedna strone. Nie jest to jednak
wlasnosc rezyduum, tylko **dryfu kierunkowego w poranki po publikacjach**:

| Grupa sesji | N | Zwrot 09:31→10:30 | t |
|---|---|---|---|
| sesje zdarzen | 185 | -0.0631% | -1.39 |
| pozostale sesje | 1505 | +0.0133% | +1.04 |

W poranki reakcji na wyniki NQ dryfuje w dol, w pozostale — lekko w gore.
Sygnal karty (`−sign(rezyduum)`) jedynie **rozcina ten dryf** zmienna, ktora
niesie malo informacji: strona, ktora "gra z dryfem", wychodzi na plus,
druga na minus. To nie jest domykanie sie rezyduum.

**Uwaga: to nie jest nowa karta.** Dryf ma t = −1.39 przy 185 obserwacjach,
czyli jest nieistotny, i zostal znaleziony **po** obejrzeniu wyniku. Zapisuje
go jako obserwacje do ewentualnego przyszlego ID, nie jako hipoteze do testu.

### Rozklad roczny w postaci bezwzglednej

Poprzednia wersja podawala **udzial procentowy roku w wyniku**, co przy ujemnym
wyniku calkowitym jest mylace: rok stratny wychodzil `+118%`, a zyskowny `−77%`.
Ponizej to samo bez ilorazow.

| Rok | N | Suma (pkt) | Srednia (%) | Znak |
|---|---|---|---|---|
| 2019 | 4 | -188 | -0.2621 | − |
| 2020 | 24 | -695 | -0.1615 | − |
| 2021 | 27 | -557 | -0.1151 | − |
| 2022 | 30 | -1422 | -0.2642 | − |
| 2023 | 31 | +867 | +0.1559 | + |
| 2024 | 28 | +641 | +0.1276 | + |
| 2025 | 26 | +1119 | +0.2399 | + |
| 2026 | 15 | +63 | +0.0233 | + |

Lat dodatnich: **4 z 8**. Rozstep srednich rocznych: od -0.2642% do +0.2399%.

## 6. Werdykt audytu

| Pytanie | Odpowiedz |
|---|---|
| Czy model nocny ma wartosc predykcyjna OOS? | R² = 0.9753 |
| Czy skladniki wnosza cos ponad ES+SOXX? | 0.9393 → 0.9753 |
| Czy model jest skalibrowany? | γ = 1.013, α = -0.19‱ |
| Czy jest obciazony na calej probie? | +0.14‱ przy MAE 8.18‱ |
| Czy jest obciazony w sesje zdarzen? | +3.05‱ przy MAE 11.06‱, R² 0.9668 |
| Najgorszy rok | 2021 (R² 0.9594, obciazenie +1.05‱) |
| Obciazenie 2026 | +1.46‱ |

### Co audyt ustalil

**Model nocny jest dobry i lepszy od dziennego.** OOS R² 0.9753 wobec 0.9436 dla modelu dziennego
z W007, MAE 8.18‱, kalibracja γ = 1.013. Nie ma tez problemu z 2026, ktory miał model dzienny
(+1.46‱ wobec −8.59‱ tam). **Rezyduum uzyte do odrzucenia karty
jest sensownym rezyduum** — i to jest glowna odpowiedz tego audytu.

**Skladniki wnosza duzo — do MODELU.** Sam ES+SOXX daje MAE 12.73‱; dolozenie osmiu spolek schodzi do 8.18‱, czyli o 36%.
To **nie jest sprzeczne** z przewidywaniem 6 z W009, ktore mowilo o czyms innym:
ze rezyduum tych skladnikow nie daje sygnalu handlowego lepszego niz sama luka.
Oba zdania sa prawdziwe i trzeba je trzymac osobno — modelowanie ruchu indeksu
to nie to samo co handlowanie odchylenia od modelu.

**Znaleziono realna usterke W009.** Model jest obciazony w sesje zdarzen
(+3.05‱ wobec −0.21‱ w pozostale), co przesuwalo znak rezyduum
i wytwarzalo pozorna asymetrie stron (106/79). Po korekcie bez lookaheadu
jest 93/92. **Przewidywanie 4 z W009 zawiodlo czesciowo z powodu wewnetrznego
dla modelu, nie wlasnosci rynku** — i tak trzeba je odtad opisywac.

**Werdykt karty sie nie zmienia.** Po korekcie wynik fade'u idzie ku zeru
(t -0.79 → -0.11), warunkowanie nadal dziala na opak
(t maleje wraz z wielkoscia rezyduum, nie rosnie), a znak wyniku nadal odwraca
sie miedzy 2022 a 2023. Zadna z tych trzech rzeczy nie byla artefaktem
obciazenia.

### Sformulowanie werdyktu

Poprzednia wersja W009 twierdzila, ze „sprzecznosci wewnetrzne nie sa kwestia
mocy testu". **To bylo za mocne.** Mala proba sama w sobie potrafi wytworzyc
niestabilnosc znakow, pozorna asymetrie i skrajne wyniki w decylu liczacym
19 obserwacji.

> Poprawne sformulowanie: **mimo ograniczonej mocy uklad wynikow jest
> niezgodny z wczesniej zadeklarowanymi przewidywaniami mechanizmu, dlatego
> karta nie spelnia bramki GO.**

To wystarcza do odrzucenia karty bez twierdzenia, ze udowodniono statystycznie
brak jakiegokolwiek edge'u. Nie udowodniono i przy tej probie udowodnic sie
nie da.

---

Odtworzenie: `python3 research/W011_model_nocny_oos.py`
