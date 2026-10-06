# Brief drugiej generacji

Dokument **projektowy**, nie raport z pomiaru. Nie zawiera ani jednej liczby
policzonej z danych na potrzeby Gen2 — wszystkie wielkości pochodzą z raportów
Gen1 albo z publicznej specyfikacji instrumentów.

Nie uruchomiono: nowych przekrojów P&L, przeszukiwania cech, optymalizacji,
wariantów kart odrzuconych, środkowego tercyla H003, wariantu kontynuacyjnego
H014, żadnych zakupów danych.

---

## A. Cel Gen2

**Znaleźć predyktor kierunku albo wykonalny mechanizm P&L — nie kolejną zmienną
przewidującą amplitudę.**

Pierwsza generacja znalazła zmienne przewidujące amplitudę z bardzo dużą
pewnością (zakres nocny: t = +10,2) i **nic** przewidującego znak. To nie jest
przypadek ani pech — to opis tego, co zawiera cena i wielkość obrotu. Amplituda
jest w nich zapisana; kierunek nie.

Gen2 wygrywa tylko wtedy, gdy odpowiedź na pytanie „dlaczego akurat w tę
stronę?" jest zdaniem o **kimś, kto musi coś zrobić**, a nie o kształcie
wykresu.

---

## B. Ograniczenia odziedziczone po Gen1

Dziewięć zdań, z których każde ma pokrycie w raporcie. Naruszenie
któregokolwiek unieważnia kartę **przed** pomiarem, nie po.

| # | Ograniczenie | Skąd |
|---|---|---|
| 1 | OHLCV M1 nie dostarczyło stabilnego predyktora znaku | osiem kart, licznik prób 0 |
| 2 | Statystyka samej ceny i wielkości impulsu jest wyczerpana w przetestowanych rodzinach | cmentarz 3.1 — H003, H013, H014 |
| 3 | Zmienność przewiduje amplitudę, nie kierunek | cmentarz 3.3 — t = +10,2 dla amplitudy, ≈ 0 dla charakteru |
| 4 | Dotknięcie poziomu nie jest P&L | cmentarz 3.4 |
| 5 | Redukcja szumu nie jest przewagą | cmentarz 3.5 — hedge redukował wariancję i przegrywał z kosztami |
| 6 | Model opisujący nie jest sygnałem | W011 — OOS R² 0,975 i zero P&L |
| 7 | Historia 2019–2026 jest **zbiorem deweloperskim** | synteza 5.1 |
| 8 | Idea wygenerowana przez Gen1 wymaga forwardu | synteza 4.2 |
| 9 | „Zero prób" ≠ „zero ekspozycji na dane" | synteza 4.3 |

### Ograniczenie, którego w syntezie nie było — i które zmienia priorytety

Punkty 7 i 8 mają konsekwencję arytmetyczną, którą trzeba wypowiedzieć wprost,
bo inaczej Gen2 zaprojektuje się sama w ślepy zaułek.

Jeśli historia jest wyłącznie deweloperska, **jedynym uczciwym źródłem dowodu
jest forward**. A podłoga próby to 400 transakcji (cel 800+, `validation/power`).

**Czym N = 400 jest, a czym nie jest.** To **reguła governance tego projektu
i konserwatywna podłoga certyfikacji**, a nie uniwersalne prawo statystyczne.
Bardzo duży efekt bywa wykrywalny znacznie wcześniej. Świadomie nie
certyfikujemy jednak strategii na małej próbie, bo:

- efekty finansowe są niestabilne w czasie,
- obserwacje są zależne (klastrowanie zmienności),
- jedna faza rynku potrafi zdominować wynik,
- forward musi objąć więcej niż jeden reżim,
- potrzebujemy oszacowania **lewego ogona**, nie tylko średniej.

Nie należy więc pisać, że przy N < 400 zależność jest matematycznie
niewykrywalna. Należy pisać, że **my jej nie certyfikujemy**. Stąd:

| Częstotliwość okazji | Czas do N = 400 na forwardzie |
|---|---|
| ~30 zdarzeń rocznie (profil H013) | **ponad 13 lat** |
| ~50 rocznie (profil makro) | ~8 lat |
| ~250 rocznie (raz na sesję) | **~1,6 roku** |
| kilka razy dziennie | miesiące |

