# Protokół współpracy — trzy modele, jeden właściciel

**Po co ten dokument.** Największym ryzykiem tego projektu nie jest błąd w kodzie —
błędy w kodzie łapią testy o znanej odpowiedzi. Największym ryzykiem jest
**monokultura oceny**: jeden model pisze kod, projektuje kartę i wystawia sobie
świadectwo. Testy tego nie wykryją, bo test sprawdza, czy kod robi to, co napisano,
a nie czy napisano właściwą rzecz.

Ten protokół dzieli role tak, żeby żaden model nie oceniał własnej pracy, i opisuje
formaty, w których modele się ze sobą komunikują. Nie zmienia zachowania silnika ani
żadnego wyniku badawczego.

---

## 1. Role według dostępu, nie według „specjalizacji"

Podział wynika z tego, **co kto widzi**, bo to jedyna granica, której nie da się
przekroczyć dobrą wolą.

| Rola | Kto | Dostęp | Odpowiada za | Czego NIE robi |
|---|---|---|---|---|
| **Wykonawca** | Claude Code | repo + terminal + dane | buduje, testuje, pisze projekty kart i specyfikacji, prowadzi rejestry | **nie wystawia sobie oceny końcowej**; nie zamyka etapu własnym werdyktem |
| **Recenzent-weryfikator** | Notion AI | odczyt repo przez GitHub | krytyka kart, spec i wyników **z weryfikacją twierdzeń w źródle**; strażnik reguł procesu | nie pisze kodu; nie jest arbitrem sporu, w którym sam zajął stanowisko |
| **Ślepy recenzent i arbiter** | GPT | **celowo żaden** | ocena samowystarczalnych pakietów; arbitraż | nie dostaje repo, historii ani cudzych recenzji |
| **Właściciel** | Lipa | wszystko | **wszystkie decyzje** | — |

**Żaden model nie ma głosu rozstrzygającego.** Rekomendacja modelu jest wejściem do
decyzji właściciela, nigdy decyzją.

**Dlaczego ślepota GPT jest wartością, a nie ograniczeniem.** Recenzent, który zna
historię projektu, dziedziczy jego założenia — łącznie z błędnymi. Recenzent, który
widzi wyłącznie kartę, ocenia kartę. Jeśli karta jest niezrozumiała bez kontekstu,
to jest wada karty, nie recenzenta.

---

## 2. Meldunek standardowy

Kończy każdy handoff Wykonawcy. **Maksymalnie ~30 linii.**

**Zasada „artefakty, nie narracja":** wszystko, co da się recenzować, jest plikiem
w repo. Meldunek tylko **wskazuje ścieżki**. Opis wyniku w czacie nie jest wynikiem —
znika przy końcu sesji i nie da się go przypiąć do SHA.

```
STAN
  <SHA> · <gałąź> · jedno zdanie o tym, gdzie projekt stoi

ZROBIONE
  - <co> → <ścieżka pliku jako dowód>

LICZBY
  <dosłownie, bez zaokrągleń i bez słowa „około">

NIEPEWNOŚCI
  - <co może być nie tak i jak by to wyszło>
  (co najmniej jedna pozycja; „brak" jest ZAKAZANE)

DECYZJE DO PODJĘCIA
  - <opcja A> — koszt: <…> · <opcja B> — koszt: <…>

NASTĘPNY KROK
  <jedna propozycja, nie lista możliwości>
```

**Dlaczego „NIEPEWNOŚCI: brak" jest zakazane.** Wykonawca, który nie widzi żadnej
niepewności, najczęściej nie szukał. Wymuszenie jednej pozycji zamienia to
z deklaracji pewności siebie w pracę analityczną. Jeśli naprawdę nie ma nic
istotnego — wpisz najsłabsze ogniwo tego, co zrobiłeś, i powiedz, dlaczego
oceniasz je jako nieistotne.

**Dlaczego liczby dosłownie.** „Około 75 USD" i „75,0083 USD" to nie ta sama
informacja przy limicie 82 USD. Zaokrąglenie w meldunku wraca jako zaokrąglenie
w decyzji.

---

## 3. Pakiety komunikacyjne

### Pakiet A — meldunek

Po każdym etapie. Format z sekcji 2. Odbiorca: właściciel, do wglądu recenzenci.

### Pakiet B — ślepa recenzja

