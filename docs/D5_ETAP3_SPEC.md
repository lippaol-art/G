# D5-C — audyt jednodniowej próbki MBO

**Specyfikacja zamrożona PRZED zakupem** (reguła R4). Commit z tym plikiem
poprzedza jakiekolwiek pobranie danych `mbo`.

**Data zamrożenia:** 2026-08-04.
**Poprzednik:** `D5-B INCONCLUSIVE — niewłaściwa jednostka pomiaru`.
**Licznik prób: 0.** Ten etap nie mierzy przyszłych zwrotów, P&L ani VIF.

---

## 1. Dlaczego ten etap istnieje

Databento potwierdziło (2026-08-04, `docs/D5_PYTANIE_DATABENTO.md` §C), że
`sequence` jest numerem sekwencyjnym wiadomości CME i **nie identyfikuje**
pojedynczego zdarzenia dopasowania. Wskazało `mbo` jako **minimalny właściwy
schemat** i `F_LAST` jako granicę zdarzenia per instrument.

Ten etap sprawdza, **czy da się z MBO odtworzyć pojedyncze zdarzenia agresora** —
nic więcej. Nie jest to test przewagi ani mechanizmu.

---

## 2. Próbka

| | |
|---|---|
| Sesja | **2026-07-30** — ta sama, którą posiadamy w `trades` |
| Instrument | `MNQU6`, `GLBX.MDP3`, `stype_in=raw_symbol` |
| Schemat | **`mbo`** |
| Okno | RTH `09:30–16:00 America/New_York`, UTC **wyprowadzone ze strefy** |
| Okno UTC (dla tej daty) | `2026-07-30T13:30` … `2026-07-30T20:00` |

**Dlaczego akurat ta sesja:** jest już development setem po Etapie 1, więc
**nie dokładamy nowej daty do ekspozycji na obejrzane dane**. Dodatkowo mamy
dla niej `trades`, co pozwala na kontrolę krzyżową obu schematów.

---

## 3. Koszt — zmierzony, nie ekstrapolowany

`metadata.get_cost` / `get_record_count` / `get_billable_size`, zapytania
read-only, 2026-08-04:

| Schemat | Koszt | Rekordów | Rozmiar rozliczeniowy |
|---|---|---|---|
| **`mbo`** | **3,5961 USD** | **38 306 877** | **2,145 GB** |
| `trades` (posiadany, dla skali) | 1,2318 USD | 984 113 | 0,047 GB |

**MBO to 38,9× więcej rekordów i 45,6× większy rozmiar** niż `trades` w tym
samym oknie.

### Zamrożony limit

```
LIMIT_USD = 4.00
```

Powyżej tej kwoty zakup **nie zostaje wykonany**. Limit jest o 11% wyższy od
wyceny — zapas na wahania liczby rekordów, nie na zmianę zakresu.

**Nie opieram limitu na wcześniejszym oszacowaniu 4,67 USD.** Ta liczba
pochodziła z ekstrapolacji, a moje ekstrapolacje kosztu myliły się w tym
projekcie dwukrotnie (o 21% i o 40%). Powyższa wycena dotyczy dokładnie tego
zapytania, które zostanie wykonane.

### Skala miesięczna — do decyzji, nie do zakupu

Przy tej stawce **miesiąc RTH w MBO to około 79 USD i ~47 GB** danych
rozliczeniowych. To istotna część odnawialnego budżetu 125 USD i wymaga
**osobnej decyzji**, której ten dokument NIE obejmuje.

---

## 4. Ostrzeżenie dostawcy o snapshocie księgi

`metadata` zwraca przy tym zapytaniu ostrzeżenie:

> The request time range does not start at UTC midnight, which contains
> a synthetic snapshot of the full order book state.

**Konsekwencja, którą zapisuję zawczasu:** okno RTH nie zawiera syntetycznego
snapshotu księgi, więc rekordy `Fill` mogą odwoływać się do zleceń złożonych
**przed** początkiem okna. Nie blokuje to celu tego etapu — badamy granice
zdarzeń i powiązanie Trade↔Fill, a nie rekonstrukcję pełnej księgi — ale
**każde pytanie wymagające stanu księgi jest poza zakresem D5-C** i wymagałoby
okna od północy UTC (czyli innego kosztu i innego rozmiaru).