To nie jest szczegół harmonogramu, tylko **kryterium selekcji mechanizmu**.
Karta oparta na zdarzeniach rzadkich jest w tym projekcie niecertyfikowalna
niezależnie od tego, jak dobry ma mechanizm — nie dlatego, że jest zła, tylko
dlatego, że właściciel nie dożyje jej certyfikacji przed decyzją o kapitale.

**Wniosek dla Gen2: częstotliwość okazji przestaje być jednym z wielu kryteriów
i staje się warunkiem wstępnym.** Poniższa ocena to odzwierciedla.

---

## C. Skąd ma pochodzić nowy mechanizm

Dopuszczalne źródła — każde musi dać się zapisać jako łańcuch przyczynowy
„podmiot X **musi** zrobić Y w momencie Z, więc cena idzie w stronę W":

- reguły uczestników i mandaty (fundusze indeksowe, ETF-y, fundusze emerytalne),
- **wymuszone przepływy** o znanej dacie i znanym kierunku,
- mechanika aukcji i rozliczeń,
- informacja o agresorze (kto był stroną inicjującą),
- zmiany płynności i głębokości księgi,
- inventory i hedging dealerów,
- oficjalne reguły indeksów i kontraktów,
- literatura z **konkretnym** łańcuchem przyczynowym, nie samą korelacją.

**Nie wystarczy** kolejna transformacja OHLCV ani nowy iloraz dwóch cech ceny.
Kryterium praktyczne: jeśli mechanizm da się opisać bez wymienienia żadnego
uczestnika rynku, to nie jest mechanizm, tylko kształt.

---

## D. Pięć kierunków kandydackich

Kierunki, **nie karty**. Każdy wymagałby własnej karty, własnego pre-flightu
i osobnej decyzji.

---

### D1 — Rebalansowanie funduszy lewarowanych na zamknięciu

**Mechanizm.** Fundusz o stałej dźwigni *L* i aktywach *A* musi po ruchu indeksu
*r* dostosować ekspozycję. Rachunek jest zamknięty i nie zawiera żadnego
parametru swobodnego:

```
ekspozycja przed ruchem   E  = L·A
ekspozycja po ruchu       E' = L·A·(1+r)
kapitał po ruchu          A' = A·(1 + L·r)
ekspozycja wymagana       L·A' = L·A·(1 + L·r)
--------------------------------------------------
wymagana transakcja  ΔE = L·(L−1)·A·r
```

**Kto jest zmuszony.** Emitenci ETF-ów o stałej dziennej dźwigni na NDX —
3× długie, 2× długie, −1×, −2×, −3×. Mandat funduszu wymaga odtworzenia dźwigni
**każdego dnia**; to nie jest decyzja zarządzającego.

**Znak przepływu — i dlaczego to NIE jest nowy predyktor kierunku.**
Współczynnik `L·(L−1)` jest **dodatni dla obu stron**: dla L = 3 wynosi 6, dla
L = −3 wynosi 12. Fundusz lewarowany i odwrotny **kupują tak samo**, gdy indeks
rośnie. Nie ma strony kompensującej, więc wymuszony przepływ zawsze **wzmacnia**
ruch dnia.

⚠ **KOREKTA WOBEC PIERWSZEJ WERSJI TEGO DOKUMENTU.** Napisałem wcześniej, że
„znak jest jednoznaczny", i to było twierdzenie **za mocne**. Znak ΔE pochodzi
w całości ze znaku `r` — aktywa `A` i dźwignia zmieniają **wielkość**
przewidywanego przepływu, nie jego stronę. Kierunek nadal pochodzi z B04.

Uczciwe sformułowanie kierunku brzmi więc:

> Czy zewnętrznie oszacowana **wielkość** wymuszonego rebalansowania przewiduje
> **dodatkową** kontynuację na zamknięciu ponad tę, którą przewiduje sam
> dotychczasowy zwrot dnia?

A nie: „czy fundusze lewarowane przewidują kierunek zamknięcia?".

Nową informacją może być wyłącznie **wielkość** wymuszonego przepływu, jego
**relacja do płynności** i **koncentracja czasowa**. Jeśli po kontroli na samo
`r` estymowany przepływ nic nie wnosi, D1 jest bardziej skomplikowaną wersją
B04 i musi zostać odrzucona.

