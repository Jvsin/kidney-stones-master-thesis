# Podsumowanie podziału zbioru Chinese

## Zakres i metoda

Podział obejmuje **259 unikalnych pacjentów** i został wykonany na poziomie
całego wolumenu pacjenta. Przekroje, maski i późniejsze patche pochodzące od
jednego pacjenta pozostają w jednym zbiorze.

- proporcje: **70% train / 15% validation / 15% test**,
- ziarno losowe: **42**,
- etykieta kamienia: **1**,
- etykieta nerek: **2**,
- jednostka podziału: `patient_id`,
- stratyfikacja: brak kamienia oraz wielkość największego kamienia.

Pacjent `wd0218_ps` został wykluczony przed klasyfikacją i stratyfikacją, ponieważ
nałożona przez niego etykieta 1 oznacza całą nerkę zamiast kamienia. Pliki
źródłowe pacjenta pozostają w katalogu danych, lecz pacjent nie występuje w
żadnym z trzech zbiorów.

Etykieta 1 została potwierdzona wizualnie we viewerze. W przykładowym badaniu
`wd0000_ps` zajmuje 4 woksle, podczas gdy etykieta 2 zajmuje 400 637 wokseli.

## Podział pacjentów

| Zbiór | Pacjenci | Udział | Z kamieniem | Bez kamienia | Częstość kamieni |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 181 | 69,88% | 146 | 35 | 80,66% |
| Validation | 39 | 15,0% | 31 | 8 | 79,49% |
| Test | 39 | 15,06% | 31 | 8 | 79,49% |
| **Razem** | **259** | **100,0%** | **208** | **51** | **80,31%** |

Zbiory są rozłączne na poziomie identyfikatorów pacjentów:

- wspólne ID train/validation: 0,
- wspólne ID train/test: 0,
- wspólne ID validation/test: 0.

Proporcje chorych i zdrowych są zbliżone w każdym zbiorze i odzwierciedlają
rozkład całej kohorty: **208 pacjentów z kamieniem do 51 bez kamienia**.

## Klasy wielkości kamienia

Objętość pacjenta z kamieniem określono jako objętość **największego
pojedynczego kamienia**, a nie sumę wszystkich kamieni:

\[
V_{\text{kamienia}} =
N_{\text{wokseli składowej}}
\times s_x \times s_y \times s_z
\]

gdzie \(s_x, s_y, s_z\) to rzeczywisty spacing z nagłówka maski NIfTI.
Osobne kamienie wyznaczono jako składowe 3D połączone ścianami, czyli z
6-spójnością. Woksele stykające się tylko krawędzią lub narożnikiem nie są
łączone w jeden kamień.

| Klasa | Definicja | Pacjenci | Udział w całym zbiorze |
| --- | ---: | ---: | ---: |
| Brak kamienia | `V = 0 mm³` | 51 | 19,69% |
| Mały | `0 < V ≤ 28 mm³` | 14 | 5,41% |
| Średni | `28 < V ≤ 315 mm³` | 40 | 15,44% |
| Duży | `V > 315 mm³` | 154 | 59,46% |

## Stratyfikacja klas wielkości

| Zbiór | Bez kamienia | Mały | Średni | Duży | Suma |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 35 | 10 | 28 | 108 | 181 |
| Validation | 8 | 2 | 6 | 23 | 39 |
| Test | 8 | 2 | 6 | 23 | 39 |
| **Razem** | **51** | **14** | **40** | **154** | **259** |

Każda klasa występuje we wszystkich trzech zbiorach. Liczebności są możliwie
bliskie proporcji 70% / 15% / 15% po uwzględnieniu konieczności przypisania
całych pacjentów do dokładnie jednego zbioru.

### Udział klas wielkości według liczby pacjentów

| Zbiór | Małe | Średnie | Duże |
| --- | ---: | ---: | ---: |
| Train | 5,52% | 15,47% | 59,67% |
| Validation | 5,13% | 15,38% | 58,97% |
| Test | 5,13% | 15,38% | 58,97% |

Udział podano w odniesieniu do wszystkich pacjentów danego zbioru, łącznie ze
zdrowymi. Brakujące udziały odpowiadają pacjentom bez kamienia. Rozkład liczby
pacjentów jest bardzo podobny w train, validation i test.

## Rozkład liczby wokseli

Poniższa tabela opisuje liczbę wokseli **największej pojedynczej składowej
kamienia**. Nie jest to liczba wokseli etykiety 1 z całej maski w przypadku
pacjenta z wieloma kamieniami.