Zawiera **wyłącznie**: treść karty lub specyfikacji · rubrykę oceny
z `docs/GEN2_BRIEF.md` · reguły nienaruszalne z `HANDOFF.md`.

Nie zawiera: dyskusji, cudzych recenzji, wniosków Wykonawcy, historii projektu,
informacji o tym, czego się spodziewamy.

### Pakiet C — arbitraż

Dwa stanowiska w **formie symetrycznej**: zbliżona długość, **bez podpisów**,
bez wskazania, które jest czyje. Plus artefakty niezbędne do rozstrzygnięcia.

Asymetria formy jest sama w sobie argumentem — dłuższe stanowisko wygląda na
lepiej uzasadnione niezależnie od treści, a wiedza o autorze uruchamia zaufanie
zamiast oceny.

---

## 4. Szablony do wklejania

### Szablon pakietu B (ślepa recenzja)

```
Oceniasz samowystarczalny dokument. Nie masz dostępu do repozytorium ani do
historii projektu i nie potrzebujesz ich — jeśli dokument jest niezrozumiały
bez kontekstu, to jest jego wada i tak to zaraportuj.

ZADANIE: znajdź NAJMOCNIEJSZY ARGUMENT PRZECIW temu dokumentowi.
Nie szukaj równowagi. Nie doceniaj tego, co jest dobre — od tego są inni.

--- DOKUMENT ---
<pełna treść karty lub specyfikacji>

--- RUBRYKA OCENY ---
<wklej z docs/GEN2_BRIEF.md>

--- REGUŁY NIENARUSZALNE ---
<wklej sekcję „Zasady, których nie wolno naruszyć" z HANDOFF.md>

--- FORMAT ODPOWIEDZI ---
WERDYKT: GO / FIX / NO-GO
TRZY NAJMOCNIEJSZE ZARZUTY, każdy w postaci:
  Zarzut:  <co jest nie tak>
  Skutek:  <co się stanie, jeśli to zignorujemy>
  Warunek rozstrzygnięcia: <konkretny test, liczba albo plik, który to rozstrzyga>
CO PRZECZYTAŁEM: <wymień, na czym opierasz ocenę>
```

### Szablon pakietu C (arbitraż)

```
Rozstrzygasz spór. Nie wiesz, kto reprezentuje które stanowisko, i nie pytaj —
autorstwo nie jest przesłanką.

PYTANIE SPORNE:
<jedno zdanie>

STANOWISKO 1:
<treść>

STANOWISKO 2:
<treść>

ARTEFAKTY:
<liczby, fragmenty plików, wyniki — to samo dla obu stanowisk>

--- FORMAT ODPOWIEDZI ---
KTÓRE STANOWISKO JEST MOCNIEJSZE I DLACZEGO
NAJSŁABSZY PUNKT STANOWISKA, KTÓRE UZNAJESZ ZA MOCNIEJSZE
TEST ROZSTRZYGAJĄCY: <eksperyment, liczba albo plik o znanej odpowiedzi,
  który zamknąłby ten spór empirycznie>
JEŚLI TAKIEGO TESTU NIE DA SIĘ ZAPROJEKTOWAĆ — napisz to wprost.
```

---

## 5. Poziomy recenzji

### P1 — codzienny

Meldunek → krytyka albo OK. Bez ceremonii. Cel: wyłapać dryf, zanim urośnie.

### P2 — przed każdym zamrożeniem karty lub specyfikacji

**Dwie niezależne recenzje:**

| Recenzent | Tryb | Co wnosi |
|---|---|---|
| Notion AI | z weryfikacją twierdzeń w repo | czy to, co Wykonawca twierdzi, jest w plikach |
| GPT | ślepa (pakiet B) | czy dokument broni się sam, bez kontekstu |

Każda kończy się **werdyktem GO / FIX / NO-GO** i **trzema najmocniejszymi zarzutami**.

Wykonawca odpowiada **pisemnie na każdy zarzut** w sekcji „Recenzje" karty.
Zamrożenie następuje **dopiero po odpowiedziach** — nie po ich przeczytaniu.
`scripts/waliduj_karte.py` sprawdza obecność tej sekcji i nie pozwala zamrozić
karty bez niej.

Przy rozbieżnych werdyktach decyduje właściciel.

### P3 — spór

