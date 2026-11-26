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

Stały podział 70% / 15% / 15% jest tworzony wyłącznie na poziomie pacjenta,
ze stratyfikacją według etykiety kamienia:

```powershell
python tools\split_chinese.py
```

Manifest domyślnie zapisuje się jako
`datasets/chinese/patient_splits.json`. Zawiera osobno ścieżki obrazu i maski
dla każdego pacjenta oraz liczbę chorych i zdrowych w zbiorach train, validation
i test. Ten sam `--seed` daje identyczny podział, a obecność kamienia jest
domyślnie rozpoznawana przez etykietę 1. Podział dla aktualnego zbioru
(209 chorych i 51 zdrowych) ma 182 / 39 / 39 pacjentów w kolejnych zbiorach.

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