**Kiedy działa.** W ostatnich kilkunastu minutach sesji, gdy fundusze domykają
ekspozycję. Siła rośnie z |r| i z aktywami kompleksu.

**Kiedy powinien zniknąć.** Gdy aktywa kompleksu lewarowanego zmaleją; gdy dzień
jest płaski (ΔE → 0); gdy rynek zacznie wyprzedzać przepływ na tyle wcześnie, że
zostanie wyceniony przed oknem.

**Zmienna obserwowalna.** Szacunek ΔE = Σ_i L_i(L_i−1)·A_i·r, gdzie A_i to
aktywa poszczególnych funduszy, a r to zwrot indeksu od poprzedniego zamknięcia
do momentu wejścia.

**Potrzebne dane.** Aktywa i liczba jednostek funduszy lewarowanych na NDX —
publikowane codziennie przez emitentów, **za darmo**. Ceny mamy.

> ✅ **Zweryfikowane w audycie** (`docs/D1_AUDYT_MECHANIZMU.md`): dane istnieją,
> są darmowe i point-in-time, pełna historia od inception. To założenie
> okazało się trafne.

**Częstotliwość okazji.** Każda sesja → **~250 rocznie**. Jedyny kierunek na
liście, który mieści się w rozsądnym czasie forwardu.

**Wykonalność na MNQ.** Pełna — transakcja jest w kontrakcie indeksowym,
w oknie o wysokiej płynności.

**Koszty.** Jedna transakcja dziennie, ~2,20 USD RT. Przy 250 sesjach ~550 USD
rocznie — wymaga przewagi ≥ ~1,1 punktu na transakcję samego pokrycia kosztów.

**Najtańszy falsyfikator.** Rozkład zwrotu ostatniego okna sesji warunkowany
**znakiem** szacowanego ΔE, z kontrolą na samo |r| dnia. Jeśli szacunek ΔE nie
dodaje nic ponad znak dziennego zwrotu, kierunek redukuje się do B04 i upada.

**Związek z porażkami Gen1.** ⚠ **Najbliższy publiczny benchmark to B04**
(intraday momentum, Gao i in. 2018) — a B04 jest zdegradowaną kartą H012. To nie
dyskwalifikuje kierunku, ale **stawia poprzeczkę**: różnicą mechanizmu jest
szacowanie **wielkości wymuszonego przepływu** z zewnętrznego, publicznego
źródła, a nie samo obserwowanie, że dzień jest wzrostowy. Test przyrostowy
i ablacja aktywów kompleksu są tu obowiązkowe, nie opcjonalne.

**Wygenerowany przez dane?** Nie. Mechanizm jest z reguł produktu i literatury
(Cheng & Madhavan 2009).

**Dane płatne?** Nie.

**Uczciwy forward.** Zamrożenie specyfikacji commitem, start następnego dnia
sesyjnego, minimum 400 zdarzeń **albo** 18 miesięcy — co nastąpi później.

---

### D2 — Baza i struktura terminowa NQ jako proxy pozycjonowania

**Mechanizm.** Spread kalendarzowy NQ (kontrakt bliski minus dalszy) wycenia
koszt finansowania, oczekiwane dywidendy **i popyt na lewarowaną ekspozycję
długą**. Gdy pozycjonowanie długie się zatłacza, rolowanie robi się kosztowne —
spread odchyla się od wartości implikowanej stopą wolną od ryzyka.

**Kto jest zmuszony.** Każdy, kto utrzymuje ekspozycję dłużej niż kwartał, musi
rolować. Nie ma wyboru co do **faktu** rolowania, jest tylko wybór momentu — więc
popyt na roll jest nieelastyczny w oknie rolowania.

**Dlaczego znak.** Droga baza = tłok po stronie długiej = podwyższone ryzyko
przymusowej redukcji. Kierunek: odchylenie w górę → późniejsza słabość. To wzorzec
udokumentowany w literaturze o bazie kontraktów terminowych i pozycjonowaniu.

**Kiedy działa.** W oknach rolowania (4× rocznie) oraz w okresach skrajnego
odchylenia bazy.

**Kiedy powinien zniknąć.** Gdy odchylenie tłumaczy się w całości stopą i
dywidendami; wtedy nie mierzy pozycjonowania, tylko arytmetykę finansowania.

**Zmienna obserwowalna.** Spread bliski−dalszy skorygowany o implikowaną stopę
i harmonogram dywidend NDX.