1. **Jedna runda** pisemnej wymiany. Jedna, nie „aż do porozumienia".
2. **Test rozstrzygający**, jeśli da się taki zaprojektować — eksperyment, liczba
   albo plik o znanej odpowiedzi. To jest droga preferowana: spór o fakty
   rozstrzyga pomiar, nie retoryka.
3. Jeśli testu zaprojektować się nie da — **jedna runda arbitrażu** (pakiet C)
   i decyzja właściciela.

**Zakaz iterowania do konsensusu.** Zgoda osiągnięta przez wielokrotne ścieranie
stanowisk nie jest dowodem — jest zmęczeniem materiału. Dwa modele doprowadzone
do zgody w piątej rundzie mówią to samo, bo dopasowały się do siebie, a nie dlatego,
że któreś miało rację.

---

## 6. Format zarzutu

```
Zarzut:                    <co jest nie tak>
Skutek zignorowania:       <co się wtedy stanie>
Warunek rozstrzygnięcia:   <konkretny test, liczba albo plik>
```

**Zarzut bez warunku rozstrzygnięcia może zostać odrzucony bez odpowiedzi
merytorycznej.** Nie dlatego, że jest z góry nietrafny — tylko dlatego, że nie
da się go zamknąć. „To wygląda podejrzanie" nie ma stanu końcowego; „rozkład
roczny pokazuje ponad 40% wyniku w jednym roku" ma.

Ta reguła obowiązuje **w obie strony**: Wykonawca też nie może odrzucić zarzutu
inaczej niż przez spełnienie albo obalenie jego warunku rozstrzygnięcia.

---

## 7. Higiena niezależności

1. **Ślepota GPT jest bezwzględna.** Podanie mu kontekstu, cudzej recenzji albo
   oczekiwanego wyniku **unieważnia recenzję**. Nie „osłabia" — unieważnia.
   Recenzję trzeba wtedy powtórzyć na innym pakiecie.
2. **Recenzje przypięte do SHA.** Recenzja bez SHA dotyczy nieznanej wersji.
3. **Recenzent wymienia, co przeczytał.** Bez tego nie wiadomo, czy zarzut wynika
   z dokumentu, czy z jego braku w polu widzenia.
4. **Pytania do recenzentów neutralne**, zawsze z poleceniem: *„znajdź najmocniejszy
   argument PRZECIW"*. Pytanie „czy to dobra karta?" dostaje odpowiedź „tak" istotnie
   częściej niż zasługuje.
5. **Recenzje przekazywane w całości.** Pośrednik nie streszcza — streszczenie
   gubi zarzut, którego streszczający nie zrozumiał, a to jest dokładnie ten zarzut,
   który był potrzebny.
6. **Zdanie odrębne zapisuje się w karcie.** Dissent to dane, nie porażka procesu.
   Karta, przy której jeden recenzent został przy NO-GO, niesie tę informację dalej —
   i jeśli karta upadnie, wiadomo, że ktoś to widział.
7. **Krytyka po zamrożeniu niczego nie odmraża.** Trafia do backlogu następnej
   generacji. Odmrażanie na podstawie krytyki, która przyszła po zobaczeniu wyniku,
   jest strojeniem pod wynik — łamie regułę R2.
8. **Pakiety muszą być samowystarczalne.** Zakaz zwrotów „jak ustaliliśmy wcześniej",
   „zgodnie z poprzednią rozmową", „standardowo u nas". Odbiorca nie ma tej rozmowy.

---

## 8. Czego ten protokół nie załatwia

Uczciwie, żeby nie budować fałszywego poczucia bezpieczeństwa:

- **Trzy modele mogą się mylić zgodnie.** Trenowane na podobnym materiale, dzielą
  część błędnych przekonań o rynkach. Niezależność recenzentów jest **częściowa** —
  większa niż jednego modela, mniejsza niż trzech ludzi z różnych szkół.
- **Recenzja nie zastępuje pomiaru.** Dlatego P3 preferuje test rozstrzygający,
  a `waliduj_karte.py` wymaga warunku negatywnego. Najlepszy recenzent jest gorszy
  od najgorszego eksperymentu o znanej odpowiedzi.
- **Protokół nie chroni przed złą hipotezą**, tylko przed złym procesem. Można
  bez zarzutu przeprowadzić bardzo porządne badanie zjawiska, którego nie ma.
