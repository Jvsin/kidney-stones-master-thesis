# Podsumowanie podziału zbioru Chinese

## Zakres i metoda

Podział obejmuje **260 unikalnych pacjentów** i został wykonany na poziomie
całego wolumenu pacjenta. Przekroje, maski i późniejsze patche pochodzące od
jednego pacjenta pozostają w jednym zbiorze.

- proporcje: **70% train / 15% validation / 15% test**,
- ziarno losowe: **42**,
- etykieta kamienia: **1**,
- etykieta nerek: **2**,
- jednostka podziału: `patient_id`,
- stratyfikacja: brak kamienia oraz wielkość największego kamienia.

Etykieta 1 została potwierdzona wizualnie we viewerze. W przykładowym badaniu
`wd0000_ps` zajmuje 4 woksle, podczas gdy etykieta 2 zajmuje 400 637 wokseli.

## Podział pacjentów

| Zbiór | Pacjenci | Udział | Z kamieniem | Bez kamienia | Częstość kamieni |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 182 | 70,0% | 146 | 36 | 80,22% |
| Validation | 39 | 15,0% | 31 | 8 | 79,49% |
| Test | 39 | 15,0% | 32 | 7 | 82,05% |
| **Razem** | **260** | **100,0%** | **209** | **51** | **80,38%** |

Zbiory są rozłączne na poziomie identyfikatorów pacjentów:

- wspólne ID train/validation: 0,
- wspólne ID train/test: 0,
- wspólne ID validation/test: 0.

Proporcje chorych i zdrowych są zbliżone w każdym zbiorze i odzwierciedlają
rozkład całej kohorty: **209 pacjentów z kamieniem do 51 bez kamienia**.

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
| Brak kamienia | `V = 0 mm³` | 51 | 19,62% |
| Mały | `0 < V ≤ 28 mm³` | 14 | 5,38% |
| Średni | `28 < V ≤ 315 mm³` | 40 | 15,38% |
| Duży | `V > 315 mm³` | 155 | 59,62% |

## Stratyfikacja klas wielkości

| Zbiór | Bez kamienia | Mały | Średni | Duży | Suma |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 36 | 10 | 28 | 108 | 182 |
| Validation | 8 | 2 | 6 | 23 | 39 |
| Test | 7 | 2 | 6 | 24 | 39 |
| **Razem** | **51** | **14** | **40** | **155** | **260** |

Każda klasa występuje we wszystkich trzech zbiorach. Liczebności są możliwie
bliskie proporcji 70% / 15% / 15% po uwzględnieniu konieczności przypisania
całych pacjentów do dokładnie jednego zbioru.

## Statystyki objętości

Statystyki dotyczą największego kamienia każdego z 209 pacjentów z etykietą 1.

| Klasa | n | Minimum | Mediana | Q1 | Q3 | Maksimum | Średnia |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mały | 14 | 4,86 | 9,25 | 6,66 | 14,19 | 26,46 | 11,33 |
| Średni | 40 | 29,21 | 133,27 | 72,11 | 239,09 | 312,01 | 151,80 |
| Duży | 155 | 329,95 | 2 715,33 | 1 129,25 | 5 991,41 | 289 355,73 | 8 322,77 |
| **Wszystkie kamienie** | **209** | **4,86** | **1 375,41** | **309,05** | **4 096,96** | **289 355,73** | **6 202,20** |

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
3. Największa zmierzona składowa należy do pacjenta `wd0218_ps` ze zbioru train
   i wynosi **289 355,73 mm³**. Taka wartość jest skrajna i należy przejrzeć
   przypadek w viewerze, aby wykluczyć błąd maski albo połączenie artefaktów
   segmentacyjnych:

   ```powershell
   python tools\view_nifti.py datasets\chinese\part5\wd0218_ps_image.nii.gz --label 1
   ```
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