**Potrzebne dane.** ⚠ **Wymaga sprawdzenia dostępności**: nasz `data/clean/`
zawiera wyłącznie kontrakt aktywny, więc drugi kontrakt trzeba by wydobyć z
`data/raw/` albo dokupić. **To jest kontrola dostępności, nie pomiar** — do
wykonania przed jakąkolwiek decyzją. Stopa: darmowa (H.15 Fed). Dywidendy NDX:
wymagają źródła.

**Częstotliwość okazji.** Niska — 4 okna rolowania rocznie, ewentualnie
uzupełnione dniami skrajnej bazy. **To jest zabójcze kryterium** przy regule
forwardu: ~4–20 zdarzeń rocznie oznacza dekady do N = 400.

**Wykonalność na MNQ.** Sygnał z NQ, egzekucja w MNQ — dopuszczalne, ale trzeba
sprawdzić, czy spread MNQ jest wystarczająco płynny, jeśli sygnał miałby być
handlowany jako spread.

**Koszty.** Niskie w ujęciu rocznym (mało transakcji), ale to konsekwencja tego
samego problemu, co niska częstotliwość.

**Najtańszy falsyfikator.** Czy skorygowana baza w ogóle odchyla się od zera
w sposób wykraczający poza niepewność stopy i dywidend. Jeśli nie — nie ma czego
mierzyć.

**Związek z porażkami Gen1.** Niezależny od całego cmentarza: nie jest ani
warunkowaniem wielkością, ani zakresem, ani dotknięciem poziomu. Jest natomiast
**blisko** ograniczenia nr 5 (redukcja szumu ≠ przewaga), jeśli zamieni się
w handel spreadem dla samej stabilności.

**Wygenerowany przez dane?** Nie.

**Dane płatne?** Możliwe — zależy od wyniku kontroli dostępności.

---

### D3 — Ekspozycja gamma dealerów i przypinanie do strajków

**Mechanizm.** Animatorzy rynku opcji, którzy są netto krótko gamma, muszą
hedgować w kierunku ruchu (sprzedają w spadkach, kupują we wzrostach), co
wzmacnia trend. Netto długo gamma — odwrotnie, tłumią. W pobliżu dużych
skupisk otwartych pozycji cena bywa przypinana do strajku.

**Kto jest zmuszony.** Animatorzy z mandatem delta-neutralności.

**Dlaczego znak.** Tu jest **problem, którego nie da się zamieść**: gamma
przewiduje przede wszystkim **charakter** ruchu (trend kontra powrót), a nie
jego kierunek. Kierunek pojawia się tylko lokalnie, przy przypinaniu do strajku
i przy przejściu przez „gamma flip".

**Kiedy działa.** Wokół wygasania miesięcznego i kwartalnego, przy dużej
koncentracji OI.

**Kiedy powinien zniknąć.** Po wygaśnięciu; gdy OI się rozprasza.

**Zmienna obserwowalna.** Skumulowana ekspozycja gamma dealerów po strajkach,
odległość ceny od największego skupiska.

**Potrzebne dane.** Otwarte pozycje opcji na NDX/QQQ po strajkach. Częściowo
darmowe (podsumowania OCC/CBOE), pełna historia — płatna.

**Częstotliwość okazji.** Umiarkowana, skoncentrowana wokół wygasań.

**Wykonalność na MNQ.** Sygnał z rynku opcji, egzekucja w MNQ — dopuszczalne.

**Najtańszy falsyfikator.** Czy autokorelacja zwrotów wewnątrzdziennych różni się
między reżimami gamma. Jeśli nie — mechanizm nie działa na tym instrumencie.

**Związek z porażkami Gen1.** ⚠ **To jest predyktor charakteru, a charakter już
raz upadł** (cmentarz 3.3: zakres przewiduje amplitudę, charakter t ≈ 0). Gamma
to inny mechanizm dla tej samej wielkości docelowej — dopuszczalne, ale wymaga
jawnego argumentu, czym różni się od tego, co już zawiodło.

**Ryzyko zatłoczenia: wysokie.** „GEX" jest publicznie liczony przez wiele
serwisów i szeroko omawiany. To najbardziej skomercjalizowany kierunek na liście.

**Wygenerowany przez dane?** Nie.

**Dane płatne?** Częściowo.