Jeśli audyt wykaże, że powiązanie Trade↔Fill wymaga snapshotu, jest to wynik
etapu, a nie powód do cichego rozszerzenia zakupu.

---

## 5. Dziewięć pytań audytu — zamrożone przed zobaczeniem danych

1. Czy `F_LAST` jest **rzeczywiście obecne** i z jaką częstością?
2. Jak wyznaczyć granice zdarzenia **per instrument** (`F_LAST` + `instrument_id`)?
3. Jak łączą się rekordy `Trade` i `Fill` w obrębie jednego zdarzenia?
4. Jak często rekord `Trade` zawiera **`order_id` agresora**?
5. Czy da się zrekonstruować pojedyncze zdarzenia dopasowania — i dla jakiego
   odsetka zdarzeń jednoznacznie?
6. Czy **suma pasywnych wypełnień zgadza się** z odpowiadającym Trade Summary?
7. Czy z MBO da się odtworzyć **posiadany schemat `trades`** dla tej sesji
   (co do rekordu, ceny i wolumenu)?
8. Jaki jest **rzeczywisty rozmiar** pobranego pliku i czas przetwarzania?
9. Ile miejsca wymaga przetwarzanie (plik + struktury pośrednie)?

**Czego audyt NIE liczy:** przyszłych zwrotów, VIF, nierównowagi, korelacji
z ceną, żadnej metryki wynikowej. Pytanie 7 jest kontrolą spójności dwóch
schematów, nie pomiarem rynku.

---

## 6. Magazyn danych

Obsługa `PROJECT_G_DATA_ROOT` (`engine/paths.py`) pozwala skierować dane surowe
poza repozytorium. `data/clean/` **zostaje w repozytorium** — to artefakt
wersjonowany, na którym stoi `hash_danych` golden baseline'u.

Przed pobraniem skrypt sprawdza wolne miejsce i **przerywa**, gdy jest go mniej
niż trzykrotność oczekiwanego rozmiaru. Przerwany transfer na pełnym dysku
zostawia obciętą sesję — ta klasa awarii już w tym projekcie wystąpiła.

**Do repozytorium NIE trafia plik MBO.** Commitujemy wyłącznie: manifest,
parametry zapytania, SHA-256, raport i kod rekonstrukcji.

---

## 7. Możliwe wyniki i co po nich następuje

| Wynik | Co dalej |
|---|---|
| **MBO pozwala jednoznacznie rekonstruować zdarzenia** | powstaje **D5-B2**: zamrożona definicja oparta o `Trade`, `Fill` i `F_LAST`; wycena całego lipca RTH w MBO; **zakup dopiero po osobnej decyzji**; ponowny test identyfikowalności A przy **niezmienionych progach**; `GO` → dopiero wtedy H017 |
| **MBO działa, ale pliki są zbyt duże** | przetwarzanie sesjami; skompresowane raw lokalnie; pośredni kanoniczny zbiór zdarzeń; **żadnego wczytywania miesiąca do pamięci**; ocena, czy 300 GB wystarcza z zapasem na pliki tymczasowe |
| **MBO nie pozwala stabilnie odtworzyć zdarzeń** | **D5 `NO-GO` — jednostka mechanizmu nieobserwowalna.** Nie wracamy automatycznie do nierównowagi wypełnień ani wolumenu na tej samej historii |

---

## 8. Czego ten etap nie zmienia

`D5-B` pozostaje `INCONCLUSIVE`. Progi z §8 specyfikacji Etapu 2 **nie ulegają
zmianie** i zostaną zastosowane bez modyfikacji, jeśli powstanie D5-B2.
**B i C nie mogą przejąć roli głównej zmiennej A.**

**H017 nie powstaje na tym etapie. P&L nie jest mierzony. Licznik prób: 0.**
