# Segmentacja kamieni nerkowych w obrazach CT

Repozytorium pracy magisterskiej dotyczącej zwiększania odporności modeli głębokiego
uczenia na zmienność obrazów tomografii komputerowej w zadaniu segmentacji kamieni
nerkowych.

## Struktura projektu

- `datasets/raw/` – oryginalne dane wejściowe.
- `datasets/interim/` – dane pośrednie powstające podczas przetwarzania.
- `datasets/processed/` – dane przygotowane do treningu i ewaluacji.
- `preprocessing/` – kod wstępnego przetwarzania obrazów i masek.
- `models/` – implementacje modeli bazowych i proponowanej metody.
- `tools/` – pomocnicze skrypty do pracy z danymi i eksperymentami.

## Weryfikacja zbioru Chinese

Zainstaluj zależności w środowisku Python i uruchom:

```powershell
python -m pip install -r requirements.txt
python tools\verify_chinese.py > datasets\chinese\verification_report.txt
```

Skrypt wyszukuje pary `*_image.nii.gz` i `*_mask.nii.gz` we wszystkich częściach
zbioru. Wypisuje dla każdego pacjenta wymiary, rozmiar woksela i liczebność
etykiet oraz porównuje geometrię obrazu i maski. Na końcu podaje rozkład rozmiarów
wokseli, listy masek pustych i pozbawionych każdej z etykiet oraz wykryte problemy.
Domyślnie oczekuje 260 par; inną liczbę można podać przez `--expected-count`.
Porównanie z orientacyjnymi zakresami spacingu używa zaokrąglenia do liczby miejsc
po przecinku podanej dla danego zakresu (trzy dla XY, dwa dla Z).
Znaczenie etykiet wymaga potwierdzenia w dokumentacji zbioru; po potwierdzeniu można
wskazać etykietę kamienia opcją `--stone-label 1` lub `--stone-label 2`. Brak tej
etykiety nie dowodzi błędu bez niezależnej informacji o obecności kamieni.
Wynikowy raport jest lokalny i ignorowany przez Git.

## Podział zbioru Chinese

Stały podział 70% / 15% / 15% jest tworzony wyłącznie na poziomie pacjenta.
Stratyfikacja obejmuje brak kamienia oraz wielkość największego pojedynczego
kamienia, mierzoną jako objętość największej składowej 6-spójnej w masce:

- mały: $0 < V \leq 28\ \mathrm{mm}^3$
- średni: $28 < V \leq 315\ \mathrm{mm}^3$
- duży: $V > 315\ \mathrm{mm}^3$

```powershell
python tools\split_chinese.py
```

Manifest domyślnie zapisuje się jako
`datasets/chinese/patient_splits.json`. Zawiera osobno ścieżki obrazu i maski
dla każdego pacjenta, objętość największego kamienia i liczbę pacjentów w każdej
klasie wielkości w zbiorach train, validation i test. Ten sam `--seed` daje
identyczny podział, a obecność kamienia jest domyślnie rozpoznawana przez
etykietę 1. Objętość jest liczona na podstawie liczby wokseli składowej oraz
rzeczywistego spacingu obrazu w mm³.

Aktualny zbiór zawiera 51 pacjentów bez kamienia, 14 z największym kamieniem
małym, 40 średnim i 155 dużym. Podział zapisany dla `seed=42`:

| Zbiór | Pacjenci | Bez kamienia | Małe | Średnie | Duże |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 182 | 36 | 10 | 28 | 108 |
| Validation | 39 | 8 | 2 | 6 | 23 |
| Test | 39 | 7 | 2 | 6 | 24 |

## Viewer NIfTI

Instalując `matplotlib`, można przejrzeć obraz i wybraną etykietę maski:

```powershell
python tools\view_nifti.py datasets\chinese\part1\wd0000_ps_image.nii.gz
```

Do wyboru etykiety maski służy panel `Mask`, bez automatycznego założenia,
która etykieta oznacza kamień, a która nerki. Przekroje X/Y/Z zmienia się
suwakami albo kółkiem myszy nad odpowiednim widokiem. Można również podać
maskę jako pierwszy argument:

```powershell
python tools\view_nifti.py datasets\chinese\part1\wd0000_ps_mask.nii.gz --label 1
```

Jeżeli nazwy nie mają standardowych sufiksów `_image` i `_mask`, ścieżkę maski
można wskazać osobno przez `--mask`.

## Dane medyczne i Git

Zawartość katalogów danych jest ignorowana przez Git, z wyjątkiem plików `.gitkeep`
utrzymujących strukturę katalogów. Pliki DICOM (`.dcm`, `.dicom`) i NIfTI
(`.nii`, `.nii.gz`, również warianty dwplikowe `.hdr`/`.img` i ich wersje
skompresowane) są ignorowane w całym repozytorium, niezależnie od wielkości liter.

Samo rozszerzenie nie pozwala rozpoznać wszystkich danych medycznych: DICOM może
nie mieć rozszerzenia lub używać innego. Przed dodaniem jakichkolwiek danych,
metadanych lub wyników do repozytorium sprawdź, czy nie zawierają danych pacjentów
i czy można je udostępniać. Reguły `.gitignore` nie usuwają plików już śledzonych
przez Git.