---

### D4 — Oficjalne reguły indeksu NDX: rekonstytucja i rebalans specjalny

**Mechanizm.** Nasdaq publikuje reguły indeksu z wyprzedzeniem: coroczna
rekonstytucja w grudniu, kwartalne korekty wag, oraz **rebalans specjalny**
uruchamiany progiem koncentracji. Fundusze śledzące muszą wykonać transakcję
na zamknięciu dnia wejścia w życie — data jest znana, kierunek per spółka jest
znany, wielkość jest szacowalna.

**Kto jest zmuszony.** Fundusze indeksowe i ETF-y śledzące NDX.

**Dlaczego znak.** Dla **spółek** znak jest jednoznaczny. **Dla indeksu — nie.**
Rebalans wagowy jest z definicji redystrybucją wewnątrz koszyka i w pierwszym
przybliżeniu neutralny dla samego indeksu. Kierunkowy efekt na MNQ musiałby
pochodzić z drugiego rzędu: z bazy, z niedopasowania czasowego przepływów albo
z aukcji zamknięcia.

**Kiedy działa.** Okno ogłoszenie → wejście w życie, kilka razy w roku.

**Zmienna obserwowalna.** Ogłoszona zmiana wag, szacowane aktywa śledzące.

**Potrzebne dane.** Komunikaty Nasdaq — **darmowe**. Wagi historyczne —
częściowo mamy z warstwy K6.

**Częstotliwość okazji.** **Bardzo niska** — kilka zdarzeń rocznie.

**Wykonalność na MNQ.** ⚠ **Słaba i to jest główny zarzut.** Efekt jest
w spółkach, a my handlujemy indeksem. Monetyzacja wymagałaby handlu koszykiem,
którego nie handlujemy.

**Najtańszy falsyfikator.** Czy zwrot indeksu w oknie rebalansu w ogóle różni
się od zwrotu w dniach porównywalnych. Prawdopodobna odpowiedź: nie.

**Związek z porażkami Gen1.** Niezależny od cmentarza, ale trafia w to samo
ograniczenie wykonalności, przez które upadło H015.

---

### D5 — Mikrostruktura agresora (WARUNKOWY — wymaga danych `trades`/MBP)

**Mechanizm.** **Strona inicjująca i odpowiedź płynności na przepływ.**
Przewaga agresji kupna nad sprzedażą przy jednoczesnym braku ruchu ceny oznacza,
że ktoś tę agresję absorbuje — i odwrotnie.

⚠ **KOREKTA WOBEC PIERWSZEJ WERSJI.** Napisałem wcześniej o „tożsamości
przepływu" i to przecenia zawartość tych danych. `trades` i MBP **pokazują**:
stronę inicjującą, nierównowagę agresji, reakcję ceny na agresję, absorpcję,
głębokość i zmiany księgi. **Nie pokazują**: czy uczestnikiem jest fundusz, czy
działa execution algo, czy zlecenie jest częścią większego zlecenia macierzystego,
ani czy ktokolwiek „musi" kontynuować.

**Kto jest zmuszony.** ⚠ Tego te dane **nie rozstrzygają**. Hipoteza
o niedokończonym dużym zleceniu, które musi być dokończone, wymagałaby
**osobnego argumentu** i nie może być traktowana jako obserwowany fakt.

**Dlaczego znak.** Kandydat na argument: przepływ ma bezwładność, bo mandat
wykonania nie znika z końcem minuty. To jest **hipoteza do uzasadnienia**, nie
przesłanka.

**Zmienna obserwowalna.** Nierównowaga agresji, absorpcja, zmiany głębokości
księgi w odpowiedzi na agresję.

**Potrzebne dane.** `trades` albo MBP. **Z OHLCV M1 to jest niebadalne** — nie
ma tam informacji o stronie inicjującej.

**Częstotliwość okazji.** Bardzo wysoka.

**Związek z porażkami Gen1.** To jest **dokładnie ta zmienna**, której cmentarz
3.1 i 3.3 domagają się jako warunku otwarcia rodziny na nowo: „zmienna opisująca
**kto** handlował, nie ile i jak szeroko". Kierunek jest więc merytorycznie
najlepiej uzasadniony z całej piątki.