| Zbiór | Klasa | n | Minimum | Q1 | Mediana | Q3 | Maksimum | Średnia |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | Mały | 10 | 4 | 5,25 | 7,0 | 10,75 | 18 | 8,8 |
| Train | Średni | 28 | 29 | 79,25 | 148,5 | 222,25 | 1 186 | 198,0 |
| Train | Duży | 108 | 273 | 1 095,0 | 2 305,0 | 7 252,0 | 114 706 | 8 187,1 |
| Validation | Mały | 2 | 4 | 5,25 | 6,5 | 7,75 | 9 | 6,5 |
| Validation | Średni | 6 | 21 | 27,25 | 45,0 | 56,75 | 225 | 69,7 |
| Validation | Duży | 23 | 310 | 1 688,5 | 3 204,0 | 5 608,0 | 96 251 | 8 943,3 |
| Test | Mały | 2 | 9 | 15,25 | 21,5 | 27,75 | 34 | 21,5 |
| Test | Średni | 6 | 51 | 83,0 | 134,0 | 181,25 | 461 | 173,8 |
| Test | Duży | 23 | 276 | 896,0 | 3 438,0 | 5 591,5 | 16 872 | 4 280,6 |

Liczba wokseli powinna być analizowana osobno od objętości w mm³. Klasy
mały/średni/duży zdefiniowano przez fizyczną objętość uwzględniając spacing,
dlatego zakresy liczby wokseli mogą zachodzić na siebie między klasami.

### Wszystkie woksle etykiety kamienia

Po zsumowaniu całej etykiety 1, zatem obejmując także dodatkowe kamienie u tego
samego pacjenta:

| Zbiór | Woksle kamienia | Udział globalnej liczby wokseli | Małe | Średnie | Duże |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 1 242 637 | 69,35% | 108 (0,009%) | 11 043 (0,889%) | 1 231 486 (99,102%) |
| Validation | 364 711 | 20,36% | 18 (0,005%) | 955 (0,262%) | 363 738 (99,733%) |
| Test | 184 372 | 10,29% | 50 (0,027%) | 1 348 (0,731%) | 182 974 (99,242%) |
| **Razem** | **1 791 720** | **100,00%** | **176** | **13 346** | **1 778 198** |

W każdym zbiorze duże przypadki odpowiadają za ponad **99% wokseli kamienia**,
chociaż na poziomie pacjentów stanowią około 59–62% całego zbioru. Jest to
naturalna konsekwencja dużej objętości tych segmentacji.

### Wnioski

- Liczby pacjentów w klasach małych, średnich i dużych są dobrze
  zbilansowane względem przyjętych proporcji.
- Na poziomie wokseli zbiory nie są zbilansowane — duże kamienie dominują
  całkowicie. Jest to typowa różnica między stratyfikacją pacjentów a
  bilansowaniem ich powierzchni segmentacji.
- Validation i test mają po 2 pacjentów z małym kamieniem. Utrzymanie wszystkich
  14 małych przypadków w jednym stałym podziale nie wystarcza do stabilnej
  oceny tej podgrupy; wskazana jest walidacja 5-krotna albo raportowanie
  metryk z przedziałem ufności.
- Train nadal zawiera większość skrajnie dużej segmentacji, co ogranicza
  bezpośrednią porównywalność średnich i wariancji objętości między zbiorami.

## Statystyki objętości

Statystyki dotyczą największego kamienia każdego z 208 pacjentów z etykietą 1.

| Klasa | n | Minimum | Mediana | Q1 | Q3 | Maksimum | Średnia |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mały | 14 | 4,86 | 9,25 | 6,66 | 14,19 | 26,46 | 11,33 |
| Średni | 40 | 29,21 | 133,27 | 72,11 | 239,09 | 312,01 | 151,80 |
| Duży | 154 | 329,95 | 2 714,32 | 1 120,48 | 5 609,64 | 96 024,91 | 6 497,88 |
| **Wszystkie kamienie** | **208** | **4,86** | **1 372,90** | **304,93** | **4 072,85** | **96 024,91** | **4 840,88** |

Wartości objętości podano w **mm³**. Duża różnica między medianą a średnią
wynika z silnie prawostronnie skośnego rozkładu i obecności bardzo dużych
segmentacji.

## Uwagi metodologiczne

1. Klasa kamienia jest wyznaczana na podstawie segmentacji, a nie pomiaru
   średnicy. Jej wynik zależy od jakości maski, wartości progu segmentacji oraz
   przestrzennego rozdzielenia składowych.
2. Grupa małych kamieni jest nieliczna. W validation i test znajdują się po
   **2 pacjentów** z małym kamieniem, dlatego wyniki dla tej podgrupy powinny
   być raportowane z dużą ostrożnością.
3. Pacjent `wd0218_ps` został wykluczony z powodu błędnej etykiety 1.
   Największa pozostała składowa należy do `wd0045_ps` i ma objętość
   **96 024,91 mm³**.
4. Rozmiar zbioru validation i test wynika z przyjętego stałego podziału.
   Dla bardziej stabilnej oceny małych i średnich kamieni można także użyć
   5-krotnej walidacji krzyżowej ze stratyfikacją na identycznych klasach.

## Pliki i odtwarzalność

- manifest podziału: `patient_splits.json`,
- generator podziału: `../../tools/split_chinese.py`,
- viewer masek: `../../tools/view_nifti.py`,
- ponowne wygenerowanie:

```powershell
python tools\split_chinese.py
```

Ten sam seed i niezmieniony zbiór danych odtwarzają identyczny podział.