**Dane płatne?** **Tak** — i dlatego kierunek pozostaje **warunkowy**.
Bez osobnej decyzji nic tu nie kupujemy. Znany punkt odniesienia z Gen1: miesiąc
`trades` MNQ kosztował 23,77 USD.

---

## E. Ocena kierunków przed pomiarem

Skala 0–5. **Nie oceniam potencjalnego Sharpe'a ani oczekiwanego zwrotu** — bez
danych taka ocena byłaby zgadywaniem udającym analizę.

| Kryterium | D1 lewar ETF | D2 baza | D3 gamma | D4 reguły NDX | D5 agresor |
|---|---|---|---|---|---|
| siła mechanizmu | **5** | 3 | 3 | 4 | **5** |
| jednoznaczność znaku *(patrz korekta przy D1)* | 2 | 3 | 2 | 1 | 4 |
| falsyfikowalność | **5** | 4 | 3 | 4 | 4 |
| dostępność danych | **5** | 2 | 2 | 4 | 1 |
| koszt | **5** | 3 | 2 | 5 | 2 |
| liczba okazji | **5** | 1 | 3 | 1 | **5** |
| realizm wykonania | **5** | 3 | 4 | 1 | 4 |
| niezależność od cmentarza | 3 | 4 | 2 | 4 | **5** |
| zgodność z limitami konta funded | **5** | 4 | 3 | 3 | 3 |
| **suma (max 45)** | **40** | 27 | 24 | 27 | 33 |

### Jak czytać tę tabelę

Suma nie jest werdyktem — jest sposobem, żeby zobaczyć, gdzie kierunki się
rozjeżdżają.

**D1 wygrywa nie siłą mechanizmu, tylko wykonalnością.** D5 ma równie mocny
mechanizm i lepszą niezależność od cmentarza, ale przegrywa na danych i koszcie.
To jest realny wybór, nie formalność: D1 można zacząć jutro za zero złotych,
D5 wymaga decyzji zakupowej.

**Jedyna słabość D1 to niezależność od cmentarza (3/5)** — jego benchmarkiem
jest B04, czyli zdegradowana karta H012. To trzeba traktować jako główne
ryzyko kierunku, nie jako drobiazg.

**D2 i D4 przegrywają na tym samym: liczbie okazji (1/5).** Przy regule
„historia = development only" kilka zdarzeń rocznie oznacza, że certyfikacja nie
nastąpi w horyzoncie decyzyjnym właściciela. Ich mechanizmy nie są złe —
są **niedopasowane do ograniczenia czasowego tego projektu**.

**D3 ma najniższą sumę** i dwa niezależne powody do ostrożności: przewiduje
charakter (który już raz upadł) i jest najbardziej skomercjalizowanym pomysłem
na liście.

---

## F. Protokół forwardu

Obowiązuje **każdą** kartę Gen2, bez wyjątku.

| Pole | Reguła |
|---|---|
| status historii | **2019–2026 = development only.** Wynik na tej historii nigdy nie jest potwierdzeniem. |
| data zamrożenia | commit, po którym specyfikacji nie wolno dotknąć; SHA w karcie |
| pierwszy dzień forwardu | pierwszy dzień sesyjny po commicie zamrażającym |
| minimalna liczba zdarzeń | **400** (`validation/power`, podłoga bezwzględna) |
| minimalny czas kalendarzowy | **12 miesięcy**, żeby próba objęła więcej niż jeden reżim |
| warunek negatywny | zadeklarowany **z góry**: co konkretnie zabija kartę |
| zmiany po starcie | **zakazane** |
| zmiana mechanizmu | **nowe ID i nowy forward**, nie poprawka |

Warunek negatywny jest tu najważniejszy i najczęściej pomijany. H003 zginęła na
własnym kryterium monotoniczności — gdyby go nie zadeklarowała, dałoby się ją
uratować wyborem środkowego tercyla. Karta bez zadeklarowanego warunku
negatywnego nie jest falsyfikowalna, więc nie jest hipotezą.

---

## G. Dane płatne

D5 i wszystko oparte na `trades`/MBP pozostaje **wymienione jako kierunek, ale
niekupione**. Każdy zakup wymaga osobno:

1. dokładnego mechanizmu, który dane odblokują (nie „zobaczymy, co tam jest"),
2. wskazania **pól** potrzebnych do testu,
3. minimalnego okresu danych,
4. wyceny przez `metadata.get_cost` przed zakupem,
5. sprawdzenia darmowej alternatywy,
6. najtańszego możliwego pre-flightu,
7. **osobnej zgody właściciela**.

Punkt odniesienia z Gen1: cała pierwsza generacja kosztowała **7,82 USD**
i zamknęła osiem kart. Próbka `trades` MNQ za miesiąc to 23,77 USD — czyli
trzykrotność całego dotychczasowego wydatku. To nie jest argument przeciw, tylko
skala, o której trzeba pamiętać przy decyzji.

---

## H. Czego ten dokument nie rozstrzyga

Zgodnie z ustaleniem: **nie wybieram kierunku i nie piszę żadnej karty.**

Do decyzji właściciela pozostaje wybór **maksymalnie jednego lub dwóch**
mechanizmów. Moja rekomendacja, gdyby była potrzebna:

- **D1 jako kierunek pierwszy** — jedyny, który da się zacząć bez zakupu danych
  i który akumuluje próbę forwardową w tempie pozwalającym na certyfikację
  w rozsądnym czasie. Z pełną świadomością, że jego benchmarkiem jest
  zdegradowana karta i test przyrostowy będzie ostry.
- **D5 jako kierunek warunkowy** — merytorycznie najmocniejszy, ale wymagający
  osobnej decyzji zakupowej. Sensowna kolejność to najtańszy możliwy pre-flight
  na jednym miesiącu `trades`, dopiero po zobaczeniu, co da D1.

**D2, D3 i D4 odradzam na teraz** — nie dlatego, że mechanizmy są złe, tylko
dlatego, że dwa z nich nie zmieszczą się w horyzoncie forwardu, a trzeci celuje
w wielkość, która w Gen1 już raz okazała się niepredykowalna.

Następny krok po decyzji: karta wybranego kierunku wraz z benchmarkiem, różnicą
mechanizmu, planem ablacji i zadeklarowanym warunkiem negatywnym — **przed**
jakimkolwiek pomiarem.

---

# Status kierunków po decyzji właściciela (03.08.2026)

| Kierunek | Status |
|---|---|
| **D1** | wybrany jako aktywny → **audyt: `NIEWYKONALNY`** (`docs/D1_AUDYT_MECHANIZMU.md`) |
| **D5** | rezerwowy, bez zakupu danych |
| D2, D3, D4 | odłożone bez pisania kart |

## Czego nauczył audyt D1

Dwie rzeczy warte przeniesienia na kolejne kierunki:

1. **Założenie o darmowych danych point-in-time było trafne** — i to nie jest
   oczywiste. Pełna historia aktywów i liczby jednostek jest publicznie
   dostępna od inception funduszy. Ta droga zostaje otwarta dla innych
   mechanizmów opartych na funduszach.

2. **Nowe kryterium selekcji, sprawdzalne na kartce przed pobraniem danych.**

> **Reguła algebraiczna.** Przed pobraniem danych sprawdź algebraicznie, czy
> zmienna mechanizmu nie jest tylko transformacją istniejącego benchmarku.
> W szczególności konstrukcja **`(wolno zmienny czynnik) × bieżący zwrot`**
> zwykle nie dostarcza nowego predyktora kierunku względem momentum. Zmienność
> czynnika musi być **wystarczająco szybka, point-in-time i niezależna od
> benchmarku**, żeby efekt dało się zidentyfikować.

   **To nie jest zakaz, tylko wymóg dowodu.** Nie twierdzę, że każda taka
   zmienna jest matematycznie bezużyteczna — może istnieć wolny czynnik
   z egzogenicznymi skokami albo wyraźnymi zmianami strukturalnymi, i wtedy
   identyfikacja jest możliwa. Reguła brzmi „**wymaga dowodu niezależnej
   zmienności**", a nie „automatycznie odrzucone".

   D1 upadł dokładnie na tym: `ΔE = K·r`, przy `K` zmieniającym się o rzędy
   wielkości wolniej niż `r`, bez żadnych skoków egzogenicznych. Wewnątrzroczne
   `R²` z zestawem kontrolnym B04 wyniosło 0,86–0,97.

   Kryterium należy dodać do listy pytań o każdy kolejny kierunek, obok pytania
   o częstotliwość okazji. Oba dają się rozstrzygnąć **przed** wydaniem złotówki
   i przed dotknięciem danych.
